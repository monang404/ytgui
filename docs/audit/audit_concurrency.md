# AUDIT CONCURRENCY — YTGUI Phase 3

---

## Arsitektur Concurrency

YTGUI menggunakan satu asyncio event loop dengan:
- Background tasks via `safe_create_task()`
- Thread executor untuk yt-dlp (blocking)
- Satu `threading.Thread` untuk Termux FIFO reader
- MPV event observer sebagai background task

---

## CONC-01: Global EventBus — Cross-Room Event Contamination (KRITIS)

**Severity:** CRITICAL  
**Status:** TERKONFIRMASI

**Root Cause:**
```python
# core/event_bus.py
bus = EventBus()  # ← global singleton

# engine/mpv_controller.py
from core.event_bus import bus  # ← diimport global
await bus.publish(TrackProgressEvent(position=float(data)))  # ← tanpa room_id dispatch
```

**Problem Detail:**
`TrackProgressEvent` memiliki field `room_id`, tapi `EventBus.publish()` men-dispatch ke **semua subscriber** tanpa filtering room_id:

```python
async def publish(self, event: DomainEvent):
    event_type = type(event)
    for ref in list(self._subscribers[event_type]):  # ← semua subscriber!
        # ...
```

`LyricsFetcher`, `SponsorBlockHandler`, dan handler di `web/server.py` semuanya subscribe ke `TrackProgressEvent` global. Ketika room A publish progress event, handler dari room B, C, dst. semua dipanggil.

**Konkret Impact:**
- Lyrics sync room B bergerak berdasarkan posisi audio room A
- SponsorBlock room B bisa seek audio room B karena progress room A melewati segment

**Fix:**
```python
# Setiap Room buat EventBus sendiri:
class Room:
    def __init__(self, room_id, ...):
        self.event_bus = EventBus()  # bukan global bus!
        # ...
        self.mpv = MpvController(socket_path=..., event_bus=self.event_bus)
        self.lyrics_fetcher = LyricsFetcher(self.state, session=..., event_bus=self.event_bus)
        self.sponsorblock = SponsorBlockHandler(self.mpv, state=..., event_bus=self.event_bus)
```

---

## CONC-02: `PlaybackController._lock` — Lock Tidak Melindungi `_on_track_ended`

**Severity:** HIGH  
**Status:** POTENSIAL MASALAH (Race Condition)

```python
async def _on_track_ended(self, event: TrackEndedEvent):
    # TIDAK ada lock!
    if reason == "eof":
        await self._on_next(next_data)  # → masuk ke _on_next yang punya lock

async def _on_next(self, data=None):
    async with self._lock:  # lock baru di sini
        # ...
        await self._advance_to_next()
```

**Scenario:**
1. MPV mengirim dua event `end-file` (bisa terjadi saat reconnect atau bug MPV)
2. Dua coroutine `_on_track_ended` berjalan secara concurrent (via EventBus dispatch)
3. Keduanya memeriksa `self.state.current_track.video_id` — sama, karena state belum berubah
4. Keduanya memanggil `_on_next()` dengan `data["video_id"]` yang sama
5. Coroutine pertama masuk lock, advance ke track berikutnya
6. Coroutine kedua menunggu lock, masuk, memeriksa guard `current_track.video_id != data["video_id"]`
7. Pada saat ini `current_track` sudah berubah (track berikutnya) → guard `!=` benar → coroutine kedua mungkin juga advance!

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
            self.state.status = PlayerStatus.ERROR
            await asyncio.sleep(2)
            await self._advance_to_next()
```

---

## CONC-03: `TermuxNowPlaying` — Thread + Asyncio Bridge

**Severity:** MEDIUM  
**Status:** POTENSIAL MASALAH

```python
def _blocking_read_loop(self):
    while not self._stop.is_set():
        with open(self._fifo_path, "r") as f:
            for line in f:
                token = line.strip()
                if token and self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._handle_token(token), self._loop
                    )
```

**Issues:**
1. `self._loop` bisa menjadi `None` antara pengecekan `if self._loop` dan `asyncio.run_coroutine_threadsafe()` — tidak atomic
2. Jika event loop sudah ditutup tapi thread masih berjalan, `run_coroutine_threadsafe` akan raise `RuntimeError`
3. Thread tidak di-join saat cleanup — potensi orphan thread setelah shutdown

**Fix:**
```python
async def cleanup(self):
    self._stop.set()
    # Tutup FIFO untuk unblock blocking read
    try:
        with open(self._fifo_path, "w") as f:
            f.write("")  # unblock open()
    except Exception:
        pass
    if self._reader_thread and self._reader_thread.is_alive():
        self._reader_thread.join(timeout=2.0)  # tunggu thread selesai
    # ...

def _blocking_read_loop(self):
    loop = self._loop  # capture sekali
    while not self._stop.is_set() and loop and not loop.is_closed():
        # ...
        if loop and not loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._handle_token(token), loop)
