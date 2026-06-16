# 📋 IMPLEMENTASI PLAN — YT Termux Player Pro v1.0

**Author:** Senior Engineering Review  
**Base PRD:** Bagas Sunandar Hamonangan  
**Target:** Android (Termux) · Python 3.10+ · asyncio  
**Status:** Ready for Sprint Execution

---

## PRINSIP ENGINEERING

> "Build boring infrastructure first. Fancy features are worthless if the event loop blocks."

Setiap fase didesain **incremental & testable**. Tidak ada fase yang bergantung pada fase berikutnya yang belum selesai. Setiap milestone menghasilkan *working software*, bukan hanya skeleton.

---

## FASE 0 — Environment Bootstrap & Tooling (Hari 1–2)

Tujuan: Termux siap 100% sebelum baris kode pertama ditulis.

### 0.1 Instalasi Dependencies Termux

```bash
# Core runtime
pkg update && pkg upgrade -y
pkg install python ffmpeg mpv yt-dlp sqlite termux-api

# Python deps
pip install aiohttp aiofiles rich httpx

# MPRIS support via dbus (jika tersedia di build Termux)
pkg install dbus
pip install dbus-python || echo "fallback: gunakan mpv IPC langsung"

# Validasi versi minimum
python --version        # harus >= 3.10
mpv --version           # harus >= 0.35 (IPC socket support)
yt-dlp --version        # update ke latest selalu
```

### 0.2 Struktur Direktori Proyek

```
~/yt-player/
├── main.py                  # Entry point, bootstrap event loop
├── config.py                # Konstanta global, path, default settings
├── requirements.txt
│
├── core/
│   ├── __init__.py
│   ├── event_bus.py         # Pub/sub internal antar modul
│   ├── state.py             # AppState dataclass (single source of truth)
│   └── exceptions.py        # Custom exceptions hierarki
│
├── engine/
│   ├── __init__.py
│   ├── ytdlp_client.py      # Wrapper async yt-dlp
│   ├── mpv_controller.py    # IPC socket controller
│   ├── queue_manager.py     # PlayQueue + gapless logic
│   └── autoplay.py          # Infinite autoplay / radio mode
│
├── cache/
│   ├── __init__.py
│   ├── db.py                # SQLite async (aiosqlite)
│   ├── schema.sql           # DDL — tidak ditulis inline di Python
│   └── resolver.py          # Local vs stream routing logic
│
├── integrations/
│   ├── __init__.py
│   ├── sponsorblock.py      # SponsorBlock API client
│   ├── lyrics.py            # lrclib.net fetcher
│   └── bluetooth.py         # MPRIS / termux-media-player bridge
│
├── tui/
│   ├── __init__.py
│   ├── dashboard.py         # Rich Live layout root
│   ├── panels/
│   │   ├── now_playing.py   # Panel kiri: info + equalizer
│   │   ├── queue_panel.py   # Panel kanan atas: antrian
│   │   ├── lyrics_panel.py  # Panel kanan bawah: lirik sync
│   │   └── controls.py      # Footer: keyboard hints
│   └── input_handler.py     # Async keyboard reader (aioconsole)
│
├── widgets/
│   └── shortcuts/           # Termux Widget shell scripts
│       ├── play_pause.sh
│       ├── next_track.sh
│       └── volume_up.sh
│
└── tests/
    ├── test_ytdlp_client.py
    ├── test_mpv_controller.py
    ├── test_cache_resolver.py
    └── test_queue_manager.py
```

### 0.3 config.py — Konstanta Global

```python
# config.py
from pathlib import Path

BASE_DIR       = Path.home() / "yt-player"
CACHE_DIR      = BASE_DIR / "cache" / "mp3"
DB_PATH        = BASE_DIR / "cache" / "library.db"
MPV_SOCKET     = "/tmp/mpv-yt-player.sock"
DEFAULT_VOLUME = 80
GAPLESS_PREBUFFER_SEC = 15   # mulai buffer lagu berikut 15 detik sebelum habis
AUTOPLAY_THRESHOLD = 2       # trigger autoplay ketika sisa queue <= 2
SPONSORBLOCK_CATS  = ["sponsor", "intro", "outro", "selfpromo"]
LYRICS_API_BASE    = "https://lrclib.net/api"
```

