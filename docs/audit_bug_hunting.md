# AUDIT BUG HUNTING — YTGUI Phase 3

---

## BUG-01: MPV Reconnect Menggunakan Socket Global (TERKONFIRMASI)

**Severity:** HIGH  
**File:** `main.py` baris 78–98  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
async def mpv_reconnect_checker():
    while True:
        await asyncio.sleep(5)
        for room in list(room_manager.rooms.values()):
            if not getattr(room.mpv, "is_connected", False):
                await room.mpv.connect()  # ← MpvController.connect() menggunakan self.socket_path
```

Di `core/room_manager.py`:
```python
self.mpv = MpvController(socket_path=f"/tmp/mpv-socket-{room_id}")
```

Di `main.py` awal:
```python
for _ in range(50):
    await asyncio.sleep(0.1)
    if os.path.exists(MPV_SOCKET):  # ← ini global config, bukan per-room!
        break
```

Polling di `MpvController.connect()` menggunakan `MPV_SOCKET` (dari config global) bukan `self.socket_path` untuk cek keberadaan file. Jika ada lebih dari 1 room, reconnect akan salah tunggu socket.

**Reproduksi:**
1. Buat 2 room
2. Matikan MPV di room "room2"
3. `mpv_reconnect_checker` mencoba reconnect room2
4. Polling `os.path.exists(MPV_SOCKET)` menunggu `/tmp/mpv-socket-default` bukan `/tmp/mpv-socket-room2`
5. Reconnect bisa langsung berhasil (salah socket) atau timeout

**Fix:**
```python
# Di MpvController.connect()
# Ganti:
if os.path.exists(MPV_SOCKET):  # salah
# Dengan:
if os.path.exists(self.socket_path):  # benar
```

---

## BUG-02: `_retry_count` Tidak Di-reset di `_on_stop()` (TERKONFIRMASI)

**Severity:** MEDIUM  
**File:** `engine/playback_controller.py`  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
async def _on_stop(self, _data=None):
    await self.mpv.pause()
    self.state.status = PlayerStatus.IDLE
    self.state.current_track = None
    # ... tapi TIDAK ada: self._retry_count = 0
```

`_retry_count` diinisialisasi ke 0, direset ke 0 saat sukses play, tapi tidak direset saat stop. Jika user stop setelah 2 retry gagal, lagu berikutnya yang diputar hanya punya 1 kesempatan sebelum "Terlalu banyak kegagalan".

**Fix:**
```python
async def _on_stop(self, _data=None):
    self._retry_count = 0  # tambahkan ini
    await self.mpv.pause()
    # ...
```

---

## BUG-03: Double Skip Dari Concurrent `TrackEndedEvent` (POTENSIAL MASALAH)

**Severity:** HIGH  
**File:** `engine/playback_controller.py`  
**Status:** POTENSIAL MASALAH

**Root Cause:**
```python
async def _on_track_ended(self, event: TrackEndedEvent):
    reason = event.reason
    next_data = {}
    if self.state.current_track:
        next_data["video_id"] = self.state.current_track.video_id
    
    if reason == "eof":
        await self._on_next(next_data)  # ← tidak ada lock di sini
```

```python
async def _on_next(self, data=None):
    async with self._lock:  # lock di sini
        if data and isinstance(data, dict) and "video_id" in data:
            if not self.state.current_track or self.state.current_track.video_id != data["video_id"]:
                return  # guard ada
        await self._advance_to_next()
```

Guard `video_id` ada di `_on_next` tapi tidak di `_on_track_ended`. Jika dua event `end-file` dikirim MPV secara bersamaan (bug MPV atau reconnect), dua coroutine `_on_track_ended` berjalan bersamaan. Masing-masing mengambil `next_data` sebelum state berubah → dua panggilan `_on_next` dengan `video_id` yang sama → keduanya lolos guard → double advance.

**Reproduksi:** Sulit direproduksi secara deterministik. Lebih mungkin terjadi saat MPV reconnect mid-playback.

**Fix:**
```python
async def _on_track_ended(self, event: TrackEndedEvent):
    async with self._lock:  # pindahkan lock ke sini
        reason = event.reason
        next_data = {}
        if self.state.current_track:
            next_data["video_id"] = self.state.current_track.video_id
        
        if reason == "eof":
            await self._advance_to_next()
        elif reason == "error":
            # ...
```

---

## BUG-04: `DownloadManager._on_download` Signature Mismatch (TERKONFIRMASI)

**Severity:** HIGH  
**File:** `engine/download_manager.py` baris 19–21  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
# CommandBus.execute() calls handler(room_id, data)
command_bus.register(CMD_DOWNLOAD, self._on_download)

async def _on_download(self, track: TrackInfo | None = None):  # ← hanya 1 arg!
    target = track or self.state.current_track
```

Ketika `command_bus.execute(CMD_DOWNLOAD, room_id, data)` dipanggil, handler dipanggil sebagai `handler(room_id, data)`. Tapi signature `_on_download(self, track=None)` — `self` adalah instance, `room_id` akan masuk ke parameter `track`, dan `data` (TrackInfo) tidak diteruskan sama sekali.

**Reproduksi:**
```python
await command_bus.execute(CMD_DOWNLOAD, "default", some_track)
# _on_download dipanggil sebagai: _on_download(self, "default", some_track)
# tapi signature hanya: _on_download(self, track=None)
# → TypeError: _on_download() takes from 1 to 2 positional arguments but 3 were given
```

**Fix:**
```python
async def _on_download(self, room_id: str, track: TrackInfo | None = None):
    target = track or self.state.current_track
