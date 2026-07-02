"""
Professional terminal logger for ytgui.
Replaces the default structlog renderer with a compact, ANSI-coloured format.
Suppresses aiohttp access log spam and static-file noise.
Writes full logs to logs/app.log for debugging.
"""
import sys
import os
import logging
import logging.handlers
import time
import threading
from pathlib import Path

# psutil is optional: it fails to install on many Termux/Android setups
# (no prebuilt wheel, needs a C compiler). The status bar simply shows
# no RAM/CPU numbers when it's unavailable, instead of crashing the app.
try:
    import psutil
except ImportError:
    psutil = None

# ── ANSI colours ────────────────────────────────────────────
_R  = "\033[0m"
_G  = "\033[32m"     # green
_Y  = "\033[33m"     # yellow
_RE = "\033[31m"     # red
_B  = "\033[34m"     # blue
_GY = "\033[90m"     # grey
_C  = "\033[36m"     # cyan
_W  = "\033[1m"      # bold/white
_BG = "\033[1;32m"   # bold green

# ── Spinner frames ───────────────────────────────────────────
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# ── Global stats counter (for summary + status bar) ─────────
class _Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.songs_played = 0
        self.errors = 0
        self.timeouts = 0
        self.clients = 0
        self.current_track = "—"
        self.status = "Idle"
        self.queue_size = 0
        self.is_playing = False

    def inc(self, field, n=1):
        with self.lock:
            setattr(self, field, getattr(self, field) + n)

STATS = _Stats()

# ── Status bar ───────────────────────────────────────────────
_status_bar_active = False
_status_bar_thread = None

def _status_bar_worker():
    """Renders a live status bar at the bottom of the terminal without spamming."""
    proc = psutil.Process(os.getpid()) if psutil else None
    while _status_bar_active:
        try:
            if proc is not None:
                ram_mb = int(proc.memory_info().rss / 1024 / 1024)
                cpu = proc.cpu_percent(interval=None)
            else:
                ram_mb = 0
                cpu = 0.0
        except Exception:
            ram_mb = 0
            cpu = 0.0

        with STATS.lock:
            clients = STATS.clients
            track = STATS.current_track
            is_playing = STATS.is_playing
            queue = STATS.queue_size

        status_icon = "🎵" if is_playing else "⏸ "
        status_text = "Playing" if is_playing else "Paused"
        if STATS.status == "Idle":
            status_icon = "💤"
            status_text = "Idle"

        line = (
            f"\033[s"                           # save cursor
            f"\033[999;1H"                      # move to last line
            f"\033[2K"                          # clear line
            f"{_GY}────────────────────────────────────────────────────────{_R}\n"
            f"\033[2K"
            f" {_W}▸ ytgui{_R}  "
            f"{_BG}🟢 Ready{_R}  "
            f"👤 {_C}{clients}{_R} client{'s' if clients != 1 else ''}  "
            f"{status_icon} {_G}{status_text}{_R}  "
            f"Queue {_Y}{queue}{_R}  "
            f"RAM {_GY}{ram_mb} MB{_R}  "
            f"CPU {_GY}{cpu:.0f}%{_R}"
            f"\033[u"                            # restore cursor
        )
        sys.stderr.write(line)
        sys.stderr.flush()
        time.sleep(5)

def start_status_bar():
    global _status_bar_active, _status_bar_thread
    if _status_bar_active:
        return
    if psutil is None:
        return  # psutil not installed — status bar disabled (RAM/CPU hidden)
    _status_bar_active = True
    _status_bar_thread = threading.Thread(target=_status_bar_worker, daemon=True, name="status_bar")
    _status_bar_thread.start()

def stop_status_bar():
    global _status_bar_active
    _status_bar_active = False