---

## FASE 1 — Core Engine Backend (Hari 3–7)

### 1.1 AppState — Single Source of Truth

```python
# core/state.py
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto

class PlayerStatus(Enum):
    IDLE = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    BUFFERING = auto()
    ERROR = auto()

@dataclass
class TrackInfo:
    video_id:    str
    title:       str
    artist:      str
    duration:    int           # detik
    thumbnail:   Optional[str] = None
    local_path:  Optional[str] = None   # None = streaming
    stream_url:  Optional[str] = None
    view_count:  Optional[int] = None

@dataclass
class AppState:
    status:         PlayerStatus = PlayerStatus.IDLE
    current_track:  Optional[TrackInfo] = None
    queue:          list[TrackInfo] = field(default_factory=list)
    position:       float = 0.0          # detik
    volume:         int = 80
    is_radio_mode:  bool = False
    lyrics_lines:   list[str] = field(default_factory=list)
    lyrics_index:   int = 0
    error_msg:      Optional[str] = None
```

### 1.2 Event Bus — Decoupled Communication

```python
# core/event_bus.py
import asyncio
from collections import defaultdict
from typing import Callable, Any

class EventBus:
    """
    Lightweight pub/sub. Modul tidak saling import langsung —
    semua komunikasi lewat event. Ini krusial untuk mencegah
    circular imports di arsitektur async.
    """
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable):
        self._subscribers[event].append(handler)

    async def publish(self, event: str, data: Any = None):
        for handler in self._subscribers[event]:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)

# Singleton
bus = EventBus()

# Event names — define sebagai konstanta, jangan hardcode string
TRACK_STARTED    = "track.started"
TRACK_ENDED      = "track.ended"
TRACK_PROGRESS   = "track.progress"
QUEUE_EMPTY      = "queue.empty"
VOLUME_CHANGED   = "volume.changed"
LYRICS_UPDATED   = "lyrics.updated"
ERROR_OCCURRED   = "error.occurred"
SEARCH_RESULTS   = "search.results"
```

### 1.3 yt-dlp Async Client

```python
# engine/ytdlp_client.py
import asyncio
import yt_dlp
from core.state import TrackInfo
from config import CACHE_DIR

class YtDlpClient:
    """
    yt-dlp dijalankan di thread executor karena library-nya synchronous.
    JANGAN pernah panggil yt-dlp langsung di event loop — ini akan
    memblokir seluruh UI dan input selama 2-5 detik.
    """

    _YDL_OPTS_INFO = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "format": "bestaudio/best",
    }

    async def search(self, query: str, max_results: int = 10) -> list[TrackInfo]:
        opts = {**self._YDL_OPTS_INFO,
                "extract_flat": True,
                "playlist_items": f"1:{max_results}"}
        url = f"ytsearch{max_results}:{query}"
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, self._extract_sync, url, opts)
        return [self._to_track(e) for e in results.get("entries", [])]

    async def get_stream_url(self, video_id: str) -> str:
        """Dapatkan direct audio URL (expire ~6 jam, cache di DB saja jika perlu)."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {**self._YDL_OPTS_INFO}
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, self._extract_sync, url, opts)
        # Pilih format terbaik: opus > m4a > webm
        return self._pick_audio_url(info)

    async def download_mp3(self, video_id: str, on_progress=None) -> str:
        """Download ke CACHE_DIR/video_id.mp3. Return path."""
        out_path = CACHE_DIR / f"{video_id}.%(ext)s"
        opts = {
            **self._YDL_OPTS_INFO,
            "format": "bestaudio/best",
            "outtmpl": str(out_path),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "progress_hooks": [on_progress] if on_progress else [],
        }
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._download_sync, video_id, opts)
        return str(CACHE_DIR / f"{video_id}.mp3")

    def _extract_sync(self, url, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _download_sync(self, video_id, opts):
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    def _pick_audio_url(self, info: dict) -> str:
        formats = info.get("formats", [])
        for fmt in reversed(formats):
            if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                return fmt["url"]
        return info["url"]

    def _to_track(self, entry: dict) -> TrackInfo:
        return TrackInfo(
            video_id=entry.get("id", ""),
            title=entry.get("title", "Unknown"),
            artist=entry.get("uploader", "Unknown"),
            duration=entry.get("duration", 0),
            thumbnail=entry.get("thumbnail"),
            view_count=entry.get("view_count"),
        )
```

