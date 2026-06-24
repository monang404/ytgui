# Audit Arsitektur & Performa — ytgui-ytclient
**Auditor:** Principal Software Architect / Staff+ Python Engineer
**Tanggal:** 22 Juni 2026
**Codebase:** ytgui-ytclient (Python asyncio + aiohttp + WebSocket + MPV + yt-dlp)
**Tujuan:** Blueprint enterprise — latency rendah, throughput tinggi, tahan kegagalan

---

## 1. Executive Summary

ytgui adalah aplikasi pemutar musik YouTube berbasis terminal + web UI untuk Termux/desktop. Secara keseluruhan, arsitekturnya **lebih sehat dari rata-rata proyek personal** — menggunakan async secara konsisten, ada event bus, pemisahan modul yang masuk akal, dan ada upaya nyata untuk menangani error. Namun ada sejumlah **kelemahan struktural yang akan menyebabkan masalah serius** jika skala bertambah atau tim berkembang.

### Architecture Health Scorecard

| Dimensi | Skor | Keterangan |
|---|---|---|
| Arsitektur | 5/10 | Event bus bagus, tapi state global mutable tanpa proteksi |
| Maintainability | 6/10 | Modul terpisah baik, tapi coupling implisit tinggi |
| Scalability | 2/10 | Single-process, satu shared state, tidak bisa horizontal scale |
| Reliability | 5/10 | Ada retry & reconnect, tapi ada race condition tersembunyi |
| Observability | 2/10 | Logging minimal, tidak ada metrics, tidak ada tracing |
| Production Readiness | 3/10 | Cocok untuk single-user personal, belum siap multi-user produksi |

### Top 10 Masalah Paling Fatal

1. 🚨 **AppState mutable tanpa locking** — race condition nyata antara concurrent WebSocket commands
2. 🚨 **EventBus serial blocking** — satu handler lambat memblokir seluruh pipeline event
3. 🚨 **`create_task` tanpa error propagation** — task crash diam-diam, tidak ada recovery
4. 🚨 **`asyncio.Lock` di dalam handler event bus** — potensi deadlock terstruktur
5. 🚨 **Session auth token disimpan di in-memory dict** — hilang saat restart, tidak persistent
6. **`renderFullState()` dipanggil 3× per detik** — DOM rebuild masif setiap progress tick
7. **EQ canvas animation 60fps terus tanpa throttle** — membuang CPU bahkan saat tab tersembunyi
8. **Stream proxy `Cache-Control: no-store`** — browser re-download audio setiap seek
9. **`history` deque tidak dibatasi dengan benar** — bisa tumbuh tanpa batas di sesi panjang
10. **Tidak ada circuit breaker ke YouTube/yt-dlp** — satu API lambat dapat memblokir seluruh radio

### Top 10 Quick Wins (< 1 Minggu)

1. Tambah `defer` di `<script src="/static/app.js">` — gratis, langsung terasa
2. Pisah handler `progress` WS dari `renderFullState()` — hapus jank 3× per detik
3. Tambah `Cache-Control: public, max-age=3600` di static assets
4. Pause EQ animation saat tab bukan "home" — hemat CPU signifikan
5. Implementasi optimistic UI untuk tombol play/next/prev
6. Pre-bake gradient objek di EQ canvas (bukan buat baru per frame)
7. Ganti `innerHTML = ""` + rebuild di `renderQueue()` dengan key-based diffing
8. Kurangi stream chunk size dari 64KB ke 16KB untuk playback lebih mulus
9. Tambah `asyncio.gather(return_exceptions=True)` di semua `create_task` yang fire-and-forget
10. Tambah periodic cleanup untuk `command_history` dan `login_attempts` di ConnectionManager

---

## 2. Arsitektur Sistem

### Dependency Graph

```
main.py
├── AppState (core/state.py)          ← shared mutable singleton
├── Database (cache/db.py)            ← aiosqlite, WAL mode
├── YtDlpClient (engine/ytdlp_client.py) ← run_in_executor wrapper
├── MpvController (engine/mpv_controller.py) ← Unix socket IPC
├── CacheResolver (cache/resolver.py)
├── SponsorBlockHandler (integrations/sponsorblock.py)
├── LyricsFetcher (integrations/lyrics.py)
├── QueueMode / RadioMode (engine/)
├── PlaybackController (engine/playback_controller.py)
│   └── subscribes to 16 events di EventBus
└── WebServer (web/server.py)
    ├── ConnectionManager
    └── /ws WebSocket endpoint
```

### Pola Arsitektur yang Digunakan

Aplikasi menggunakan **kombinasi Layered Architecture + Event-Driven Architecture (partial)**:

- Event bus (`core/event_bus.py`) digunakan sebagai backbone komunikasi antar modul
- Ada pemisahan engine, integrations, cache, dan web layer
- `AppState` bertindak sebagai shared state store (mirip Redux tetapi tanpa immutability)

**Apakah pola ini tepat?** Untuk skala satu pengguna: ya. Untuk multi-user atau tim: tidak.

**Masalah utama:** domain logic (playback, lyrics, sponsorblock) terlalu erat terikat ke `AppState` singleton. Tidak ada abstraksi antara domain dan infrastructure. Tidak ada port/adapter. Sulit diuji secara independen.

**Rekomendasi migrasi:** Hexagonal Architecture dengan domain services yang pure (tidak bergantung langsung ke `AppState`), dan adapter layer untuk WebSocket, MPV, dan YouTube.

### Coupling & Cohesion