# ── Summary printer ──────────────────────────────────────────
def _summary_worker():
    while True:
        time.sleep(600)  # every 10 minutes
        with STATS.lock:
            songs   = STATS.songs_played
            errors  = STATS.errors
            timeouts = STATS.timeouts
            clients  = STATS.clients
        line = (
            f"\n{_GY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{_R}\n"
            f"{_W} SUMMARY{_R}\n"
            f" {_G}Songs played{_R} : {songs}\n"
            f" {_RE}Errors      {_R} : {errors}\n"
            f" {_Y}Timeouts    {_R} : {timeouts}\n"
            f" {_C}Clients     {_R} : {clients}\n"
            f"{_GY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{_R}\n"
        )
        sys.stderr.write(line)
        sys.stderr.flush()

_summary_thread = threading.Thread(target=_summary_worker, daemon=True, name="summary")

# ── Spinner context ──────────────────────────────────────────
class Spinner:
    def __init__(self, label: str = ""):
        self.label = label
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        idx = 0
        while not self._stop.is_set():
            frame = SPINNER_FRAMES[idx % len(SPINNER_FRAMES)]
            sys.stderr.write(f"\r{_GY}{frame}{_R} {self.label} ")
            sys.stderr.flush()
            time.sleep(0.1)
            idx += 1
        sys.stderr.write("\r\033[2K")
        sys.stderr.flush()

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)

# ── Custom log renderer ──────────────────────────────────────
_NOISE_PATHS = frozenset({
    "/static/", "/favicon.ico", "/manifest.json",
    "/sw.js", "/robots.txt",
})
_NOISE_METHODS = frozenset({"OPTIONS"})
_NOISE_CODES = frozenset({"304", "302", "301"})

def _is_noise(event: str) -> bool:
    ev = event or ""
    for p in _NOISE_PATHS:
        if p in ev:
            return True
    for m in _NOISE_METHODS:
        if ev.startswith(m + " "):
            return True
    for c in _NOISE_CODES:
        if f" {c}" in ev or ev.strip() == c:
            return True
    if '"OPTIONS ' in ev:
        return True
    return False

def _fmt_time() -> str:
    return time.strftime("%H:%M:%S")

def _module_tag(name: str) -> str:
    """Return short coloured module tag."""
    n = (name or "app").split(".")[-1]
    short = n[:7].ljust(7)
    colour_map = {
        "websocket": _C,
        "handler":   _C,
        "ws_handle": _C,
        "controll":  _G,
        "radio_en":  _B,
        "download":  _Y,
        "db":        _GY,
        "resolver":  _GY,
        "prefetch":  _GY,
        "mpv_cont":  _B,
        "stream_p":  _GY,
        "lyrics":    _C,
        "sponsorb":  _GY,
        "notifica":  _GY,
        "task_uti":  _GY,
        "event_bu":  _GY,
        "command_":  _GY,
    }
    col = _GY
    for k, v in colour_map.items():
        if n.startswith(k[:4]):
            col = v
            break
    return f"{col}{short}{_R}"

# ── Semantic rewrite rules ───────────────────────────────────
import re as _re