### 1.4 mpv IPC Controller

```python
# engine/mpv_controller.py
import asyncio, json
from pathlib import Path
from config import MPV_SOCKET
from core.event_bus import bus, TRACK_PROGRESS, TRACK_ENDED

class MpvController:
    """
    Kontrol mpv via Unix socket JSON IPC.
    mpv harus dijalankan dengan: mpv --no-video --idle --input-ipc-server={socket}
    """

    def __init__(self):
        self._reader = None
        self._writer = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._observer_task = None

    async def connect(self):
        for attempt in range(10):
            try:
                self._reader, self._writer = await asyncio.open_unix_connection(MPV_SOCKET)
                self._observer_task = asyncio.create_task(self._observe_events())
                return
            except (FileNotFoundError, ConnectionRefusedError):
                await asyncio.sleep(0.5)
        raise RuntimeError(f"Tidak bisa konek ke mpv socket: {MPV_SOCKET}")

    async def play(self, url_or_path: str):
        await self._command(["loadfile", url_or_path, "replace"])

    async def pause(self):
        await self._set_property("pause", True)

    async def resume(self):
        await self._set_property("pause", False)

    async def toggle_pause(self):
        paused = await self._get_property("pause")
        await self._set_property("pause", not paused)

    async def set_volume(self, vol: int):
        await self._set_property("volume", max(0, min(150, vol)))

    async def get_position(self) -> float:
        return await self._get_property("time-pos") or 0.0

    async def get_duration(self) -> float:
        return await self._get_property("duration") or 0.0

    async def seek(self, seconds: float):
        await self._command(["seek", seconds, "absolute"])

    async def _observe_events(self):
        """Event loop listener untuk mpv events (end-file, time-pos, dll)."""
        # Observe time-pos setiap ~0.5 detik
        await self._command(["observe_property", 1, "time-pos"])
        await self._command(["observe_property", 2, "playback-time"])

        while True:
            try:
                line = await self._reader.readline()
                if not line:
                    break
                msg = json.loads(line.decode())
                await self._handle_event(msg)
            except Exception:
                break

    async def _handle_event(self, msg: dict):
        if "request_id" in msg:
            fut = self._pending.pop(msg["request_id"], None)
            if fut and not fut.done():
                fut.set_result(msg.get("data"))
            return

        event = msg.get("event")
        if event == "property-change" and msg.get("name") == "time-pos":
            await bus.publish(TRACK_PROGRESS, msg.get("data", 0.0))
        elif event == "end-file":
            reason = msg.get("reason", "")
            if reason in ("eof", "stop"):
                await bus.publish(TRACK_ENDED, reason)

    async def _command(self, cmd: list) -> int:
        self._request_id += 1
        req_id = self._request_id
        payload = json.dumps({"command": cmd, "request_id": req_id}) + "\n"
        self._writer.write(payload.encode())
        await self._writer.drain()
        return req_id

    async def _get_property(self, prop: str):
        self._request_id += 1
        req_id = self._request_id
        fut = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        payload = json.dumps({"command": ["get_property", prop], "request_id": req_id}) + "\n"
        self._writer.write(payload.encode())
        await self._writer.drain()
        return await asyncio.wait_for(fut, timeout=2.0)

    async def _set_property(self, prop: str, value):
        await self._command(["set_property", prop, value])
```

### 1.5 Milestone Validasi Fase 1

- [ ] `python main.py` menampilkan dashboard Rich tanpa crash
- [ ] Pencarian mengembalikan hasil dalam < 3 detik tanpa UI freeze
- [ ] `play()` memutar audio via mpv socket
- [ ] `TRACK_PROGRESS` event terpublish setiap ~0.5 detik
- [ ] `TRACK_ENDED` event memicu lagu berikutnya

---