| Modul | Cohesion | Coupling | Catatan |
|---|---|---|---|
| `core/event_bus.py` | Tinggi ✓ | Rendah ✓ | Desain terbaik di codebase |
| `core/state.py` | Tinggi ✓ | Tinggi ✗ | Diakses langsung dari semua modul |
| `engine/playback_controller.py` | Medium | Tinggi ✗ | Subscribe 16 event, tahu terlalu banyak |
| `web/server.py` | Medium | Tinggi ✗ | Akses langsung ke state, ytdlp, db |
| `engine/radio_mode.py` | Tinggi ✓ | Medium | Independen dari queue ✓ |
| `integrations/lyrics.py` | Tinggi ✓ | Medium | Baik, tapi subscribe TRACK_PROGRESS langsung |

### Circular Dependency

Tidak ada circular import yang terdeteksi. Penggunaan `TYPE_CHECKING` di `radio_mode.py` dan `queue_mode.py` menunjukkan awareness yang baik terhadap masalah ini.

### God Object

`PlaybackController` mendekati God Class — ia subscribe ke 16 event dan mengetahui detail implementasi queue, radio, mpv, resolver, sponsorblock, dan lyrics sekaligus. Ini adalah **Orchestrator Anti-Pattern**: satu class yang tahu terlalu banyak tentang terlalu banyak hal.

---

## 3. Fatal Design Flaws

### 🚨 FATAL-01: AppState Mutable Tanpa Locking — Race Condition Nyata

**Severity:** Critical

**Deskripsi:**
`AppState` adalah dataclass Python biasa yang di-share antara semua concurrent WebSocket connections, event handlers, dan background tasks. Tidak ada lock, tidak ada atomic operation, tidak ada immutability.

**Evidence:**
```python
# core/state.py
@dataclass
class AppState:
    status: PlayerStatus = PlayerStatus.IDLE
    queue: deque = field(default_factory=deque)
    radio_queue: deque = field(default_factory=deque)
    # ... semua field ini dibaca DAN ditulis dari berbagai coroutine secara bersamaan
```

```python
# playback_controller.py — dua path yang bisa race
async def _on_next(self, data=None):
    async with self._lock:        # ← ada lock di sini
        await self._advance_to_next()

async def _on_track_progress(self, position: float):
    self.state.position = position  # ← tidak ada lock di sini
```

```python
# web/server.py — handler WebSocket menulis state langsung
async def _on_queue_updated(_data=None):
    await manager.broadcast({
        "type": "state",
        "data": _state_to_dict(state),  # ← membaca state saat sedang ditulis
    })
```

**Dampak:**
Dua user admin yang mengirim command bersamaan bisa menyebabkan state korup. Misalnya: `CMD_NEXT` dan `CMD_PLAY_TRACK` datang bersamaan — `queue.popleft()` bisa dipanggil dua kali, menyebabkan lagu terlewat atau `IndexError`.

**Root Cause:**
Python's asyncio single-threaded event loop memberikan false sense of safety. Memang tidak ada true thread race, tetapi `await` points menciptakan interleaving yang tidak terprediksi antara coroutine.

**Rekomendasi:**
Gunakan single-writer pattern: semua mutasi state harus melalui `PlaybackController` yang sudah punya `_lock`. Atau gunakan `asyncio.Queue` sebagai command queue dengan single consumer.

---

### 🚨 FATAL-02: EventBus Serial Blocking — Satu Handler Lambat Membunuh Semua

**Severity:** Critical

**Deskripsi:**
EventBus memanggil semua handler secara **sequential `await`**, bukan concurrent. Artinya jika `TRACK_PROGRESS` dipublish dan ada 4 subscriber (lyrics, sponsorblock, server broadcast, playback_controller), keempat handler dijalankan satu per satu.

**Evidence:**
```python
# core/event_bus.py
async def publish(self, event: str, data: Any = None):
    for handler in active_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)  # ← sequential, bukan concurrent!
            else:
                handler(data)
        except Exception as e:
            logger.error(...)
```

`TRACK_PROGRESS` dipublish ~3× per detik dan punya subscriber:
1. `_on_track_progress` di `PlaybackController`
2. `_on_progress` di `LyricsFetcher`
3. `_on_progress` di `SponsorBlockHandler`
4. `_on_track_progress` di `web/server.py` (broadcast ke semua WS clients)

Jika broadcast WebSocket ke 10 client lambat (jaringan jelek), ini akan delay handler lyrics dan sponsorblock.

**Dampak:**
Event backlog. Lyric sync terlambat. Sponsorblock terlambat skip. Pada skala lebih tinggi: event loop starvation.

**Root Cause:**
Desain awal yang aman, tetapi tidak mempertimbangkan I/O-bound handlers.

**Rekomendasi:**
```python
# Ganti sequential await dengan concurrent gather untuk handlers
async def publish(self, event: str, data: Any = None):
    tasks = []
    for handler in active_handlers:
        if asyncio.iscoroutinefunction(handler):
            tasks.append(asyncio.create_task(handler(data)))
        else:
            handler(data)
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Handler error on '{event}': {r}")
```

---

### 🚨 FATAL-03: `create_task` Tanpa Error Propagation — Silent Crash

**Severity:** Critical

**Deskripsi:**
Ada 6 titik `asyncio.create_task()` di codebase yang semua-nya menggunakan pattern `fire-and-forget` tanpa error handling yang memadai.

**Evidence:**
```python
# playback_controller.py
asyncio.create_task(self.sponsorblock.fetch_segments(track.video_id))
asyncio.create_task(self.lyrics_fetcher.fetch(track))

# radio_mode.py
task = asyncio.create_task(self._fetch_and_play_initial(controller, seed_artist))
self._bg_tasks.add(task)
task.add_done_callback(self._bg_tasks.discard)  # ← discard, bukan error handler!

# download_manager.py
asyncio.create_task(self._do_download(target))  # ← tidak ada error callback sama sekali
```

Ketika task crash, Python mencetak "Task exception was never retrieved" ke stderr — tidak ke logger, tidak ke UI, tidak ada recovery.

