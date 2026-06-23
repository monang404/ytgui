# AUDIT PERFORMANCE — YTGUI Phase 3

---

## Top 20 Bottleneck (Diurutkan berdasarkan Dampak)

### PERF-01: `yt-dlp` Dijalankan di Thread Executor Tanpa Pool Limit

**Severity:** HIGH  
**File:** `engine/ytdlp_client.py` — `search()`, `get_stream_url()`, `download_mp3()`  
**Dampak Estimasi:** 100–500ms per operasi, blokir event loop jika executor penuh

**Root Cause:**
```python
loop = asyncio.get_running_loop()
results = await loop.run_in_executor(None, self._extract_sync, url, opts)
```

`None` sebagai executor artinya menggunakan default `ThreadPoolExecutor` Python dengan `min(32, os.cpu_count() + 4)` thread. Jika Radio Mode aktif dan melakukan batch fetch untuk 4 artis sekaligus (`asyncio.gather`), bisa ada 4 thread `yt-dlp` concurrent yang masing-masing bisa berjalan 2–5 detik.

Di Termux (Android, 1–2 core), ini bisa menyebabkan starvation pada thread lain (MPV IPC, lyrics fetch, sponsorblock).

**Fix:**
```python
# Buat dedicated executor untuk yt-dlp
from concurrent.futures import ThreadPoolExecutor

class YtDlpClient:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ytdlp")
    
    async def search(self, query, max_results=10):
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(self._executor, self._extract_sync, url, opts)
```

---

### PERF-02: Lyrics Fetch Menggunakan `syncedlyrics` (Blocking) Sebagai Fallback

**Severity:** HIGH  
**File:** `integrations/lyrics.py` baris ~71  
**Dampak Estimasi:** 1–5 detik blocking di thread executor

```python
lrc = await loop.run_in_executor(None, syncedlyrics.search, search_query)
```

`syncedlyrics` melakukan HTTP request ke beberapa provider (Musixmatch, NetEase, dll) secara synchronous. Ini bisa memakan 1–5 detik dan memblokir thread pool.

**Fix:** Implementasikan versi async dari lyrics search, atau set timeout agresif:
```python
try:
    lrc = await asyncio.wait_for(
        loop.run_in_executor(None, syncedlyrics.search, search_query),
        timeout=5.0
    )
except asyncio.TimeoutError:
    lrc = None
```

---

### PERF-03: `RadioMode._gather_batch` — 4 yt-dlp Search Concurrent

**Severity:** HIGH  
**File:** `engine/radio_mode.py` baris ~157  
**Dampak Estimasi:** 2–8 detik untuk batch fetch, 4 thread yt-dlp parallel

```python
results_per_artist = await asyncio.gather(
    *[self._search_artist(artist) for artist in chosen],  # 4 concurrent searches
    return_exceptions=True,
)
```

Setiap `_search_artist` memanggil `ytdlp.search()` yang run di thread executor. 4 search concurrent → 4 thread yt-dlp sekaligus → tinggi CPU dan memori, terutama di Termux.

**Fix:** Batasi concurrent search dengan semaphore:
```python
_RADIO_SEARCH_SEM = asyncio.Semaphore(2)

async def _search_artist(self, artist: str) -> list:
    async with _RADIO_SEARCH_SEM:
        query = f"{artist} music"
        results = await self.ytdlp.search(query, max_results=15)
        # ...
```

---

### PERF-04: SQLite Write Setiap Play (Tanpa Batching)

**Severity:** MEDIUM  
**File:** `cache/db.py` — `increment_play_count()`, `upsert_track()`, `update_stream_url_only()`  
**Dampak Estimasi:** 1–5ms per write, bisa frequent jika banyak event

```python
async def increment_play_count(self, video_id: str):
    await self._conn.execute("UPDATE tracks SET ...")
    await self._conn.commit()  # ← commit setiap kali
```

WAL mode sudah diaktifkan (baik!), tapi setiap commit membuat fsync. Untuk 3 operasi berurutan (upsert + increment + stream_url_update), ada 3 commit terpisah.

**Fix:** Gunakan transaction batching untuk operasi yang berurutan:
```python
async def play_track_started(self, track: TrackInfo, stream_url: str):
    """Atomic batch untuk semua DB update saat track mulai diputar."""
    async with self._conn.execute("BEGIN"):
        await self._conn.execute("UPSERT ...")
        await self._conn.execute("UPDATE play_count ...")
        await self._conn.execute("UPDATE stream_url ...")
    await self._conn.commit()
```

---

### PERF-05: `SponsorBlockHandler._on_progress` — Linear Scan Segments

**Severity:** MEDIUM  
**File:** `integrations/sponsorblock.py` baris ~60  
**Dampak Estimasi:** Negligible untuk < 10 segments, tapi dipanggil 2–3x per detik

```python
async def _on_progress(self, event: TrackProgressEvent):
    for start, end in self.segments:  # linear scan
        if start <= current_pos <= start + 0.6:
            await self.mpv.seek(end)
            break
```

Dipanggil ~3x/detik untuk setiap room. Untuk video dengan banyak segment (educational content bisa 20+ segments), linear scan tidak efisien.

**Fix:** Gunakan `bisect` seperti yang sudah dilakukan di `LyricsFetcher`:
```python
import bisect

# Saat segments di-load:
self._segment_starts = [s for s, _ in self.segments]
self._segment_ends = [e for _, e in self.segments]

# Saat progress:
idx = bisect.bisect_right(self._segment_starts, current_pos) - 1
if idx >= 0 and current_pos <= self._segment_starts[idx] + 0.6:
    await self.mpv.seek(self._segment_ends[idx])
```