## FASE 2 — Terminal Dashboard (Hari 8–12)

### 2.1 Rich Live Layout Strategy

**Aturan kritis:** Semua update UI harus via `live.update()` dari satu coroutine terpusat. Jangan panggil `console.print()` dari mana saja — ini akan merusak layout Live.

```python
# tui/dashboard.py
import asyncio
from rich.live import Live
from rich.layout import Layout
from rich.console import Console
from core.event_bus import bus, TRACK_PROGRESS, TRACK_ENDED, LYRICS_UPDATED

class Dashboard:
    def __init__(self, state):
        self.state = state
        self.console = Console()
        self._layout = self._build_layout()
        self._live = Live(self._layout, console=self.console,
                          refresh_per_second=4, screen=True)

    def _build_layout(self) -> Layout:
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5),
        )
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        layout["right"].split_column(
            Layout(name="queue"),
            Layout(name="lyrics"),
        )
        return layout

    async def run(self):
        # Subscribe ke events
        bus.subscribe(TRACK_PROGRESS, self._on_progress)
        bus.subscribe(LYRICS_UPDATED, self._on_lyrics)

        with self._live:
            while True:
                self._refresh_all_panels()
                await asyncio.sleep(0.25)   # 4 fps — cukup untuk animasi equalizer

    def _refresh_all_panels(self):
        from tui.panels.now_playing import render_now_playing
        from tui.panels.queue_panel import render_queue
        from tui.panels.lyrics_panel import render_lyrics
        from tui.panels.controls import render_controls

        self._layout["header"].update(self._render_header())
        self._layout["left"].update(render_now_playing(self.state))
        self._layout["queue"].update(render_queue(self.state))
        self._layout["lyrics"].update(render_lyrics(self.state))
        self._layout["footer"].update(render_controls())
```

### 2.2 Animasi Equalizer — Teknik Bar Chart ASCII

```python
# tui/panels/now_playing.py
import math, time
from rich.panel import Panel
from rich.text import Text

_BAR_CHARS = "▁▂▃▄▅▆▇█"

def _equalizer_frame(t: float, n_bars: int = 16) -> str:
    """Pseudo-random animasi equalizer berbasis sine wave berlapis."""
    bars = []
    for i in range(n_bars):
        # Gabungkan beberapa frekuensi untuk efek naturalistik
        phase = (t * 3.7 + i * 0.8) % (2 * math.pi)
        val = (math.sin(phase) + math.sin(t * 7.1 + i * 1.3)) / 2
        normalized = int((val + 1) / 2 * 7)   # 0–7 index
        bars.append(_BAR_CHARS[normalized])
        if (i + 1) % 4 == 0:
            bars.append(" ")
    return "".join(bars)
```

### 2.3 Milestone Validasi Fase 2

- [ ] Layout 3-panel ter-render tanpa flicker
- [ ] Progress bar update real-time dari `TRACK_PROGRESS` event
- [ ] Equalizer animasi berjalan mulus di 4 fps
- [ ] Tidak ada `console.print()` di luar Dashboard

---

## FASE 3 — Smart Caching & Database (Hari 13–17)

### 3.1 Schema SQLite

```sql
-- cache/schema.sql
PRAGMA journal_mode=WAL;   -- penting: WAL mode agar read/write concurrent aman

CREATE TABLE IF NOT EXISTS tracks (
    video_id     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    artist       TEXT,
    duration     INTEGER,
    view_count   INTEGER,
    thumbnail    TEXT,
    local_path   TEXT,           -- NULL = belum didownload
    stream_url   TEXT,           -- cached URL, bisa expire
    stream_url_ts INTEGER,       -- Unix timestamp saat URL didapat
    play_count   INTEGER DEFAULT 0,
    last_played  INTEGER,        -- Unix timestamp
    created_at   INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_local_path ON tracks(local_path) WHERE local_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_last_played ON tracks(last_played DESC);
```

### 3.2 Cache Resolver — Logika Routing