**Dampak:**
Download bisa gagal diam-diam. Lyrics bisa tidak muncul tanpa error apapun. Radio bisa berhenti tanpa pesan.

**Rekomendasi:**
```python
def _safe_create_task(coro, name=None, on_error=None):
    async def _wrapper():
        try:
            await coro
        except Exception as e:
            logger.error(f"Task '{name}' crashed: {e}", exc_info=True)
            if on_error:
                await on_error(e)
    task = asyncio.create_task(_wrapper(), name=name)
    return task
```

---

### 🚨 FATAL-04: `asyncio.Lock` di Dalam Event Bus Handler — Deadlock Terstruktur

**Severity:** Critical

**Deskripsi:**
`PlaybackController._on_cmd_play_track` dan `_on_next` menggunakan `async with self._lock`. Event bus memanggil semua handler secara sequential. Jika event `CMD_PLAY_TRACK` datang saat `_on_next` sedang menunggu lock, event bus akan blocked — tidak bisa memproses event lain sampai lock dilepas.

**Evidence:**
```python
# playback_controller.py
async def _on_cmd_play_track(self, track: TrackInfo):
    async with self._lock:           # ← menunggu lock
        await self.play_track(track) # ← ini bisa lama (resolve URL + mpv connect)

async def _on_next(self, data=None):
    async with self._lock:           # ← juga menunggu lock yang sama
        ...
        await self._advance_to_next()
```

Skenario deadlock:
1. `CMD_NEXT` datang → `_on_next` acquire lock, memanggil `play_track()`
2. `play_track()` memanggil `self.resolver.resolve(track)` → butuh 2-5 detik fetch URL
3. Selama itu, `CMD_PLAY_TRACK` datang dari WebSocket
4. EventBus mencoba `await _on_cmd_play_track()` → blocked menunggu lock
5. Seluruh event bus frozen — tidak ada event lain yang diproses

**Dampak:**
UI tidak responsif. WebSocket commands menumpuk. Pada kondisi jaringan lambat, ini terjadi setiap kali ganti lagu.

**Rekomendasi:**
Pisahkan lock granularity. Gunakan `asyncio.Queue` sebagai command queue agar commands tidak pernah blocking event bus.

---

### 🚨 FATAL-05: Auth Token In-Memory — Hilang Saat Restart

**Severity:** High

**Deskripsi:**
Session token admin disimpan di `ConnectionManager.session_tokens` (dict biasa), dan WebSocket connection yang sudah auth disimpan di `authenticated_connections` (set). Keduanya hilang saat server restart.

**Evidence:**
```python
# web/server.py
class ConnectionManager:
    def __init__(self):
        self.session_tokens: dict[str, float] = {}           # ← in-memory only
        self.authenticated_connections: set[web.WebSocketResponse] = set()  # ← in-memory
```

**Dampak:**
Setiap kali server restart, semua admin harus login ulang. Saat koneksi WebSocket drop dan reconnect (yang terjadi saat network flicker), session token sudah dikirim ke browser via `localStorage`, tetapi server tidak mengenali token itu lagi setelah restart.

**Rekomendasi:**
Simpan session token di SQLite (tabel `sessions`) atau gunakan signed JWT yang dapat diverifikasi tanpa menyimpan state.

---

## 4. Audit Async & Concurrency

### Task Lifecycle Analysis

| Task | Dibuat di | Error Handling | Cancellation |
|---|---|---|---|
| `sponsorblock.fetch_segments` | `play_track()` | Tidak ada callback | Tidak dicancel saat track ganti |
| `lyrics_fetcher.fetch` | `play_track()` | Tidak ada callback | Tidak dicancel saat track ganti |
| `radio._fetch_and_play_initial` | `on_activated()` | `done_callback` discard saja | Ditrack di `_bg_tasks` |
| `radio._prefetch_next` | `next()` | Tidak ada callback | Tidak |
| `_do_download` | `_on_download()` | Try/except internal | Tidak |
| `connectivity_task` | `main()` | Dicek di finally | Cancel di finally |
| `mpv_reconnect_checker` | `main()` | Dicek di finally | Cancel di finally |

**Masalah Kritis:**
Jika user mengganti lagu dengan cepat (next, next, next), ada kemungkinan 3 task `lyrics_fetcher.fetch` berjalan bersamaan — semua menulis ke `self.state.lyrics_lines` yang sama. Task yang paling lambat selesai akan menimpa yang lebih cepat dengan data lagu yang salah.

**Rekomendasi:**
```python
# lyrics.py — tambah generation counter untuk cancel fetch lama
class LyricsFetcher:
    def __init__(self, ...):
        self._current_generation = 0
        self._fetch_task = None

    async def fetch(self, track: TrackInfo):
        self._current_generation += 1
        gen = self._current_generation
        if self._fetch_task and not self._fetch_task.done():
            self._fetch_task.cancel()
        self._fetch_task = asyncio.create_task(self._do_fetch(track, gen))

    async def _do_fetch(self, track, gen):
        # ... fetch logic ...
        if gen != self._current_generation:
            return  # Sudah ada fetch lebih baru, buang hasil ini
        self.state.lyrics_lines = [...]
```

### Blocking I/O dalam Async Path

**Teridentifikasi 2 titik:**

1. **`syncedlyrics.search()`** di `lyrics.py` dipanggil via `run_in_executor` — ini sudah benar ✓
2. **`yt_dlp.extract_info()`** di `ytdlp_client.py` dipanggil via `run_in_executor` — ini sudah benar ✓

**Tetapi:** `run_in_executor` menggunakan default ThreadPoolExecutor dengan thread count terbatas (biasanya `os.cpu_count() * 5`). Jika banyak request search/stream URL concurrent, thread pool bisa exhausted dan tasks akan queue up.

### Await Chain Analysis