def _rewrite_event(name: str, level: str, event: str, extra: dict) -> tuple[str, str]:
    """
    Returns (symbol+colour_prefix, rewritten_message).
    Applies semantic rules for ws/stream/player/cache/retry/timeout/error.
    """
    ev = event or ""
    lev = (level or "").lower()

    # WebSocket connected / disconnected
    if "websocket connected" in ev.lower() or ("connect" in ev.lower() and "client" in ev.lower()):
        n = extra.get("clients", "")
        STATS.inc("clients") if "connected" in ev.lower() else None
        if n:
            STATS.clients = int(str(n))
        return f"{_G}●{_R}", f"ws      {_G}● connected{_R}  (clients: {n})"

    if "websocket disconnected" in ev.lower() or ("disconnect" in ev.lower() and "client" in ev.lower()):
        n = extra.get("clients", "")
        if n:
            STATS.clients = int(str(n))
        return f"{_GY}○{_R}", f"ws      {_GY}○ disconnected{_R}  (clients: {n})"

    if "websocket error" in ev.lower():
        STATS.inc("errors")
        return f"{_RE}⚠{_R}", f"ws      {_RE}⚠ error{_R}"

    # Stream start
    m = _re.search(r"play(?:ing|back|ed)?[:\s]+(.+)", ev, _re.IGNORECASE)
    if m and "stream" in name.lower() or "memutar" in ev or "playing" in ev.lower():
        title = m.group(1).strip() if m else ev
        STATS.is_playing = True
        STATS.current_track = title[:50]
        STATS.inc("songs_played")
        return f"{_G}▶{_R}", f"stream  {_G}▶{_R} {title[:60]}"

    if "track started" in ev.lower() or "trackstarted" in ev.lower():
        title = extra.get("track", ev)
        STATS.is_playing = True
        STATS.current_track = str(title)[:50]
        STATS.inc("songs_played")
        return f"{_G}▶{_R}", f"stream  {_G}▶{_R} {str(title)[:60]}"

    # Player finished / autoplay
    if "track ended" in ev.lower() or "autoplay" in ev.lower() or "finished" in ev.lower():
        STATS.is_playing = False
        return f"{_B}■{_R}", f"player  {_B}■ finished{_R}"

    # Prefetch / cache success
    if "prefetch" in ev.lower() or "berhasil prefetch" in ev.lower() or "pre-fetch" in ev.lower():
        vid = extra.get("video_id", "")
        return f"{_G}✓{_R}", f"cache   {_G}✓ prefetched{_R}  {vid}"

    if "eviction" in ev.lower() or "stale" in ev.lower():
        return f"{_G}✓{_R}", f"cache   {_G}✓ evicted stale{_R}"

    if "database initialized" in ev.lower():
        return f"{_G}✓{_R}", f"db      {_G}✓ ready{_R}"

    if "web server running" in ev.lower():
        return f"{_G}✓{_R}", f"server  {_G}✓ listening{_R}"

    if "eventbus subscriptions" in ev.lower():
        return f"{_G}✓{_R}", f"bus     {_G}✓ subscriptions set up{_R}"

    if "shutdown" in ev.lower():
        STATS.is_playing = False
        return f"{_GY}■{_R}", f"app     {_GY}■ shutdown{_R}"

    if "sponsorblock" in ev.lower() and "segment" in ev.lower():
        n = extra.get("segments", "")
        return f"{_G}✓{_R}", f"sponsor {_G}✓ segments{_R} {n}"

    if "lyrics" in ev.lower() and ("fetched" in ev.lower() or "lines" in ev.lower()):
        return f"{_G}✓{_R}", f"lyrics  {_G}✓ loaded{_R}"

    if "download sukses" in ev.lower() or "download selesai" in ev.lower():
        title = ev.split(":", 1)[-1].strip() if ":" in ev else ev
        return f"{_G}✓{_R}", f"dl      {_G}✓ done{_R}  {title[:50]}"

    if "memulai download" in ev.lower():
        title = ev.split(":", 1)[-1].strip() if ":" in ev else ev
        return f"{_Y}⠸{_R}", f"dl      {_Y}⠸ start{_R}  {title[:50]}"

    if "reconnect" in ev.lower() and "mpv" in ev.lower() and lev == "warning":
        return f"{_Y}⚠{_R}", f"mpv     {_Y}⚠ reconnecting…{_R}"

    if "connected to mpv" in ev.lower() or "reconnect ke mpv berhasil" in ev.lower():
        return f"{_G}✓{_R}", f"mpv     {_G}✓ connected{_R}"

    if "mpv observer loop ended" in ev.lower():
        return f"{_Y}⚠{_R}", f"mpv     {_Y}⚠ connection lost{_R}"

    # timeout → warning
    if "timeout" in ev.lower():
        STATS.inc("timeouts")
        module = name.split(".")[-1][:8] if name else "app"
        return f"{_Y}⚠{_R}", f"{module:<8}{_Y}⚠ timeout{_R}"

    # retry
    m2 = _re.search(r"retry[:\s]*(\d+)\s*/\s*(\d+)", ev, _re.IGNORECASE)
    if m2:
        return f"{_Y}⚠{_R}", f"retry   {_Y}{m2.group(1)}/{m2.group(2)}{_R}"

    if "retry" in ev.lower() and lev == "warning":
        module = name.split(".")[-1][:8] if name else "app"
        return f"{_Y}⚠{_R}", f"{module:<8}{_Y}⚠ retry{_R}"

    # generic warning
    if lev == "warning":
        module = name.split(".")[-1][:8] if name else "app"
        short = ev[:80]
        return f"{_Y}⚠{_R}", f"{module:<8}{_Y}⚠{_R} {short}"

    # generic error → Error Card
    if lev in ("error", "critical"):
        STATS.inc("errors")
        return f"{_RE}⚠{_R}", None  # signal: print card

    # generic info / debug
    short = ev[:100]
    return f"{_GY}·{_R}", short

