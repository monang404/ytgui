# AUDIT CODE QUALITY — YTGUI Phase 3

Diurutkan berdasarkan ROI Refactor Tertinggi

---

## CQ-01: `web/server.py` — God File (ROI: SANGAT TINGGI)

**File:** `web/server.py` (24KB, ~570 baris)  
**Masalah:** Satu file menangani:
- Route registration
- WebSocket connection management
- Authentication logic
- Rate limiting logic
- Event-to-WebSocket bridging
- Business logic (prefetch stream URL)
- Stream proxy

**Dampak Maintainability:** Setiap perubahan kecil ke auth atau routing memerlukan navigasi file besar. Test sulit karena semua fungsi nested di dalam `create_app()`.

**Refactor Target:**
```
web/
  server.py         ← hanya route registration + runner
  auth.py           ← login, session, rate limiting
  ws_handler.py     ← WebSocket message dispatch
  event_bridge.py   ← EventBus → WebSocket
  stream_proxy.py   ← handle_stream logic
```

---

## CQ-02: `config.py` — Side Effect at Import (ROI: TINGGI)

**File:** `config.py`  
**Masalah:** Config file dengan side effects: membaca file, print ke stdout, generate secrets, melakukan import bersyarat.

```python
# Semua ini terjadi saat `import config` dijalankan:
if _password_file.exists():
    with open(_password_file, "r") as f:
        ADMIN_PASSWORD = f.read().strip()
else:
    import secrets
    raw_password = secrets.token_urlsafe(12)
    ADMIN_PASSWORD = hash_password(raw_password)
    # ... print ke stdout
```

**Dampak:** Sulit di-test (setiap test yang import config akan trigger side effect). Sulit di-mock. Sulit di-override untuk environment berbeda.

**Refactor:**
```python
# config.py — hanya konstanta
ADMIN_USERNAME = os.environ.get("YTGUI_ADMIN_USER", "admin")
_RAW_ADMIN_PASSWORD = os.environ.get("YTGUI_ADMIN_PASS")

# Pindahkan logika ke AppConfig class atau startup function
class AppConfig:
    @classmethod
    def load(cls) -> "AppConfig":
        # ... logika baca/generate password
```

---

## CQ-03: Duplikasi Logic `TrackInfo` Construction (ROI: TINGGI)

**Files:** `cache/db.py`, `services/discover_service.py`, `web/server.py` (`_dict_to_track`)

Konstruksi `TrackInfo` dari dict/row dilakukan manual di 3 tempat:

```python
# cache/db.py
return TrackInfo(
    video_id=row["video_id"], title=row["title"], artist=row["artist"],
    duration=row["duration"], thumbnail=row["thumbnail"], ...
)

# services/discover_service.py — duplikasi identik
d = dict(row)
tracks.append(TrackInfo(
    video_id=d["video_id"], title=d["title"], artist=d["artist"], ...
))

# web/server.py
return TrackInfo(
    video_id=data.get("video_id"), title=data.get("title", "Unknown"), ...
)
```

**Fix:** Tambahkan classmethod ke `TrackInfo`:
```python
@dataclass
class TrackInfo:
    # ...
    
    @classmethod
    def from_db_row(cls, row) -> "TrackInfo":
        return cls(video_id=row["video_id"], title=row["title"], ...)
    
    @classmethod
    def from_dict(cls, data: dict) -> "TrackInfo":
        return cls(video_id=data.get("video_id"), title=data.get("title", "Unknown"), ...)
```

---

## CQ-04: Long Function `_handle_ws_message` (ROI: MEDIUM-TINGGI)

**File:** `web/server.py`  
**Estimasi Panjang:** ~120 baris, 15+ elif branches

Fungsi dispatch WebSocket command adalah satu fungsi besar dengan `if action == "search": ... elif action == "play_track": ... elif action == "toggle_pause": ...` yang tumbuh linear setiap ada command baru.