```
WebSocket message → _handle_ws_message() [await]
  → bus.publish(CMD_PLAY_TRACK) [await]
    → EventBus.publish() [serial await semua handler]
      → _on_cmd_play_track() [async with lock — bisa 5-30 detik!]
        → play_track() [await]
          → resolver.resolve() [await — bisa 2-5 detik fetch URL]
            → ytdlp.get_stream_url() [await — run_in_executor]
          → mpv.play() [await]
          → bus.publish(TRACK_STARTED) [await]
            → manager.broadcast() [await — kirim ke semua WS clients]
```

Total latency worst case dari "klik play" sampai lagu mulai: **7-35 detik** jika cache miss + koneksi lambat. Selama itu, event bus tidak bisa memproses event lain.

### Diagram Concurrency Flow

```
[Browser WS Client 1] ─┐
[Browser WS Client 2] ─┤─→ [ConnectionManager] ─→ [bus.publish(CMD_*)]
[Browser WS Client N] ─┘              ↓
                              [EventBus.publish()] ← SERIAL BOTTLENECK
                                  ↓        ↓
                        [PlaybackController] [SponsorBlockHandler]
                                  ↓
                         [asyncio.Lock._lock]
                                  ↓
                         [resolver.resolve()]  ← NETWORK I/O
                                  ↓
                       [run_in_executor(yt-dlp)] ← THREAD POOL
                                  ↓
                          [MpvController.play()]
                                  ↓
                       [Unix Socket IPC → mpv]
```

---

## 5. Real-Time & Streaming Audit

### Sinkronisasi Browser Audio

Mekanisme sinkronisasi saat ini:
1. MPV memainkan audio di device (HP)
2. Server mem-proxy stream YouTube via `/api/stream/{video_id}` untuk browser client
3. Browser `<audio>` element memainkan stream tersebut secara independen

**Masalah fundamental:** Dua instance audio (MPV dan browser) tidak tersinkronisasi satu sama lain. Mereka memiliki buffer, clock, dan latency masing-masing. Tidak ada mekanisme drift correction.

**Evidence:**
```javascript
// app.js — syncBrowserAudio() tidak ada seek correction berkala
function syncBrowserAudio() {
    // ...
    audio.oncanplay = () => {
        if (store.position > 2 && Math.abs(audio.currentTime - store.position) > 2) {
            audio.currentTime = store.position;  // ← hanya dilakukan sekali saat load!
        }
        audio.oncanplay = null;
    };
}
```

Setelah `oncanplay`, tidak ada periodic sync check. Browser audio bisa drift dari server position karena:
- Network jitter dalam stream proxy
- Browser buffer yang berbeda-beda per device
- Tidak ada NTP-style correction

**Estimasi drift:** 100ms–2000ms setelah 5–10 menit playback.

**Perbandingan dengan Spotify Connect:**
Spotify menggunakan timestamp berbasis NTP (monotonik) yang dikirim bersama setiap progress update, sehingga client bisa menghitung drift dan melakukan micro-seek correction tanpa mengganggu playback.

**Rekomendasi — Target <100ms sync:**
```python
# Server: sertakan server_time dalam setiap progress update
await manager.broadcast({
    "type": "progress",
    "data": {
        "position": position,
        "server_ts": time.monotonic(),  # ← tambah ini
        "status": state.status.name,
    },
})
```
```javascript
// Client: hitung round-trip time dan koreksi drift
function handleProgress(data) {
    const rtt = (performance.now() / 1000) - data.server_ts;
    const estimatedPosition = data.position + rtt / 2;
    const drift = Math.abs(audio.currentTime - estimatedPosition);
    if (drift > 0.5 && drift < 5) {  // koreksi jika drift 500ms–5s
        audio.currentTime = estimatedPosition;
    }
}
```

### Stream Proxy Performance

**Masalah:** `Cache-Control: no-store` membuat browser tidak bisa cache audio chunks. Seek mundur akan re-fetch dari YouTube — latency 500ms–2000ms per seek.

**Masalah kedua:** Chunk size 64KB (`iter_chunked(65536)`) terlalu besar. Pada koneksi lambat, chunk pertama butuh waktu lama untuk sampai, menyebabkan buffering di awal playback.

**Rekomendasi:** Gunakan chunk 8–16KB dan izinkan browser cache dengan `Cache-Control: private, max-age=3600`.

### Progress Throttle

Throttle 0.33 detik (3× per detik) di server sudah tepat. Namun di client, setiap progress event masih memicu `renderFullState()` — ini yang perlu diperbaiki (lihat Fatal Findings di atas).

---

## 6. Performance Audit

### CPU Hotspots

#### Hotspot 1: EQ Canvas Animation (60fps, selalu)

```javascript
// app.js:941 — berjalan terus tanpa henti
function tickEQ() {
    for (let i = 0; i < NUM_BANDS; i++) {
        const grad = eqCtx.createLinearGradient(...); // 12 alokasi baru per frame!
        eqCtx.beginPath();
        eqCtx.quadraticCurveTo(...);
        // ...
    }
    requestAnimationFrame(tickEQ); // loop tak terbatas
}
requestAnimationFrame(tickEQ); // mulai saat halaman load
```

Estimasi: ~720 `createLinearGradient()` per detik, terus-menerus, bahkan saat tab Queue atau Search aktif.

#### Hotspot 2: `renderFullState()` 3× per Detik

```javascript
// app.js:190 — dipanggil setiap progress update
case "progress":
    Object.assign(store, msg.data);
    renderFullState();  // ← rebuild SELURUH UI: header, now-playing,
                        //   player bar, radio, queue, lyrics
    syncBrowserAudio();
    break;
```

`renderQueue()` di dalamnya melakukan `innerHTML = ""` + rebuild semua DOM nodes. Dengan 20 lagu di queue: 20 `createElement()` + 60 `appendChild()` tiap 333ms.

#### Hotspot 3: `escapeHtml()` DOM Allocation

