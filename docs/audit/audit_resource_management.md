# AUDIT RESOURCE MANAGEMENT — YTGUI Phase 3

---

## RES-01: Duplicate `aiohttp.ClientSession` (TERKONFIRMASI)

**Severity:** MEDIUM  
**File:** `main.py` L43, `web/server.py` L108

```python
# main.py
http_session = aiohttp.ClientSession()  # Session A — digunakan oleh Room (lyrics, sponsorblock, connectivity)

# web/server.py create_app()
app["http_session"] = aiohttp.ClientSession()  # Session B — digunakan oleh stream proxy
```

**Leak Potensi:** Session B di-cleanup di `on_cleanup`, tapi jika `on_cleanup` tidak berjalan (abnormal exit), Session B leak. Session A di-cleanup di `main.py` finally block.

Lebih fundamental: dua session artinya dua connection pool ke Google/YouTube — tidak efisien.

**Fix:**
```python
# Teruskan http_session ke create_app
app = create_app(room_manager, ytdlp, db, http_session=http_session)

# web/server.py
def create_app(..., http_session: aiohttp.ClientSession):
    app["http_session"] = http_session  # pakai yang sudah ada
    # HAPUS on_cleanup yang menutup session ini (karena main.py yang tutup)
```

---

## RES-02: MPV Subprocess Tidak Di-terminate Saat Room Shutdown

**Severity:** HIGH  
**File:** `engine/mpv_controller.py` — `close()`

```python
async def close(self):
    self.is_connected = False
    if self._observer_task:
        self._observer_task.cancel()
    if self._writer:
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except OSError:
            pass
    
    if self._mpv_process:
        try:
            self._mpv_process.terminate()
            try:
                await asyncio.wait_for(self._mpv_process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._mpv_process.kill()
        except OSError:
            pass
```

Ini sudah cukup baik. Namun ada satu path: jika `MpvController.__init__` dipanggil tapi `connect()` belum pernah dipanggil (atau gagal sebelum `self._mpv_process` diset), `close()` akan skipprocess termination.

**Masalah lebih spesifik:** Di `main.py` awal, `mpv.connect()` dipanggil untuk default MPV, tapi jika gagal, `state.status` diset ke ERROR. Kemudian `Room` dibuat yang membuat `MpvController` baru untuk room. Tapi `mpv = MpvController()` di baris 37 main.py tidak digunakan lagi setelah `RoomManager` dibuat. MPV process yang sudah spawn (jika sempat) dari sini tidak punya reference dan tidak akan di-cleanup.

**Fix:** Hapus `mpv = MpvController()` di `main.py` dan biarkan RoomManager yang mengelola.

---

## RES-03: Socket File Tidak Dibersihkan Saat Crash

**Severity:** LOW  
**File:** `engine/mpv_controller.py` — `connect()`

```python
if os.path.exists(self.socket_path):
    try:
        os.remove(self.socket_path)
    except OSError:
        pass
# Spawn MPV...
```

Socket lama dihapus sebelum spawn MPV baru — ini sudah benar. Tapi jika aplikasi crash tanpa menjalankan `close()`, socket file tertinggal di `/tmp/`. Ini tidak serius (OS cleanup /tmp pada reboot), tapi bisa menyebabkan issue jika socket path sama dan file lama masih ada dari sesi sebelumnya.

Ini sudah di-handle dengan `os.remove` di awal `connect()`.

---

## RES-04: `TermuxNowPlaying` Thread Leak

**Severity:** MEDIUM  
**File:** `integrations/termux_notification.py`

```python
self._reader_thread = threading.Thread(target=self._blocking_read_loop, daemon=True)
self._reader_thread.start()
```

Thread adalah daemon, jadi akan mati saat main thread mati. Tapi di asyncio app, main thread tidak mati sampai event loop selesai. Saat `cleanup()` dipanggil:

```python
async def cleanup(self):
    self._stop.set()
    # ... hapus FIFO
```

`self._stop.set()` memberi sinyal ke thread untuk berhenti. Tapi jika thread sedang blocking di `open(self._fifo_path, "r")` (FIFO open tanpa writer memblokir), thread tidak akan berhenti sampai ada writer ke FIFO.

**Impact:** `cleanup()` return, tapi thread masih blocking. Thread akhirnya mati saat process exit, tapi `join()` tidak dipanggil.

