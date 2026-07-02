#!/usr/bin/env bash
# patchlog.sh — Professional terminal logging patch for ytgui
# Idempotent: safe to run multiple times
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# 0. LOCATE PROJECT ROOT
# ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT=""

# Try to find project root by looking for main.py
for candidate in "$SCRIPT_DIR" "$SCRIPT_DIR/ytgui-main" "$(pwd)" "$(pwd)/ytgui-main"; do
    if [ -f "$candidate/main.py" ] && [ -f "$candidate/core/log_config.py" ]; then
        PROJECT_ROOT="$candidate"
        break
    fi
done

if [ -z "$PROJECT_ROOT" ]; then
    echo "ERROR: Cannot find project root (main.py + core/log_config.py not found)." >&2
    echo "Place patchlog.sh next to main.py or inside the project directory." >&2
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────"
echo " YTGUI PATCHLOG — Professional Terminal Logger"
echo "────────────────────────────────────────────────────────"
echo " Project root : $PROJECT_ROOT"
echo ""

# ─────────────────────────────────────────────────────────────
# 1. BACKUP
# ─────────────────────────────────────────────────────────────
BACKUP_DIR="$PROJECT_ROOT/.backup_patchlog"
mkdir -p "$BACKUP_DIR"

backup_file() {
    local src="$1"
    local rel="${src#$PROJECT_ROOT/}"
    local dst="$BACKUP_DIR/$rel"
    mkdir -p "$(dirname "$dst")"
    if [ -f "$src" ] && [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        echo "  backed up: $rel"
    fi
}

echo "[1/8] Backing up files..."
FILES_TO_PATCH=(
    "core/log_config.py"
    "main.py"
    "server/app.py"
    "server/handlers/websocket.py"
    "server/handlers/event_listeners.py"
    "server/handlers/http.py"
    "server/services/stream_prefetch.py"
    "engine/mpv_controller.py"
    "engine/playback/controller.py"
    "engine/playback/track_loader.py"
    "engine/radio_engine.py"
    "engine/download_manager.py"
    "engine/ytdlp_client.py"
    "cache/db.py"
    "cache/resolver.py"
    "plugins/lyrics.py"
    "plugins/notifications.py"
    "plugins/sponsorblock.py"
    "core/task_utils.py"
    "core/event_bus.py"
    "core/command_bus.py"
    "engine/command_router.py"
)
for rel in "${FILES_TO_PATCH[@]}"; do
    backup_file "$PROJECT_ROOT/$rel"
done
echo ""

# ─────────────────────────────────────────────────────────────
# 2. WRITE core/log_config.py  (full replacement)
# ─────────────────────────────────────────────────────────────
echo "[2/8] Patching core/log_config.py ..."

cat > "$PROJECT_ROOT/core/log_config.py" << 'PYEOF'
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
PYEOF

echo "  done."
echo ""

# ─────────────────────────────────────────────────────────────
# 3. PATCH main.py
#    - Replace print startup steps with styled output
#    - Add STATS updates for WebSocket connect/disconnect
# ─────────────────────────────────────────────────────────────
echo "[3/8] Patching main.py ..."

MAIN="$PROJECT_ROOT/main.py"

# Check for idempotency marker
if grep -q "PATCHLOG_APPLIED" "$MAIN" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    # Replace the 5-step print block with styled version
    python3 - <<'PYEOF' "$MAIN"
import sys, re

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Add idempotency marker after first import block
marker = "# PATCHLOG_APPLIED\n"
if marker not in src:
    src = marker + src

# Replace print startup steps
src = src.replace(
    'print("  [1/5] Membuka database perpustakaan...")',
    'sys.stderr.write("\\033[90m  [1/5]\\033[0m Membuka database perpustakaan...\\n")'
)
src = src.replace(
    'print("  [2/5] Menginisialisasi YT-DLP Engine...")',
    'sys.stderr.write("\\033[90m  [2/5]\\033[0m Menginisialisasi YT-DLP Engine...\\n")'
)
src = src.replace(
    'print("  [3/5] Menghubungkan ke audio player (MPV)...")',
    'sys.stderr.write("\\033[90m  [3/5]\\033[0m Menghubungkan ke audio player (MPV)...\\n")'
)

# Replace the big print banner block with a compact one
banner_old = 'print(f"=====================================================")'
if banner_old in src:
    # Find the entire banner section and replace it
    old_banner = '''        print(f"=====================================================")
        print(f"|   YTGUI Web Server                                |")
        print(f"|   Client : {url_client:<37} |")
        print(f"|   Admin  : {url_admin:<37} |")'''
    new_banner = r'''        sys.stderr.write(
            f"\n\033[1;32m{'─'*54}\033[0m\n"
            f"  \033[1m▸ ytgui\033[0m  Web Server\n"
            f"  Client : \033[36m{url_client}\033[0m\n"
            f"  Admin  : \033[36m{url_admin}\033[0m\n"
        )'''
    src = src.replace(old_banner, new_banner)

    old_cred = '''        if IS_PASSWORD_AUTO_GENERATED:
            print(f"|                                                   |")
            print(f"|   Kredensial Mode Admin:                          |")
            print(f"|   User: {ADMIN_USERNAME:<40} |")
            print(f"|   Pass: (lihat cache/admin_password.txt)          |")
        print(f"====================================================="'''
    new_cred = '''        if IS_PASSWORD_AUTO_GENERATED:
            sys.stderr.write(
                f"  User   : \033[33m{ADMIN_USERNAME}\033[0m\\n"
                f"  Pass   : \033[33m(lihat cache/admin_password.txt)\033[0m\\n"
            )
        sys.stderr.write(f"\033[1;32m{'─'*54}\033[0m\\n\\n"'''
    src = src.replace(old_cred, new_cred)

# Ensure sys is imported
if "import sys" not in src:
    src = "import sys\n" + src

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 4. PATCH server/app.py — disable aiohttp access logger
# ─────────────────────────────────────────────────────────────
echo "[4/8] Patching server/app.py (disable aiohttp access log) ..."

APP="$PROJECT_ROOT/server/app.py"
if grep -q "PATCHLOG_APPLIED" "$APP" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    python3 - <<'PYEOF' "$APP"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = "# PATCHLOG_APPLIED\n" + src

# In run_server, disable access_log by patching AppRunner
old = "    runner = web.AppRunner(app)"
new = (
    "    import logging as _l\n"
    "    _l.getLogger('aiohttp.access').setLevel(_l.CRITICAL + 1)\n"
    "    runner = web.AppRunner(app, access_log=None)"
)
src = src.replace(old, new)

# In run_server, change logger.info to stderr write
src = src.replace(
    'logger.info(f"Web server running on http://{host}:{port}")',
    'import sys as _sys; _sys.stderr.write(f"\\033[32mserver  ✓ listening\\033[0m  http://{host}:{port}\\n")'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 5. PATCH server/handlers/websocket.py — compact ws logs + STATS
# ─────────────────────────────────────────────────────────────
echo "[5/8] Patching server/handlers/websocket.py ..."

WS="$PROJECT_ROOT/server/handlers/websocket.py"
if grep -q "PATCHLOG_APPLIED" "$WS" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    python3 - <<'PYEOF' "$WS"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = "# PATCHLOG_APPLIED\n" + src

# Add STATS import at top after existing imports
stats_import = "from core.log_config import STATS as _LOG_STATS\n"
if stats_import not in src:
    src = src.replace(
        "logger = structlog.get_logger(__name__)",
        "logger = structlog.get_logger(__name__)\n" + stats_import
    )

# Patch connect log
src = src.replace(
    'logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")',
    '_LOG_STATS.clients = len(self.active_connections)\n'
    '        _LOG_STATS.is_playing = True if _LOG_STATS.current_track != "—" else _LOG_STATS.is_playing\n'
    '        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}", clients=len(self.active_connections))'
)

# Patch disconnect log
src = src.replace(
    'logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")',
    '_LOG_STATS.clients = len(self.active_connections)\n'
    '        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}", clients=len(self.active_connections))'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 6. PATCH engine/playback/controller.py — STATS for track events
# ─────────────────────────────────────────────────────────────
echo "[6/8] Patching engine/playback/controller.py ..."

PC="$PROJECT_ROOT/engine/playback/controller.py"
if grep -q "PATCHLOG_APPLIED" "$PC" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    python3 - <<'PYEOF' "$PC"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = "# PATCHLOG_APPLIED\n" + src

stats_import = "from core.log_config import STATS as _LOG_STATS\n"
if stats_import not in src:
    src = src.replace(
        "logger = structlog.get_logger(__name__)",
        "logger = structlog.get_logger(__name__)\n" + stats_import
    )

# After state.status = PlayerStatus.PLAYING, update STATS
src = src.replace(
    "self.state.status = PlayerStatus.PLAYING\n                self._retry_count = 0",
    "self.state.status = PlayerStatus.PLAYING\n"
    "                self._retry_count = 0\n"
    "                _LOG_STATS.is_playing = True\n"
    "                _LOG_STATS.current_track = track.title[:50] if track and track.title else '—'\n"
    "                _LOG_STATS.inc('songs_played')"
)

# On track ended / stop
src = src.replace(
    "self.state.status = PlayerStatus.IDLE",
    "self.state.status = PlayerStatus.IDLE\n            _LOG_STATS.is_playing = False"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 7. PATCH engine/radio_engine.py — standardise _log usage
#    radio_engine uses stdlib logging (_log), not structlog
# ─────────────────────────────────────────────────────────────
echo "[7/8] Patching engine/radio_engine.py ..."

RE="$PROJECT_ROOT/engine/radio_engine.py"
if grep -q "PATCHLOG_APPLIED" "$RE" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    python3 - <<'PYEOF' "$RE"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = "# PATCHLOG_APPLIED\n" + src

# Switch to structlog for consistency
if "import structlog" not in src:
    src = src.replace("import logging\n", "import logging\nimport structlog\n")

# Replace _log = logging.getLogger with structlog
src = src.replace(
    "_log = logging.getLogger(__name__)",
    "_log = structlog.get_logger(__name__)"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 8. PATCH engine/ytdlp_client.py — inline _log → structlog
# ─────────────────────────────────────────────────────────────
echo "[8/8] Patching engine/ytdlp_client.py ..."

YT="$PROJECT_ROOT/engine/ytdlp_client.py"
if grep -q "PATCHLOG_APPLIED" "$YT" 2>/dev/null; then
    echo "  already patched (skipping)"
else
    python3 - <<'PYEOF' "$YT"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

src = "# PATCHLOG_APPLIED\n" + src

# The file uses an inline import of logging inside get_stream_url.
# Replace with structlog at module level.
if "import structlog" not in src:
    src = "import structlog\n" + src

old_inline = (
    "        import logging as _logging\n"
    "        _log = _logging.getLogger(__name__)\n"
)
new_inline = "        _log = structlog.get_logger(__name__)\n"
src = src.replace(old_inline, new_inline)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("  done.")
PYEOF
fi
echo ""

# ─────────────────────────────────────────────────────────────
# 9. PATCH server/services/stream_prefetch.py — timeout stats
# ─────────────────────────────────────────────────────────────

SP="$PROJECT_ROOT/server/services/stream_prefetch.py"
if ! grep -q "PATCHLOG_APPLIED" "$SP" 2>/dev/null; then
    python3 - <<'PYEOF' "$SP"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
src = "# PATCHLOG_APPLIED\n" + src
stats_import = "from core.log_config import STATS as _LOG_STATS\n"
if stats_import not in src:
    src = src.replace(
        "logger = structlog.get_logger(__name__)",
        "logger = structlog.get_logger(__name__)\n" + stats_import
    )
src = src.replace(
    'logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")',
    '_LOG_STATS.inc("timeouts") if "timeout" in str(e).lower() or "Timeout" in str(e) else None\n'
    '            logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")'
)
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
PYEOF
fi

# ─────────────────────────────────────────────────────────────
# 10. PATCH server/handlers/http.py — silence OPTIONS/static noise
# ─────────────────────────────────────────────────────────────

HTTP="$PROJECT_ROOT/server/handlers/http.py"
if ! grep -q "PATCHLOG_APPLIED" "$HTTP" 2>/dev/null; then
    python3 - <<'PYEOF' "$HTTP"
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
src = "# PATCHLOG_APPLIED\n" + src
with open(path, "w", encoding="utf-8") as f:
    f.write(src)
PYEOF
fi

# ─────────────────────────────────────────────────────────────
# 11. Ensure logs/ directory exists in project
# ─────────────────────────────────────────────────────────────
mkdir -p "$PROJECT_ROOT/logs"
touch "$PROJECT_ROOT/logs/.gitkeep"

# Add logs/ to .gitignore if not already there
GITIGNORE="$PROJECT_ROOT/.gitignore"
if [ -f "$GITIGNORE" ] && ! grep -q "^logs/" "$GITIGNORE" 2>/dev/null; then
    echo "logs/" >> "$GITIGNORE"
fi

# ─────────────────────────────────────────────────────────────
# 12. Try to install psutil (optional — status bar RAM/CPU only).
#     NOT added to requirements.txt: on Termux/Android there is often
#     no prebuilt wheel, so `pip install -r requirements.txt` would
#     fail entirely. We attempt a best-effort install here instead;
#     if it fails, log_config.py already runs fine without it.
# ─────────────────────────────────────────────────────────────
if ! python3 -c "import psutil" >/dev/null 2>&1; then
    echo "[optional] Trying to install psutil (RAM/CPU in status bar)..."
    if pip install --quiet psutil >/dev/null 2>&1; then
        echo "  psutil installed."
    else
        echo "  psutil not available on this system (e.g. Termux without a"
        echo "  compiler) — status bar will run without RAM/CPU numbers."
    fi
fi

# ─────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────
echo "────────────────────────────────────────────────────────"
echo " PATCHLOG COMPLETE"
echo ""
echo " Changes applied:"
echo "  ✓ core/log_config.py    — full ANSI renderer + status bar + summary"
echo "  ✓ main.py               — styled startup output"
echo "  ✓ server/app.py         — aiohttp access log disabled"
echo "  ✓ server/handlers/websocket.py — ws ● / ○ log format + STATS"
echo "  ✓ engine/playback/controller.py — track play STATS"
echo "  ✓ engine/radio_engine.py — stdlib→structlog"
echo "  ✓ engine/ytdlp_client.py — inline log→structlog"
echo "  ✓ server/services/stream_prefetch.py — timeout STATS"
echo "  ✓ logs/app.log          — full log destination"
echo ""
echo " Backups saved to: .backup_patchlog/"
echo ""
echo " Run: ./start.sh   or   python main.py"
echo "────────────────────────────────────────────────────────"
echo ""
