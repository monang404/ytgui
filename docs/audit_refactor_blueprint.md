# AUDIT REFACTOR BLUEPRINT — YTGUI Phase 3

---

## 1. Current Architecture

```
main.py                    ← entry point, God bootstrap
├── config.py              ← ISSUE: side effects at import
├── core/
│   ├── event_bus.py       ← ISSUE: global singleton `bus`
│   ├── command_bus.py     ← ISSUE: global singleton `command_bus`
│   ├── room_manager.py    ← multi-room OK, tapi pakai global bus
│   ├── state.py           ← clean
│   ├── ports.py           ← clean
│   ├── security.py        ← ISSUE: plaintext fallback
│   └── ...
├── engine/
│   ├── playback_controller.py ← clean, good orchestration
│   ├── mpv_controller.py      ← ISSUE: hardcode global bus
│   ├── ytdlp_client.py        ← clean
│   ├── download_manager.py    ← ISSUE: signature mismatch
│   └── ...
├── cache/
│   ├── db.py              ← ISSUE: no write lock, error path
│   └── resolver.py        ← clean
├── web/
│   └── server.py          ← ISSUE: god file, auth/rate-limit mixed in
├── integrations/
│   ├── lyrics.py          ← ISSUE: global bus subscribe
│   └── sponsorblock.py    ← ISSUE: global bus subscribe
└── services/
    └── discover_service.py ← ISSUE: accesses private _conn
```

---

## 2. Critical Problems

### P1 — Global EventBus (KRITIS)
Satu `bus` singleton dipakai semua room. Event dari room A men-trigger handler room B. Ini adalah bug arsitektur mendasar yang membuat multi-room fitur secara efektif broken.

### P2 — Security Holes (KRITIS)
Plaintext password fallback, `/metrics` tanpa auth, unauth `next` bypass, `room_id` tidak divalidasi.

### P3 — Cross-cutting Resource Issues (HIGH)
Duplicate `aiohttp.ClientSession`, MPV reconnect pakai socket global, `TermuxNowPlaying` thread leak, `RadioMode` orphan tasks.

### P4 — `web/server.py` God File (MEDIUM)
Auth, rate limiting, routing, event bridging semua di satu file 570 baris. Sulit di-test dan di-maintain.

### P5 — Config Side Effects (MEDIUM)
`config.py` melakukan I/O, print ke stdout, dan generate secrets saat diimport. Sulit di-test.

---

## 3. Target Architecture

```
main.py                    ← thin: setup logging, load config, call bootstrap
startup/
└── bootstrap.py           ← orchestrate room, server, task creation

config/
├── settings.py            ← pure constants, no side effects
└── secrets.py             ← password loading/generation (explicit, called once)

core/
├── event_bus.py           ← class EventBus (no singleton!)
├── command_bus.py         ← class CommandBus (no singleton!)
├── room_manager.py        ← Room dengan per-room EventBus dan CommandBus
├── state.py               ← unchanged
├── ports.py               ← unchanged
└── security.py            ← remove plaintext fallback

engine/
├── playback_controller.py ← inject EventBus via constructor
├── mpv_controller.py      ← inject EventBus via constructor, fix socket path
├── ytdlp_client.py        ← add dedicated ThreadPoolExecutor
├── download_manager.py    ← fix signature, inject per-room EventBus
└── ...

cache/
├── db.py                  ← add write lock, fix error path
└── resolver.py            ← unchanged

web/
├── server.py              ← thin: register routes, create runner
├── auth.py                ← login, session, rate limiting
├── ws_handler.py          ← WebSocket message dispatch
├── event_bridge.py        ← EventBus → WebSocket bridging
└── stream_proxy.py        ← stream proxy handler

integrations/
├── lyrics.py              ← inject per-room EventBus
└── sponsorblock.py        ← inject per-room EventBus
```

---

## 4. Refactor Plan

---

### Phase 1: Critical Security Fixes
**Effort:** 1–2 hari  
**Impact:** Eliminasi semua kerentanan security kritis

**1.1 — Fix `verify_password` plaintext fallback**
```python
# core/security.py
def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password.startswith("pbkdf2:sha256:"):
        # Untuk backward compat: jika hash ada tanda tangan pbkdf2, verify.
        # Jika tidak, return False — jangan accept plaintext.
        return False
    # ... pbkdf2 verify
```

**1.2 — Hash password ENV var di startup**
```python
# main.py atau startup/bootstrap.py
from config import ADMIN_PASSWORD
if not ADMIN_PASSWORD.startswith("pbkdf2:"):
    from core.security import hash_password
    ADMIN_PASSWORD_HASHED = hash_password(ADMIN_PASSWORD)
else:
    ADMIN_PASSWORD_HASHED = ADMIN_PASSWORD
```

**1.3 — Proteksi `/metrics`**
```python
async def handle_metrics(request):
    if not _is_metrics_allowed(request):
        return web.HTTPForbidden()
    # ...
```

**1.4 — Validasi `room_id`**
```python
MAX_ROOMS = 10
ROOM_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

room_id = request.query.get("room", "default")
if not ROOM_ID_RE.match(room_id):
    return web.HTTPBadRequest(text="Invalid room_id")
if room_id not in room_manager.rooms and len(room_manager.rooms) >= MAX_ROOMS:
    return web.HTTPTooManyRequests()
```