```

---

## BUG-05: `LyricsFetcher._on_progress` Subscribe ke Global Bus (TERKONFIRMASI)

**Severity:** HIGH  
**File:** `integrations/lyrics.py` baris 20  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
class LyricsFetcher:
    def __init__(self, state, session=None):
        self.state = state
        bus.subscribe(TrackProgressEvent, self._on_progress)  # ← global bus!
```

Setiap Room membuat `LyricsFetcher` sendiri. Namun semua subscribe ke global `bus`. Ketika room "A" memutar lagu dan MPV room A mengirim `TrackProgressEvent(room_id="A", position=30.0)`, **event ini di-dispatch ke SEMUA handler** yang subscribe `TrackProgressEvent` — termasuk `LyricsFetcher` dari room B, C, dst.

**Impact:**
- Lyrics sync dari room A akan mempengaruhi state lyrics room B
- `self.state.lyrics_index` di room B berubah berdasarkan posisi room A
- Dapat menyebabkan lyrics index out-of-sync

**Reproduksi:**
1. Buat 2 room, masing-masing putar lagu berbeda
2. Lihat bahwa `lyrics_index` room B bergerak berdasarkan posisi room A

**Fix:** Setiap Room harus punya `EventBus` sendiri, bukan menggunakan singleton global.

---

## BUG-06: `login_attempts` dan `command_history` Memory Leak (TERKONFIRMASI)

**Severity:** MEDIUM  
**File:** `web/server.py` — `ConnectionManager.__init__`  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
self.login_attempts: dict[str, list[float]] = {}
self.command_history: dict[str, list[float]] = {}
```

Entry di-evict dari list (sliding window 5 menit / 60 detik) tapi **key dict tidak pernah dihapus**. Untuk setiap IP unik yang pernah connect, key tetap ada selamanya.

Pada server yang menerima banyak IP berbeda (NAT besar, sekolah, kampus), `login_attempts` bisa tumbuh tanpa batas.

**Fix:**
```python
# Hapus key setelah cleanup
if not attempts:
    del manager.login_attempts[client_ip]

# Atau tambah background task cleanup setiap jam:
async def cleanup_rate_limits():
    while True:
        await asyncio.sleep(3600)
        now = time.time()
        manager.login_attempts = {
            k: [t for t in v if now - t < 300]
            for k, v in manager.login_attempts.items()
            if any(now - t < 300 for t in v)
        }
        manager.command_history = {
            k: [t for t in v if now - t < 60]
            for k, v in manager.command_history.items()
            if any(now - t < 60 for t in v)
        }
```

---

## BUG-07: Duplicate `http_session` (TERKONFIRMASI)

**Severity:** MEDIUM  
**File:** `main.py` baris 43, `web/server.py` baris ~108  
**Status:** TERKONFIRMASI

```python
# main.py
http_session = aiohttp.ClientSession()  # session #1
room_manager = RoomManager(db, ytdlp, http_session)

# web/server.py create_app()
app["http_session"] = aiohttp.ClientSession()  # session #2 — tidak pernah dipakai oleh Room!
```

Session di `create_app()` dipakai hanya untuk proxy stream (`handle_stream`). Session dari `main.py` dipakai untuk `LyricsFetcher`, `SponsorBlockHandler`, connectivity check. Tidak ada yang salah secara fungsional, tapi membuat resource tidak konsisten dan session #2 di `create_app` berpotensi leak jika cleanup tidak berjalan.

**Fix:** Teruskan `http_session` dari `main.py` ke `create_app()` sebagai parameter.

---

## BUG-08: `SponsorBlock` Buat Session Baru Jika Tidak Ada Session (POTENSIAL MASALAH)

**Severity:** LOW  
**File:** `integrations/sponsorblock.py` baris 38–45  
**Status:** POTENSIAL MASALAH

```python
session = self._session or aiohttp.ClientSession()  # ← membuat session baru jika None
close_after = self._session is None
try:
    async with session.get(...) as resp:
        ...
finally:
    if close_after:
        await session.close()
```

Jika `_session` adalah `None` (dan dipanggil di path di mana session tidak di-inject), setiap fetch SponsorBlock akan membuat dan menutup `aiohttp.ClientSession()` baru. `ClientSession` creation overhead tidak besar, tapi ini tidak ideal dan menunjukkan inconsistency dengan LyricsFetcher.

---

## BUG-09: `RadioMode._bg_tasks` Tidak Dibersihkan saat `on_deactivated()` (TERKONFIRMASI)

**Severity:** MEDIUM  
**File:** `engine/radio_mode.py`  
**Status:** TERKONFIRMASI

```python
async def on_deactivated(self) -> None:
    self.state.radio_queue.clear()
    # ← TIDAK ada: cancel _bg_tasks!
```

Saat user menonaktifkan Radio Mode, background tasks yang sedang berjalan (`radio_initial`, `radio_prefetch`) tidak di-cancel. Task tersebut bisa masih berjalan, memanggil `controller.play_track()` pada track radio yang sudah tidak relevan, men-switch playback kembali ke Radio Mode secara tak terduga.

**Reproduksi:**
1. Aktifkan Radio Mode
2. Segera switch ke Queue Mode (sebelum `_fetch_and_play_initial` selesai)
3. `_fetch_and_play_initial` selesai → memanggil `controller.play_track()` → override Queue Mode

**Fix:**
```python
async def on_deactivated(self) -> None:
    self.state.radio_queue.clear()
    for task in self._bg_tasks:
        task.cancel()
    self._bg_tasks.clear()
```