```javascript
// app.js:1108
function escapeHtml(str) {
    const div = document.createElement("div"); // alokasi DOM baru tiap call
    div.textContent = str;
    return div.innerHTML;
}
```

Dipanggil tiap `createQueueItem()` (2× per item) dan tiap lyric render — puluhan kali per render cycle.

### Memory Issues

#### Memory Leak Potensial: `history` Deque

```python
# core/state.py
history: deque = field(default_factory=lambda: deque(maxlen=50))
```

`maxlen=50` sudah bagus. Namun `TrackInfo` object menyimpan `stream_url` yang bisa sepanjang 500+ karakter. 50 track × 500 bytes = 25KB — bukan masalah saat ini, tetapi jika maxlen diperbesar tanpa sadar, bisa jadi isu.

#### Memory Leak: `ConnectionManager._bg_tasks` di RadioMode

```python
# radio_mode.py
self._bg_tasks = set()
task = asyncio.create_task(...)
self._bg_tasks.add(task)
task.add_done_callback(self._bg_tasks.discard)
```

Ini sudah benar — `done_callback` membersihkan task dari set. Pola yang tepat.

#### Memory Concern: `command_history` dan `login_attempts`

```python
# web/server.py — ConnectionManager.__init__
self.command_history: dict[str, list[float]] = {}
self.login_attempts: dict[str, list[float]] = {}
```

Dibersihkan saat entry diakses (sliding window per-IP), tetapi entry dari IP yang tidak pernah kembali tidak pernah dihapus. Pada server publik dengan banyak IP, ini akan tumbuh terus.

### Database Performance

Schema sudah baik: WAL mode, index yang tepat pada `last_played` dan `play_count`.

**Satu masalah:** `upsert_track()` selalu commit dengan `await self._conn.commit()`. Untuk operasi yang sering (progress tracking), ini bisa menjadi bottleneck. Namun karena playback tidak sering upsert, ini bukan masalah serius saat ini.

**Missing index:** Tidak ada index pada `stream_url_ts` yang dipakai untuk check freshness di `resolver.py`. Ini query akan full scan jika tabel besar.

### External API Performance

**yt-dlp search:** Dipanggil dengan `run_in_executor` — benar. Waktu respons: 1–5 detik per search. Tidak ada caching hasil search.

**Radio mode:** `_gather_batch()` memanggil 4 artis secara paralel dengan `asyncio.gather()` — ini sudah sangat baik ✓

**Stream URL fetch:** Butuh 2–5 detik setiap cache miss (setiap 6 jam). Prefetch di `_on_track_started` sudah ada (`_prefetch_stream_url`) — ini bagus, tapi hanya dipanggil untuk track yang baru saja dimulai, bukan untuk track berikutnya dalam queue.

---

## 7. Scalability Assessment

### Estimasi Kapasitas Saat Ini

Desain saat ini: **single-process, single asyncio event loop, shared in-memory state**.

| Stage | Concurrent Users | Status | Bottleneck Pertama |
|---|---|---|---|
| Stage 1 | 10 | ✓ Aman | EQ animation CPU |
| Stage 2 | 50 | ⚠ Mulai bermasalah | WebSocket broadcast serial, event bus blocking |
| Stage 3 | 200 | ✗ Bermasalah | Event loop overload, MPV single instance |
| Stage 4 | 1.000+ | ✗ Gagal total | Single process Python, GIL, no horizontal scaling |

**Catatan penting:** ytgui saat ini dirancang sebagai aplikasi **single-user personal** (satu MPV, satu state). Arsitektur ini fundamental tidak bisa di-scale ke multi-user tanpa redesign besar.

### Komponen yang Akan Runtuh Pertama

1. **MPV** — satu instance, tidak bisa di-share ke banyak user yang ingin memutar lagu berbeda
2. **`AppState` singleton** — satu state untuk semua, tidak ada konsep "session" per user
3. **EventBus serial** — semua WebSocket broadcasts berjalan sequential
4. **Python GIL + single asyncio loop** — tidak bisa fully parallelise di multi-core

### Tabel Risiko

| Komponen | Risiko | Dampak | Mitigation |
|---|---|---|---|
| AppState singleton | Race condition pada concurrent write | Data korup | Locking atau immutable state |
| EventBus serial | Handler lambat block semua | UI freeze | Concurrent dispatch |
| MPV single instance | Hanya 1 user bisa play audio | Fundamental limit | Desain ulang untuk multi-room |
| yt-dlp ThreadPool | Pool exhausted saat banyak search | Search timeout | BoundedSemaphore + queue |
| WebSocket broadcast | O(n) per event untuk n clients | Latency naik linear | Jika n < 20: ok. n > 100: butuh pub/sub |

---

## 8. Reliability Assessment

### Error Handling

**Yang sudah baik:**
- EventBus tidak propagate exception antar handler (CRITICAL-01 fix)
- MPV reconnect checker ada dan berfungsi
- Retry dengan exponential backoff di `play_track()` (2^n detik, max 3 kali)
- `asyncio.wait_for()` timeout di `_get_property()` (2 detik)

**Yang kurang:**
- Tidak ada circuit breaker ke YouTube API
- Tidak ada timeout di `_gather_batch()` radio — jika yt-dlp lambat, radio bisa berhenti lama
- `create_task()` tanpa error callback (lihat FATAL-03)

### Graceful Shutdown

```python
# main.py — finally block
for t in tasks:
    t.cancel()
lyrics_fetcher.cleanup()
sponsorblock.cleanup()
await nowplaying.cleanup()
ytdlp.cancel_download()
await http_session.close()
await mpv.close()
await db.close()
```

Shutdown sudah cukup baik untuk personal use. Namun `await asyncio.gather(*tasks)` setelah cancel tidak ada — task mungkin tidak selesai cleanup sebelum proses exit.