```

---

## CONC-04: `RadioMode._is_fetching` Flag — Race Condition

**Severity:** MEDIUM  
**Status:** POTENSIAL MASALAH

```python
async def _prefetch_next(self, controller):
    if self._is_fetching:  # ← tidak atomic dengan set di bawah
        return
    self._is_fetching = True  # ← gap antara check dan set!
    try:
        # ...
    finally:
        self._is_fetching = False
```

Di Python asyncio, GIL mencegah true parallel execution, tapi dua coroutine bisa interleave di await point. Jika dua `_prefetch_next()` dipanggil sebelum ada yang mencapai `self._is_fetching = True`, keduanya bisa lolos check.

**Scenario:** `radio.next()` dipanggil, `safe_create_task(_prefetch_next)` dibuat. Sebelum task berjalan, `radio.next()` dipanggil lagi (cepat) dan task lain dibuat. Keduanya berjalan dan keduanya melihat `_is_fetching = False`.

**Fix:**
```python
self._prefetch_lock = asyncio.Lock()

async def _prefetch_next(self, controller):
    if self._prefetch_lock.locked():
        return
    async with self._prefetch_lock:
        # ...
```

---

## CONC-05: `Database` — Concurrent Access Tanpa Serialisasi

**Severity:** HIGH  
**Status:** TERKONFIRMASI

```python
class Database:
    async def upsert_track(self, track, stream_url=None, local_path=None):
        await self._conn.execute(query, (...))
        await self._conn.commit()  # ← bisa concurrent dengan operasi lain
    
    async def update_stream_url_only(self, video_id, stream_url):
        await self._conn.execute(...)
        await self._conn.commit()  # ← concurrent commit!
```

`aiosqlite` menggunakan satu connection dan `asyncio` event loop. Karena `await` adalah yield point, dua coroutine bisa mengeksekusi query secara interleaved:

1. Coroutine A: `execute(INSERT)`
2. Coroutine B: `execute(UPDATE)` ← interleave!
3. Coroutine A: `commit()` ← mengcommit keduanya (atau hanya A?)
4. Coroutine B: `commit()` ← no-op atau error?

`aiosqlite` menggunakan thread executor internal dan seharusnya serialisasi per-connection, tapi behavior di concurrent coroutine tidak explicitly guaranteed tanpa lock aplikasi.

**Fix:**
```python
class Database:
    def __init__(self, ...):
        self._write_lock = asyncio.Lock()
    
    async def upsert_track(self, ...):
        async with self._write_lock:
            await self._conn.execute(...)
            await self._conn.commit()
```

---

## CONC-06: `safe_create_task` — Task Leak di Shutdown

**Severity:** MEDIUM  
**Status:** POTENSIAL MASALAH

```python
# main.py
tasks = [connectivity_task, mpv_reconnect_task]
# ...
finally:
    for t in tasks:
        t.cancel()
```

Tasks yang dibuat via `safe_create_task()` di luar `tasks` list (misalnya `fetch_sponsorblock`, `fetch_lyrics`, `radio_initial`, `radio_prefetch`) tidak di-track untuk cancellation di shutdown. Saat `main()` masuk finally block, beberapa task ini mungkin masih berjalan.

`asyncio.run()` akan cancel semua task yang tersisa setelah event loop selesai, tapi tanpa explicit cancel, task bisa mencoba mengakses resources yang sudah di-cleanup (DB yang sudah ditutup, session yang sudah ditutup).

**Fix:**
```python
finally:
    # Cancel SEMUA pending tasks, bukan hanya yang di `tasks` list
    pending = asyncio.all_tasks()
    for task in pending:
        if not task.done():
            task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    
    # Baru cleanup resources
    await nowplaying.cleanup()
    await room_manager.shutdown()
    # ...
```

---

## Task Lifecycle Map

```
main()
├── connectivity_checker ← tracked, di-cancel di shutdown
├── mpv_reconnect_checker ← tracked, di-cancel di shutdown
├── WebServer (run_server) ← tracked via asyncio.run()
│
└── Per-request tasks (TIDAK tracked):
    ├── fetch_sponsorblock ← orphan jika shutdown saat fetch
    ├── fetch_lyrics ← orphan
    ├── radio_initial ← orphan jika deactivated
    ├── radio_prefetch ← orphan
    ├── download_{video_id} ← orphan
    └── event_{EventName} ← short-lived, OK
```

---

## Ringkasan Concurrency Risk

| Risk | Probability | Impact | Mitigasi |
|---|---|---|---|
| Cross-room event contamination | TINGGI (selalu terjadi di multi-room) | HIGH | Per-room EventBus |
| Double skip dari concurrent EOF | RENDAH | MEDIUM | Lock di _on_track_ended |
| Thread + loop race di Termux | SANGAT RENDAH | LOW | Capture loop reference |
| Radio prefetch race | RENDAH | LOW | Asyncio Lock |
| DB concurrent write | RENDAH (aiosqlite serialize) | MEDIUM | Write lock explicit |
| Task leak di shutdown | MEDIUM | LOW | Cancel all tasks |