---

### PERF-06: WebSocket Broadcast ke Semua Client Untuk Setiap Progress Event

**Severity:** MEDIUM  
**File:** `web/server.py` — `ConnectionManager.broadcast()`  
**Dampak Estimasi:** O(N) per event, N = jumlah WS connections

```python
async def broadcast(self, message: dict, room_id: str = None):
    data = json.dumps(message, ensure_ascii=False)  # ← serialisasi ulang tiap broadcast
    dead = []
    for ws, r_id in self.active_connections:  # ← linear scan semua connections
        if room_id is None or r_id == room_id:
            await ws.send_str(data)
```

Progress event dikirim 3x/detik. Jika ada 10 client di room yang sama, ada 30 WS message/detik dari satu room. JSON serialisasi dilakukan satu kali (baik), tapi linear scan bisa lebih efisien jika rooms diindeks.

**Fix:**
```python
# Index connections per room
self._rooms: dict[str, list[web.WebSocketResponse]] = defaultdict(list)

async def broadcast(self, message: dict, room_id: str = None):
    data = json.dumps(message, ensure_ascii=False)
    targets = self._rooms.get(room_id, []) if room_id else [ws for connections in self._rooms.values() for ws in connections]
    for ws in targets:
        try:
            await ws.send_str(data)
        except Exception:
            # handle dead connections
```

---

### PERF-07: `_TITLE_NOISE_WORDS` Cek Menggunakan Tuple (bukan Set)

**Severity:** LOW  
**File:** `engine/radio_mode.py` baris ~57  
**Dampak Estimasi:** Minuscule per call, tapi dipanggil untuk setiap kata dari setiap title

```python
_TITLE_NOISE_WORDS = (  # ← tuple, O(n) lookup
    "official", "music", "video", ...
)
words = [w for w in t.split() if w not in _TITLE_NOISE_WORDS]
```

`not in` pada tuple adalah O(n). Dengan 22 noise words dan title yang memiliki 5–10 kata, setiap normalisasi = 50–220 comparisons.

**Fix:**
```python
_TITLE_NOISE_WORDS = frozenset((  # ← frozenset, O(1) lookup
    "official", "music", "video", ...
))
```

---

### PERF-08: `_build_exclusion_set()` Dipanggil Tiap Radio Search

**Severity:** LOW  
**File:** `engine/radio_mode.py` baris ~205  
**Dampak Estimasi:** Negligible, tapi creates set dari deque setiap batch

```python
def _build_exclusion_set(self) -> set[str]:
    ids = {t.video_id for t in self.state.radio_queue}  # iterasi seluruh radio_queue (max 30)
    if self.state.current_track:
        ids.add(self.state.current_track.video_id)
    for t in list(self.state.history)[-20:]:  # iterasi 20 history
        ids.add(t.video_id)
    return ids
```

Dipanggil 4x per batch (sekali per artis). Set comprehension dari deque — tidak bisa O(1). Untuk radio_queue max 30 item, overhead kecil tapi bisa dikache.

---

### PERF-09: `last_progress` Throttle Dict Shared (Semua Room)

**Severity:** LOW  
**File:** `web/server.py` baris ~140  
**Dampak Estimasi:** Room A throttle mempengaruhi room B

```python
last_progress = {"t": 0.0}  # ← satu dict untuk semua room

async def _on_track_progress(event: TrackProgressEvent):
    now = time.monotonic()
    if now - last_progress["t"] < 0.33:
        return  # throttle berlaku untuk SEMUA room!
    last_progress["t"] = now
```

Jika room A aktif, throttle dict menganggap update sudah dikirim, dan room B yang butuh update juga di-throttle padahal belum.

**Fix:**
```python
last_progress = {}  # dict per room_id
async def _on_track_progress(event: TrackProgressEvent):
    room_id = event.room_id
    now = time.monotonic()
    if now - last_progress.get(room_id, 0) < 0.33:
        return
    last_progress[room_id] = now
```

---

### PERF-10: `observer_task` di MPV Tidak Ada Timeout untuk Pending Requests

**Severity:** MEDIUM  
**File:** `engine/mpv_controller.py` — `_get_property()`  
**Dampak Estimasi:** 2 detik timeout sudah ada, tapi pending futures bisa menumpuk

```python
async def _get_property(self, prop: str):
    fut = loop.create_future()
    self._pending[req_id] = fut
    # ...
    try:
        return await asyncio.wait_for(fut, timeout=2.0)
    except asyncio.TimeoutError:
        self._pending.pop(req_id, None)
        return None
```

Timeout 2 detik sudah ada (bagus). Namun jika `_observer_task` mati sebelum response datang, semua pending futures di `_pending` di-cancel di `finally` block — tapi futures yang timeout tidak memiliki cleanup di `finally`. Sudah handled dengan benar, ini hanya catatan observasi.

---

## Estimasi Dampak Keseluruhan

| Area | Dampak | Prioritas |
|---|---|---|
| yt-dlp thread pool tidak limited | CPU spike, Termux crash | HIGH |
| Lyrics syncedlyrics blocking | 1–5s delay | HIGH |
| Radio 4x concurrent search | High resource usage | HIGH |
| SQLite commit per operation | 5–15ms overhead | MEDIUM |
| SponsorBlock linear scan | Negligible | LOW |
| WS broadcast O(N) | 10ms @ 10 clients | LOW |