**Fix:**
```python
async def cleanup(self):
    self._stop.set()
    # Unblock FIFO dengan membuka sebagai writer sebentar
    try:
        with open(self._fifo_path, "w") as f:
            pass  # open saja cukup untuk unblock reader
    except Exception:
        pass
    if self._reader_thread:
        self._reader_thread.join(timeout=2.0)
```

---

## RES-05: `LyricsFetcher` dan `SponsorBlockHandler` — Tidak Unsubscribe di Multi-Room

**Severity:** HIGH  
**File:** `integrations/lyrics.py` L20, `integrations/sponsorblock.py` L22

```python
class LyricsFetcher:
    def __init__(self, state, session=None):
        bus.subscribe(TrackProgressEvent, self._on_progress)  # ← subscribe
    
    def cleanup(self):
        bus.unsubscribe(TrackProgressEvent, self._on_progress)  # ← unsubscribe tersedia
```

`cleanup()` tersedia dan dipanggil di `Room.stop()`. Ini sudah benar.

Namun masalahnya: jika `Room` di-create dan kemudian di-destroy **tanpa memanggil `stop()`**, handler akan tetap terdaftar di global `bus` sebagai dead `WeakMethod` reference yang akan di-cleanup lazy saat next event dispatch. Ini OK karena `WeakMethod`, tapi ada jeda antara room destroy dan cleanup.

Lebih kritis: karena ini adalah global `bus`, bahkan jika cleanup berjalan benar, semua handler dari semua room masih subscribe ke bus yang sama.

---

## RES-06: `RadioMode._bg_tasks` Set — Task Orphan

**Severity:** MEDIUM  
**File:** `engine/radio_mode.py`

```python
async def on_activated(self, controller):
    task = safe_create_task(self._fetch_and_play_initial(...), name="radio_initial")
    self._bg_tasks.add(task)
    task.add_done_callback(self._bg_tasks.discard)

async def on_deactivated(self):
    self.state.radio_queue.clear()
    # ← tidak cancel _bg_tasks!
```

Saat radio dinonaktifkan, task yang masih berjalan tidak di-cancel. Task tersebut bisa selesai setelah mode berubah dan memanggil `controller.play_track()` pada state yang sudah bukan Radio Mode.

**Fix:**
```python
async def on_deactivated(self):
    self.state.radio_queue.clear()
    for task in list(self._bg_tasks):
        task.cancel()
    self._bg_tasks.clear()
    self._is_fetching = False
```

---

## RES-07: `Database` Connection — Error Path Tidak Tutup Connection

**Severity:** LOW  
**File:** `cache/db.py` — `init()`

```python
async def init(self):
    self._conn = await aiosqlite.connect(self.db_path)
    await self._conn.execute("PRAGMA journal_mode=WAL")
    
    with open(self._schema_path, "r") as f:  # ← bisa raise FileNotFoundError
        schema_sql = f.read()
    await self._conn.executescript(schema_sql)  # ← bisa raise
    
    await self._conn.execute("DELETE FROM tracks WHERE ...")
    await self._conn.commit()
```

Jika `open(schema_sql)` gagal atau `executescript` gagal, `self._conn` sudah di-set tapi exception di-raise tanpa menutup connection. `close()` tidak akan dipanggil jika init gagal (caller mungkin tidak handle ini).

**Fix:**
```python
async def init(self):
    self._conn = await aiosqlite.connect(self.db_path)
    try:
        await self._conn.execute("PRAGMA journal_mode=WAL")
        with open(self._schema_path, "r") as f:
            schema_sql = f.read()
        await self._conn.executescript(schema_sql)
        # ...
    except Exception:
        await self._conn.close()
        self._conn = None
        raise
```

---

## Ringkasan Resource Leak Risk

| Resource | Status | Risk |
|---|---|---|
| `aiohttp.ClientSession` (2x) | ISSUE | Duplikat, cleanup tidak sinkron |
| MPV subprocess | OK (ada cleanup) | Rendah |
| MPV socket file | OK (dihapus saat connect) | Rendah |
| Termux FIFO thread | ISSUE | Thread bisa hang saat cleanup |
| EventBus handler WeakRef | OK (auto-cleanup) | Sangat Rendah |
| RadioMode bg tasks | ISSUE | Orphan task saat deactivate |
| Database connection | PARTIAL | Error path tidak close |
| yt-dlp thread executor | OK (daemon threads) | Rendah |