def _print_error_card(name: str, event: str, extra: dict):
    reason = event or "unknown"
    retry_info = extra.get("retry", "")
    track_info = extra.get("track", extra.get("video_id", ""))
    exc = extra.get("exc_info", "")

    # Try to extract track/reason from event string
    m = _re.search(r"track[:\s]+(.+?)(?:\||$)", event, _re.IGNORECASE)
    if m:
        track_info = m.group(1).strip()
    m2 = _re.search(r"(?:error|failed|gagal)[:\s]+(.+?)(?:\n|$)", event, _re.IGNORECASE)
    if m2:
        reason = m2.group(1).strip()[:80]

    sys.stderr.write(
        f"\n{_RE}────────────────────────────────────────────{_R}\n"
        f"{_RE}{_W}⚠ ERROR{_R}  [{name.split('.')[-1][:20]}]\n\n"
    )
    if track_info:
        sys.stderr.write(f"  Track\n  {_W}{track_info}{_R}\n\n")
    sys.stderr.write(f"  Reason\n  {_RE}{reason}{_R}\n")
    if retry_info:
        sys.stderr.write(f"\n  Retry\n  {_Y}{retry_info}{_R}\n")
    sys.stderr.write(f"{_RE}────────────────────────────────────────────{_R}\n\n")
    sys.stderr.flush()

# ── Core renderer ────────────────────────────────────────────
class _CompactRenderer:
    """structlog processor: renders compact ANSI log to stderr."""

    def __call__(self, logger, method, event_dict):
        ts = event_dict.pop("timestamp", _fmt_time())
        level = event_dict.pop("level", method or "info")
        event = event_dict.pop("event", "")
        name = event_dict.pop("logger", "") or (logger.name if hasattr(logger, 'name') else "")

        # Drop noise
        debug_mode = os.environ.get("YTGUI_DEBUG", "").lower() in ("1", "true", "yes")
        if not debug_mode and _is_noise(str(event)):
            return ""  # suppress

        extra = {k: v for k, v in event_dict.items() if k not in ("exc_info",)}

        sym, msg = _rewrite_event(name, level, str(event), extra)

        if msg is None:  # error card
            _print_error_card(name, str(event), event_dict)
            return ""

        tag = _module_tag(name)
        line = f"{_GY}{ts}{_R} {tag} {sym} {msg}"
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
        return ""  # prevent default handler from double-printing

# ── File formatter (full, no ANSI) ──────────────────────────
class _FileFormatter(logging.Formatter):
    _ANSI_RE = _re.compile(r"\033\[[0-9;]*m")

    def format(self, record):
        msg = super().format(record)
        return self._ANSI_RE.sub("", msg)

# ── Public setup ─────────────────────────────────────────────
def setup_logging():
    from config import BASE_DIR
    import structlog

    # Ensure logs/ dir
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"

    # File handler — full, no ANSI
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_FileFormatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler — routes through structlog renderer above
    # (actual writes happen inside _CompactRenderer; we use NullHandler here)
    null_handler = logging.NullHandler()

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Remove any existing handlers (idempotent)
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.addHandler(file_handler)
    root.addHandler(null_handler)

    # Suppress aiohttp access log completely
    logging.getLogger("aiohttp.access").setLevel(logging.CRITICAL + 1)
    logging.getLogger("aiohttp.server").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.web").setLevel(logging.WARNING)

    # Suppress other common noisy loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _CompactRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Start summary thread
    if not _summary_thread.is_alive():
        _summary_thread.start()

    # Start status bar
    start_status_bar()