```python
# cache/resolver.py
from cache.db import Database
from engine.ytdlp_client import YtDlpClient
from core.state import TrackInfo
import time

STREAM_URL_TTL = 4 * 3600   # URL YouTube expire ~6 jam, cache 4 jam

class CacheResolver:
    """
    Aturan prioritas (berurutan):
    1. File lokal tersedia & ada di disk → putar lokal
    2. Stream URL masih fresh (< TTL) → pakai cached URL
    3. Fetch URL baru dari yt-dlp → simpan ke DB, putar stream
    """

    def __init__(self, db: Database, ytdlp: YtDlpClient):
        self.db = db
        self.ytdlp = ytdlp

    async def resolve(self, track: TrackInfo) -> str:
        """Return playback URI: path lokal atau stream URL."""
        import os

        # Check local cache
        row = await self.db.get_track(track.video_id)
        if row and row["local_path"] and os.path.isfile(row["local_path"]):
            track.local_path = row["local_path"]
            return row["local_path"]

        # Check cached stream URL freshness
        if row and row["stream_url"] and row["stream_url_ts"]:
            age = time.time() - row["stream_url_ts"]
            if age < STREAM_URL_TTL:
                return row["stream_url"]

        # Fetch fresh URL
        url = await self.ytdlp.get_stream_url(track.video_id)
        await self.db.upsert_track(track, stream_url=url)
        return url
```

### 3.3 Milestone Validasi Fase 3

- [ ] Lagu yang sudah didownload diputar dari lokal (zero network traffic terverifikasi via `nethogs`)
- [ ] Stream URL dikache dan tidak fetch ulang dalam TTL window
- [ ] Download MP3 via `[M]` berhasil dan entry `local_path` terupdate di DB
- [ ] `play_count` dan `last_played` terupdate setiap kali lagu diputar

---

## FASE 4 — Integrasi Advanced (Hari 18–24)

### 4.1 SponsorBlock Integration

```python
# integrations/sponsorblock.py
import aiohttp
from config import SPONSORBLOCK_CATS

SPONSORBLOCK_API = "https://sponsor.ajay.app/api/skipSegments"

async def get_skip_segments(video_id: str) -> list[tuple[float, float]]:
    """Return list of (start, end) dalam detik yang harus di-skip."""
    params = {
        "videoID": video_id,
        "categories": str(SPONSORBLOCK_CATS).replace("'", '"'),
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(SPONSORBLOCK_API, params=params, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [(seg["segment"][0], seg["segment"][1]) for seg in data]
    except Exception:
        pass
    return []

async def apply_skip_segments(mpv, segments: list[tuple[float, float]], current_pos: float):
    """Panggil ini dari TRACK_PROGRESS handler."""
    for start, end in segments:
        if start <= current_pos <= start + 0.6:
            await mpv.seek(end)
            break
```

### 4.2 Lyrics Fetcher

```python
# integrations/lyrics.py
import aiohttp
from config import LYRICS_API_BASE

async def fetch_lyrics(title: str, artist: str, duration: int) -> list[tuple[float, str]]:
    """
    Return list of (timestamp_detik, lyric_line).
    Format LRC: [mm:ss.xx] teks
    """
    url = f"{LYRICS_API_BASE}/get"
    params = {"track_name": title, "artist_name": artist, "duration": duration}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lrc = data.get("syncedLyrics") or data.get("plainLyrics", "")
                    return _parse_lrc(lrc)
    except Exception:
        pass
    return []

def _parse_lrc(lrc_text: str) -> list[tuple[float, str]]:
    import re
    pattern = re.compile(r"\[(\d+):(\d+\.\d+)\](.*)")
    result = []
    for line in lrc_text.splitlines():
        m = pattern.match(line.strip())
        if m:
            minutes, seconds, text = m.groups()
            timestamp = int(minutes) * 60 + float(seconds)
            result.append((timestamp, text.strip()))
    return sorted(result, key=lambda x: x[0])
```

### 4.3 Infinite Autoplay

