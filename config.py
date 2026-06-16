import os
from pathlib import Path

# BASE_DIR defaults to current directory for Windows testing, 
# can be overridden by YT_PLAYER_BASE env var
BASE_DIR = Path(os.environ.get("YT_PLAYER_BASE", Path.cwd()))

CACHE_DIR = BASE_DIR / "cache" / "mp3"
DB_PATH = BASE_DIR / "cache" / "library.db"

# Handle Windows compatibility for Unix Sockets
if os.name == 'nt':
    # Windows doesn't support Unix sockets natively in the same way,
    # mpv on Windows supports named pipes instead.
    # Defaulting to a named pipe for Windows testing.
    MPV_SOCKET = os.environ.get("YT_PLAYER_SOCKET", r"\\.\pipe\mpv-yt-player")
else:
    MPV_SOCKET = os.environ.get("YT_PLAYER_SOCKET", "/tmp/mpv-yt-player.sock")

DEFAULT_VOLUME = int(os.environ.get("YT_PLAYER_VOLUME", 80))
GAPLESS_PREBUFFER_SEC = 15
AUTOPLAY_THRESHOLD = 2
SPONSORBLOCK_CATS = ["sponsor", "intro", "outro", "selfpromo"]
LYRICS_API_BASE = "https://lrclib.net/api"
