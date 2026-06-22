import os
from pathlib import Path

# BASE_DIR defaults to the project root
# can be overridden by YT_PLAYER_BASE env var
BASE_DIR = Path(os.environ.get("YT_PLAYER_BASE", Path(__file__).parent))

CACHE_DIR = BASE_DIR / "cache" / "mp3"
DB_PATH = BASE_DIR / "cache" / "library.db"

# Handle Windows compatibility for Unix Sockets
if os.name == 'nt':
    # Windows doesn't support Unix sockets natively in the same way,
    # mpv on Windows supports named pipes instead.
    # Defaulting to a named pipe for Windows testing.
    MPV_SOCKET = os.environ.get("YT_PLAYER_SOCKET", r"\\.\pipe\mpv-yt-player")
else:
    socket_dir = BASE_DIR / "cache" / "sockets"
    socket_dir.mkdir(parents=True, exist_ok=True)
    _raw_socket = os.environ.get("YT_PLAYER_SOCKET", str(socket_dir / "mpv-yt-player.sock"))
    _socket_path = Path(_raw_socket).resolve()
    _allowed_prefix = BASE_DIR.resolve()
    if not str(_socket_path).startswith(str(_allowed_prefix)):
        import warnings
        warnings.warn(f"YT_PLAYER_SOCKET '{_raw_socket}' di luar BASE_DIR — menggunakan default")
        _socket_path = socket_dir / "mpv-yt-player.sock"
    MPV_SOCKET = str(_socket_path)

DEFAULT_VOLUME = int(os.environ.get("YT_PLAYER_VOLUME", 80))
GAPLESS_PREBUFFER_SEC = 15
AUTOPLAY_THRESHOLD = 2
SPONSORBLOCK_CATS = ["sponsor", "intro", "outro", "selfpromo"]
LYRICS_API_BASE = "https://lrclib.net/api"

# Web Server
WEB_HOST = os.environ.get("YTGUI_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("YTGUI_PORT", 8765))

# Web Security
ADMIN_USERNAME = os.environ.get("YTGUI_ADMIN_USER", "bagasfm")
ADMIN_PASSWORD = os.environ.get("YTGUI_ADMIN_PASS", "bagasradio2626@")