**1.5 — Hapus unauth `next` bypass** (atau pertahankan dengan scope lebih sempit)

---

### Phase 2: Stabilization (Bug Fixes)
**Effort:** 2–3 hari  
**Impact:** Eliminasi bug concurrency dan resource leak

**2.1 — Fix MPV reconnect socket path**
```python
# Di MpvController.connect() — ganti MPV_SOCKET dengan self.socket_path
if os.path.exists(self.socket_path):  # bukan MPV_SOCKET
    break
```

**2.2 — Fix `DownloadManager` signature**
```python
async def _on_download(self, room_id: str, track: TrackInfo | None = None):
    target = track or self.state.current_track
```

**2.3 — Lock `_on_track_ended`**
```python
async def _on_track_ended(self, event: TrackEndedEvent):
    async with self._lock:
        reason = event.reason
        # ...
```

**2.4 — Reset `_retry_count` di `_on_stop`**
```python
async def _on_stop(self, _data=None):
    self._retry_count = 0
    # ...
```

**2.5 — Cancel `RadioMode._bg_tasks` di `on_deactivated`**

**2.6 — Fix `TermuxNowPlaying` thread cleanup**

**2.7 — Fix `Database` error path di `init()`**

**2.8 — Fix `db.conn` vs `db._conn` di health check**

**2.9 — Eviction untuk `login_attempts` dan `command_history`**

**2.10 — Close duplicate `http_session`**

---

### Phase 3: Architecture Cleanup
**Effort:** 3–5 hari  
**Impact:** Multi-room benar-benar isolated, testability meningkat drastis

**3.1 — Per-room EventBus**

Ini adalah perubahan terbesar. Setiap `Room` membuat `EventBus()` instance sendiri. Semua komponen dalam Room menerima `event_bus` via constructor injection:

```python
class Room:
    def __init__(self, room_id, db, ytdlp, http_session):
        self.room_id = room_id
        self.event_bus = EventBus()  # BUKAN global bus!
        
        self.mpv = MpvController(
            socket_path=f"/tmp/mpv-socket-{room_id}",
            event_bus=self.event_bus  # inject!
        )
        self.lyrics_fetcher = LyricsFetcher(
            self.state, session=http_session, event_bus=self.event_bus
        )
        self.sponsorblock = SponsorBlockHandler(
            self.mpv, state=self.state, session=http_session, event_bus=self.event_bus
        )
        self.controller = PlaybackController(
            self.room_id, self.event_bus, ...  # inject!
        )
```

`web/server.py` perlu subscribe ke **setiap room's event_bus** saat room dibuat:

```python
async def on_room_created(room: Room):
    room.event_bus.subscribe(TrackStartedEvent, lambda e: _on_track_started(e, room))
    room.event_bus.subscribe(TrackProgressEvent, lambda e: _on_track_progress(e, room))
    # ...
```

**3.2 — Pisahkan `web/server.py`**

**3.3 — Config tanpa side effects**

**3.4 — `TrackInfo.from_db_row()` classmethod**

**3.5 — Database write lock**

---

### Phase 4: Performance & Scalability
**Effort:** 2–3 hari  
**Impact:** Lebih stabil di Termux, lebih responsif saat Radio Mode aktif

**4.1 — Dedicated ThreadPoolExecutor untuk yt-dlp**
```python
class YtDlpClient:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=2)
```

**4.2 — Semaphore untuk radio batch search**
```python
_RADIO_SEARCH_SEM = asyncio.Semaphore(2)
```

**4.3 — Timeout untuk syncedlyrics**
```python
lrc = await asyncio.wait_for(
    loop.run_in_executor(None, syncedlyrics.search, search_query),
    timeout=5.0
)
```

**4.4 — Per-room progress throttle**

**4.5 — `_TITLE_NOISE_WORDS` → `frozenset`**

**4.6 — DB write batching untuk play_track_started**

---

## Estimasi Effort dan Impact

| Phase | Effort | Risk Eliminasi | Testability | Scalability |
|---|---|---|---|---|
| Phase 1: Security | 1–2 hari | 🔴 3 critical | Tidak berubah | Tidak berubah |
| Phase 2: Stabilization | 2–3 hari | 🟠 7 high bugs | Sedikit meningkat | Tidak berubah |
| Phase 3: Architecture | 3–5 hari | 🟡 Cross-room bugs | Meningkat signifikan | Meningkat signifikan |
| Phase 4: Performance | 2–3 hari | Tidak ada | Tidak berubah | Meningkat |
| **Total** | **8–13 hari** | | | |

---

## Quick Wins (< 30 menit masing-masing)

1. `_TITLE_NOISE_WORDS` → `frozenset` (1 baris)
2. Reset `_retry_count` di `_on_stop` (1 baris)
3. Fix `db.conn` → `db._conn` di health check (1 baris)
4. Tambah `shlex.quote` di termux script (2 baris)
5. Fix `last_progress` per-room dict (5 baris)
6. Cancel `_bg_tasks` di `RadioMode.on_deactivated` (3 baris)