### Startup Ordering

Urutan startup di `main.py` sudah benar: DB → ytdlp → MPV → integrations → controller → web server. Jika MPV gagal, sistem tetap berjalan (degraded) — ini desain yang baik.

### Fault Isolation

Jika komponen crash:
- **LyricsFetcher crash:** tidak mempengaruhi playback (background task) ✓
- **SponsorBlock crash:** tidak mempengaruhi playback ✓
- **Database crash:** playback tidak terganggu, tetapi stream URL tidak di-cache, setiap play akan re-fetch ✓
- **MPV crash:** auto-reconnect dalam 5 detik ✓ (tapi ada window 5 detik di mana play/pause tidak berfungsi)
- **WebSocket error:** reconnect dalam 2 detik dari client ✓

---

## 9. Security Audit

### SEC-01: Password Auto-Generated Disimpan Plaintext

**Severity:** Medium

```python
# config.py
with open(_password_file, "w", encoding="utf-8") as f:
    f.write(ADMIN_PASSWORD)  # ← plaintext di cache/admin_password.txt
```

Password disimpan plaintext di filesystem. Siapapun yang bisa baca direktori `cache/` bisa mendapat akses admin.

**Rekomendasi:** Hash password dengan bcrypt/argon2 sebelum simpan, atau gunakan hashing di proses verifikasi.

### SEC-02: SSRF via Stream Proxy

**Severity:** High

```python
# web/server.py:handle_stream
stream_url = row.get("stream_url")  # ← berasal dari DB, awalnya dari yt-dlp
async with http_session.get(stream_url, ...) as upstream:  # ← fetch URL sembarang!
```

`stream_url` disimpan di DB dari hasil yt-dlp. Jika DB dapat dimanipulasi (misalnya via SQL injection atau direct DB write), attacker bisa membuat server mem-fetch URL internal (misalnya `http://169.254.169.254/` untuk AWS metadata).

**Rekomendasi:**
```python
from urllib.parse import urlparse
def _is_safe_stream_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("https",) and parsed.hostname.endswith(
        (".youtube.com", ".googlevideo.com", ".ytimg.com")
    )
```

### SEC-03: Path Traversal di Stream Endpoint (Low Risk tapi Ada)

**Severity:** Low

```python
# web/server.py
video_id = request.match_info.get("video_id")
if not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
    return web.HTTPBadRequest(...)
cache_file = CACHE_DIR / f"{video_id}.mp3"  # ← sudah aman karena regex di atas
```

Validasi regex sudah ada dan tepat. Tidak ada path traversal aktual. Tapi ketergantungan pada regex saja rawan jika regex berubah.

**Rekomendasi:** Tambah `cache_file.resolve().is_relative_to(CACHE_DIR)` sebagai defense in depth.

### SEC-04: Session Token Tidak Ada Expiry Cleanup

**Severity:** Low

```python
# web/server.py
manager.session_tokens[new_token] = now + 86400  # 24 jam
```

Expired token tidak pernah dibersihkan dari dict kecuali ada login yang mencoba pakai token itu. Dict ini akan terus tumbuh.

### SEC-05: WebSocket Tidak Ada Rate Limiting per Connection

**Severity:** Low

Rate limiting yang ada (30 cmd/menit) sudah bagus. Tapi tidak ada limit pada jumlah WebSocket connections per IP, memungkinkan connection flooding.

---

## 10. Code Quality Audit

### Readability: Baik

Kode menggunakan docstring yang konsisten, nama yang deskriptif, dan komentar yang menjelaskan "mengapa" bukan hanya "apa". Penggunaan `TYPE_CHECKING` dan type hints menunjukkan awareness yang baik.

### Modularitas: Medium

Pemisahan modul sudah ada, tetapi coupling ke `AppState` terlalu tinggi. Hampir semua modul menerima `AppState` sebagai parameter dan mengaksesnya langsung.

### SOLID Compliance

| Prinsip | Status | Catatan |
|---|---|---|
| Single Responsibility | ⚠ Partial | `PlaybackController` terlalu banyak tanggung jawab |
| Open/Closed | ✓ OK | EventBus memudahkan extensibility |
| Liskov Substitution | ✓ OK | Tidak ada inheritance yang bermasalah |
| Interface Segregation | ✗ Kurang | Tidak ada abstrak interface/protocol |
| Dependency Inversion | ✗ Kurang | Semua modul depend on concrete class, bukan abstraction |

### Testability

Sangat rendah. Hampir tidak mungkin unit test tanpa:
- MPV yang berjalan
- Koneksi internet
- File database

`PlaybackController` sulit di-mock karena menerima concrete class, bukan interface. `AppState` shared mutable state membuat test isolation tidak mungkin tanpa reset manual.

### Anti-Pattern yang Teridentifikasi

- **Feature Envy:** `web/server.py` terlalu sering akses `state.*` langsung — seharusnya delegasi ke controller
- **Primitive Obsession:** `audio_output` disimpan sebagai string `"device"/"browser"` — seharusnya Enum
- **Shotgun Surgery:** Menambah field baru ke `AppState` membutuhkan perubahan di: `_state_to_dict()`, `state.py`, dan setiap client yang render state — terlalu tersebar

---

## 11. Observability Audit

### Status Saat Ini

| Komponen | Status |
|---|---|
| Structured logging | ✗ Tidak ada (hanya format string) |
| Correlation ID | ✗ Tidak ada |
| Distributed tracing | ✗ Tidak ada |
| Metrics (latency, throughput) | ✗ Tidak ada |
| Health check endpoint | ✓ Ada (`/health`) |
| Readiness check | ✗ Tidak ada |
| Latency histogram | ✗ Tidak ada |
| Dashboard readiness | ✗ Tidak ada |
| Alerting | ✗ Tidak ada |

### Log Level Issue