```python
# engine/autoplay.py
from engine.ytdlp_client import YtDlpClient
from core.event_bus import bus, QUEUE_EMPTY
from config import AUTOPLAY_THRESHOLD

class AutoplayEngine:
    def __init__(self, ytdlp: YtDlpClient, state):
        self.ytdlp = ytdlp
        self.state = state
        bus.subscribe(QUEUE_EMPTY, self._on_queue_low)

    async def _on_queue_low(self, _):
        if not self.state.is_radio_mode:
            return
        if not self.state.current_track:
            return

        query = f"{self.state.current_track.artist} {self.state.current_track.title} similar"
        results = await self.ytdlp.search(query, max_results=5)

        # Filter: jangan tambahkan yang sudah ada di queue
        existing_ids = {t.video_id for t in self.state.queue}
        existing_ids.add(self.state.current_track.video_id)
        new_tracks = [t for t in results if t.video_id not in existing_ids]

        self.state.queue.extend(new_tracks[:3])
```

### 4.4 MPRIS / Bluetooth Support

```bash
# widgets/shortcuts/play_pause.sh
#!/data/data/com.termux/files/usr/bin/bash
# Termux Widget shortcut — kirim perintah ke mpv IPC
echo '{"command":["cycle","pause"]}' | socat - UNIX-CONNECT:/tmp/mpv-yt-player.sock

# widgets/shortcuts/next_track.sh
#!/data/data/com.termux/files/usr/bin/bash
echo '{"command":["playlist-next","force"]}' | socat - UNIX-CONNECT:/tmp/mpv-yt-player.sock
```

```bash
# Aktifkan MPRIS plugin mpv (install mpv-mpris)
# ~/.config/mpv/mpv.conf
script=/data/data/com.termux/files/home/mpv-mpris/mpris.so
```

### 4.5 Milestone Validasi Fase 4

- [ ] SponsorBlock: intro/outro terskip otomatis, verified dengan lagu yang diketahui punya segmen
- [ ] Lirik tersinkronisasi: baris aktif ter-highlight tepat waktu (toleransi ±1 detik)
- [ ] Radio mode: queue otomatis terisi sebelum kosong
- [ ] Tombol headset fisik mengontrol play/pause via MPRIS

---

## TESTING STRATEGY

### Unit Tests

```python
# tests/test_cache_resolver.py
import pytest, asyncio

@pytest.mark.asyncio
async def test_resolver_prioritizes_local():
    """Jika file lokal ada, tidak boleh ada network call."""
    # Mock DB return local_path yang valid
    # Mock ytdlp — pastikan get_stream_url TIDAK dipanggil
    ...

@pytest.mark.asyncio
async def test_resolver_fetches_on_stale_url():
    """URL yang expired harus trigger fetch baru."""
    ...
```

### Integration Tests

```bash
# Smoke test manual — jalankan setelah tiap fase
python -c "
import asyncio
from engine.ytdlp_client import YtDlpClient

async def test():
    client = YtDlpClient()
    results = await client.search('nasi goreng song', max_results=3)
    print(f'Search OK: {len(results)} results')
    print(f'  First: {results[0].title} by {results[0].artist}')

asyncio.run(test())
"
```

---

## RISK REGISTER

| Risiko | Probabilitas | Impact | Mitigasi |
|--------|-------------|--------|----------|
| yt-dlp API break (YouTube update) | Tinggi | Kritis | Pin ke versi stabil + `yt-dlp -U` di startup |
| mpv IPC timeout di device lemah | Sedang | Tinggi | Retry dengan backoff + fallback ke subprocess |
| SponsorBlock API rate limit | Rendah | Rendah | Cache hasil per video_id di DB |
| lrclib.net tidak temukan lirik | Tinggi | Rendah | Graceful degradation: panel lirik kosong, tidak crash |
| Termux MPRIS tidak support di semua ROM | Sedang | Sedang | Fallback: hanya Termux Widget (socat IPC) |
| Stream URL expire saat gapless pre-buffer | Sedang | Tinggi | Pre-buffer 15 menit sebelum habis, bukan 15 detik |

---

## DEFINITION OF DONE

Versi 1.0 dianggap selesai jika:

- [ ] Semua 4 fase milestone terpenuhi
- [ ] Cold start ke lagu pertama < 5 detik
- [ ] Tidak ada UI freeze selama operasi normal
- [ ] Memory usage < 150MB (pantau via `top -p $(pgrep python)`)
- [ ] Berjalan stabil 2 jam tanpa crash di Termux Android 12+