**Refactor:**
```python
_ACTION_HANDLERS = {
    "search": handle_search,
    "play_track": handle_play_track,
    "toggle_pause": lambda *a: command_bus.execute(CMD_TOGGLE_PAUSE, a[5]),
    # ...
}

async def _handle_ws_message(msg, ws, ...):
    action = msg.get("action", "")
    handler = _ACTION_HANDLERS.get(action)
    if handler:
        await handler(data, ws, room_id, ytdlp, ...)
```

---

## CQ-05: Dead Code — `core/observability.py` `setup_tracing()` Jarang Dipakai

**File:** `core/observability.py`  
**Masalah:** OpenTelemetry `ConsoleSpanExporter` didefinisikan dan `tracer` diinisialisasi, tapi span hanya dipakai di `CommandBus`. Tidak ada export ke Jaeger atau OTLP collector.

ConsoleSpanExporter mengirim span ke stdout — ini noise di production. Di Termux, ini bisa menjadi bottleneck I/O jika banyak command dieksekusi.

**Fix:** Jadikan tracing opsional:
```python
def setup_tracing():
    if not os.environ.get("YTGUI_TRACING_ENABLED"):
        return trace.get_tracer("ytplayer.noop")  # noop tracer
    # ... setup real exporter
```

---

## CQ-06: `DownloadManager` Tidak Expose Room Context

**File:** `engine/download_manager.py`  
**Masalah:** `DownloadManager` dibuat satu instance untuk default room tapi `CMD_DOWNLOAD` diregistrasi di global `command_bus`. Jika ada multi-room, semua download request ke semua room diteruskan ke satu `DownloadManager` yang terikat ke `default` room state.

Ini adalah **architectural dead code** untuk skenario multi-room.

---

## CQ-07: Circular Import Potensial — `core/room_manager.py`

**File:** `core/room_manager.py` baris 34  
```python
async def __init__(self, ...):
    # ...
    from core.event_bus import bus  # ← deferred import di dalam method
    self.volume_service = VolumeService(bus, ...)
```

Import dilakukan di dalam method `__init__` (sebenarnya di `Room.__init__`). Ini bisa menandakan circular import yang dipecahkan dengan deferred import — teknik yang valid tapi bisa menjadi masalah jika dependency graph berubah.

**Verifikasi:** Tidak ada circular import nyata yang ditemukan saat ini, tapi patut diperhatikan.

---

## CQ-08: `TermuxNowPlaying` — Tidak Handle `pathlib` Import (Bug Kecil)

**File:** `integrations/termux_notification.py` baris ~100  
```python
pathlib_p = __import__("pathlib").Path(p)  # ← aneh
```

`pathlib` sudah diimport di seluruh file ini (via `from config import BASE_DIR` yang menggunakan Path). Seharusnya:
```python
from pathlib import Path
# ...
pathlib_p = Path(p)
```

---

## CQ-09: `AppState.conn` vs `Database._conn` — Naming Inconsistency

**File:** `web/server.py` `handle_health()` baris ~220  
```python
db_status = "connected" if db.conn else "disconnected"  # ← attribute "conn" tidak ada!
```

`Database` menggunakan `self._conn` (private). Akses `db.conn` akan selalu `None` atau raise `AttributeError` → health check selalu menampilkan "disconnected" bahkan saat DB berfungsi.

**Fix:**
```python
# Di Database class:
@property
def conn(self):
    return self._conn

# Atau di server.py:
db_status = "connected" if getattr(db, '_conn', None) else "disconnected"
```

---

## Ringkasan ROI Refactor

| # | Item | Effort | Impact | ROI |
|---|---|---|---|---|
| 1 | Split `web/server.py` | Medium | High (testability, maintainability) | TINGGI |
| 2 | Fix `db.conn` bug | Low | High (health check benar) | SANGAT TINGGI |
| 3 | Fix `config.py` side effects | Medium | Medium | TINGGI |
| 4 | `TrackInfo.from_db_row()` classmethod | Low | Medium (less duplication) | TINGGI |
| 5 | Long function `_handle_ws_message` | Medium | Medium | MEDIUM |
| 6 | Optional tracing | Low | Low | MEDIUM |
| 7 | `_TITLE_NOISE_WORDS` ke frozenset | Very Low | Low | MEDIUM |