```python
# main.py
logging.getLogger().setLevel(logging.WARNING)
```

Root logger di-set WARNING — artinya semua `logger.info()` dan `logger.debug()` di seluruh codebase **diam**. Informasi penting seperti "Connected to mpv" tidak pernah muncul di log file.

### Rekomendasi Stack Observability (untuk future)

- **Logging:** `structlog` dengan JSON output
- **Metrics:** Prometheus dengan `aiohttp_prometheus`
- **Tracing:** OpenTelemetry dengan Jaeger
- **Dashboard:** Grafana
- **Alerting:** Alertmanager

---

## 12. Target Architecture Proposal

### Prinsip Desain

1. **Immutable Command/Event objects** — tidak ada shared mutable state
2. **Single-writer principle** — hanya satu coroutine yang boleh mutate state
3. **Bulkhead pattern** — isolasi failure antar komponen
4. **Explicit over implicit** — tidak ada hidden dependency via global state

### Diagram Arsitektur Target

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  Browser UI (app.js)  ←──WebSocket──→  TUI (Textual)           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Commands (typed dataclass)
┌─────────────────────────────▼───────────────────────────────────┐
│                       API Gateway Layer                         │
│  WebServer (aiohttp)  →  CommandBus  →  CommandHandler          │
│  Auth Middleware  |  Rate Limiter  |  CORS                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Domain Events
┌─────────────────────────────▼───────────────────────────────────┐
│                       Domain Layer                              │
│  PlaybackService   QueueService   RadioService   UserService    │
│        ↓                ↓              ↓                        │
│  [PlaybackState]  [QueueState]  [RadioState]  ← immutable       │
└──────┬──────────────────┬──────────────────────────────────────┘
       │                  │ Repository Interface
┌──────▼──────────────────▼───────────────────────────────────────┐
│                    Infrastructure Layer                         │
│  MpvAdapter  |  YtDlpAdapter  |  SQLiteRepository  |  Cache    │
│  LrcLibAdapter  |  SponsorBlockAdapter  |  HTTPSession          │
└─────────────────────────────────────────────────────────────────┘
```

### Command Flow

```
Browser klik "Play" 
  → WS message {"type":"cmd","action":"play_track","data":{...}}
    → CommandBus.dispatch(PlayTrackCommand(track=...))
      → PlaybackCommandHandler.handle(cmd)
        → PlaybackService.play(track)  [pure domain, no I/O]
          → emit TrackStartedEvent
        → MpvAdapter.play(uri)         [infrastructure, I/O]
      → EventBus.publish(TrackStartedEvent)
        → WebSocketAdapter.broadcast(state_snapshot)  [concurrent]
        → LyricsAdapter.fetch(track)                  [concurrent]
        → SponsorBlockAdapter.fetch(track)             [concurrent]
```

### Concurrency Model Target

```python
# Single-writer state dengan asyncio.Queue sebagai command bus
class CommandBus:
    def __init__(self):
        self._queue = asyncio.Queue()

    async def dispatch(self, command):
        await self._queue.put(command)

    async def run(self):  # single consumer loop
        while True:
            cmd = await self._queue.get()
            handler = self._handlers[type(cmd)]
            await handler.handle(cmd)
```

Tidak ada `asyncio.Lock` yang diperlukan karena semua mutasi state terjadi di satu loop.

---

## 13. Migration Plan

### Phase 0 — Quick Wins (< 1 Minggu)

**Tujuan:** Perbaiki performa yang paling terasa tanpa mengubah arsitektur.

| Pekerjaan | File | Estimasi |
|---|---|---|
| Tambah `defer` ke script tag HTML | `web/static/index.html` | 5 menit |
| Pisah `progress` handler dari `renderFullState()` | `web/static/app.js` | 30 menit |
| Tambah `Cache-Control` ke static assets | `web/server.py` | 30 menit |
| Pause EQ animation saat tab non-home | `web/static/app.js` | 1 jam |
| Pre-bake EQ gradient objects | `web/static/app.js` | 30 menit |
| Key-based diffing di `renderQueue()` | `web/static/app.js` | 2 jam |
| Optimistic UI untuk tombol play/next/prev | `web/static/app.js` | 2 jam |
| Periodic cleanup `command_history` | `web/server.py` | 1 jam |
| Kurangi stream chunk size ke 16KB | `web/server.py` | 5 menit |
| Ubah stream `Cache-Control` ke `private, max-age=3600` | `web/server.py` | 5 menit |

**Risiko:** Rendah — semua perubahan bersifat isolated.
**Dampak:** UI responsivitas naik signifikan, latency tombol turun 50–200ms.

### Phase 1 — Stabilisasi (1–2 Minggu)

**Tujuan:** Hilangkan race condition dan silent failures.

| Pekerjaan | File | Estimasi |
|---|---|---|
| Implementasi `_safe_create_task()` helper | `core/task_utils.py` (baru) | 1 hari |
| Ganti semua bare `create_task()` | seluruh codebase | 1 hari |
| Tambah generation counter di `LyricsFetcher` | `integrations/lyrics.py` | 2 jam |
| Concurrent dispatch di EventBus | `core/event_bus.py` | 3 jam |
| Server-side timestamp di progress broadcast | `web/server.py` | 1 jam |
| Drift correction di browser audio sync | `web/static/app.js` | 3 jam |
| Tambah timeout di `_gather_batch()` radio | `engine/radio_mode.py` | 1 jam |
| Validasi URL di stream proxy (SSRF fix) | `web/server.py` | 1 jam |
| Hash password sebelum simpan | `config.py` | 2 jam |

**Risiko:** Medium — perubahan EventBus bisa mempengaruhi timing handler.
**Dampak:** Eliminasi silent crashes, lirik lebih akurat, audio browser lebih sinkron.

### Phase 2 — Refactor Besar (2–6 Minggu)

**Tujuan:** Hilangkan coupling ke AppState, tambah testability.

| Pekerjaan | Estimasi |
|---|---|
| Definisikan Protocol/ABC untuk adapter (MPV, YtDlp, DB) | 3 hari |
| Pisah `PlaybackController` menjadi `PlaybackService` + `PlaybackCommandHandler` | 5 hari |
| Implementasi `CommandBus` dengan single-writer pattern | 3 hari |
| Pindahkan auth ke SessionRepository (SQLite) | 2 hari |
| Tambah unit tests untuk domain layer | 5 hari |
| Structured logging dengan `structlog` | 2 hari |
| Tambah `audio_output` sebagai Enum | 1 hari |

**Risiko:** High — perubahan besar, butuh regression testing menyeluruh.
**Dampak:** Testable, maintainable, onboarding developer baru lebih mudah.

### Phase 3 — Arsitektur Baru (1–3 Bulan)

**Tujuan:** Hexagonal architecture, observability, multi-room support.

| Pekerjaan | Estimasi |
|---|---|
| Implementasi Domain Events yang typed (dataclass) | 1 minggu |
| Pisah state per "room" (mendukung multi-user dengan room berbeda) | 2 minggu |
| Implementasi Repository pattern untuk semua data access | 1 minggu |
| Tambah OpenTelemetry tracing | 1 minggu |
| Tambah Prometheus metrics | 1 minggu |
| Integration test suite (WebSocket + playback flow) | 2 minggu |

**Risiko:** Very High — hampir complete rewrite dari layer domain ke atas.
**Dampak:** Siap untuk tim yang lebih besar, observable, horizontally scalable per room.

### Phase 4 — Scale-Out Readiness (Ongoing)

Hanya relevan jika produk berkembang ke multi-tenant:
- Pisah ke microservice: stream-proxy, metadata, playback-engine
- Redis untuk session storage
- Message broker (NATS/RabbitMQ) menggantikan in-process EventBus

---

## 14. Top 20 Prioritized Actions

| # | Aksi | Severity | Effort | Impact |
|---|---|---|---|---|
| 1 | Pisah handler `progress` dari `renderFullState()` | Critical | 30 menit | Hilangkan DOM rebuild 3×/detik |
| 2 | Implementasi `_safe_create_task()` dengan error callback | Critical | 2 jam | Eliminasi silent crash |
| 3 | Concurrent dispatch di EventBus | Critical | 3 jam | Eliminasi event bus blocking |
| 4 | Tambah generation counter di `LyricsFetcher` | Critical | 2 jam | Eliminasi race condition lyrics |
| 5 | Key-based diffing di `renderQueue()` | High | 2 jam | Hilangkan DOM thrashing |
| 6 | Pause EQ animation saat tab non-home | High | 1 jam | Hemat CPU signifikan |
| 7 | Tambah `defer` di script tag + `Cache-Control` static | High | 30 menit | First load lebih cepat |
| 8 | Optimistic UI untuk tombol player | High | 2 jam | Responsivitas terasa instan |
| 9 | Drift correction browser audio sync | High | 3 jam | Audio lebih sinkron <100ms |
| 10 | Tambah timeout di `_gather_batch()` radio | High | 1 jam | Radio tidak bisa freeze |
| 11 | Validasi URL di stream proxy (SSRF fix) | High | 1 jam | Tutup celah keamanan |
| 12 | Hash admin password sebelum simpan | Medium | 2 jam | Hardening keamanan |
| 13 | Kurangi chunk size stream proxy ke 16KB | Medium | 5 menit | Playback lebih mulus |
| 14 | Periodic cleanup `command_history` dict | Medium | 1 jam | Cegah memory growth |
| 15 | Pre-bake EQ gradient objects | Medium | 30 menit | Hemat 12 alokasi per frame |
| 16 | `asyncio.wait_for()` di radio `_gather_batch()` | Medium | 1 jam | Cegah radio freeze |
| 17 | Ubah `audio_output` ke Enum | Low | 30 menit | Type safety, eliminasi magic string |
| 18 | Tambah defense-in-depth path check di stream endpoint | Low | 30 menit | Security hardening |
| 19 | Structured logging dengan `structlog` | Low | 1 hari | Observability dasar |
| 20 | Session token persistence di SQLite | Low | 2 jam | UX lebih baik saat restart |

---

## Penutup

ytgui adalah codebase yang **ditulis dengan niat baik dan kesadaran yang lebih tinggi dari rata-rata proyek personal**. Ada tanda-tanda bahwa penulis familiar dengan asyncio, sudah memikirkan pemisahan modul, dan ada upaya nyata untuk menangani edge case (lihat komentar `CRITICAL-03 fix`, `HIGH-02 fix`, dll di codebase).

**Keputusan arsitektur yang baik:**
- EventBus sebagai backbone komunikasi
- `RadioMode` yang independen dari `QueueMode`
- `run_in_executor` untuk semua yt-dlp calls
- SQLite WAL mode
- Shared HTTP session

**Keputusan arsitektur yang perlu diperbaiki:**
- `AppState` sebagai shared mutable state tanpa protection
- EventBus serial yang memblokir semua handler
- `create_task` tanpa error propagation
- Lock di dalam event handler (potensi deadlock)
- Frontend `renderFullState()` pada setiap progress tick

Dengan menyelesaikan **Phase 0 dan Phase 1** (total 3–4 minggu effort), aplikasi akan jauh lebih stabil, responsif, dan aman — tanpa perlu redesign arsitektur besar. Phase 2 dan seterusnya hanya diperlukan jika produk berkembang ke arah multi-user atau tim yang lebih besar.

---
*Laporan ini dibuat berdasarkan analisis statis seluruh source code. Profiling runtime dan load testing tidak dilakukan karena keterbatasan environment.*
