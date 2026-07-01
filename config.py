import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("YT_PLAYER_BASE", Path(__file__).parent))

CACHE_DIR = BASE_DIR / "cache" / "mp3"
DB_PATH = BASE_DIR / "data" / "ytgui.db"

if os.name == 'nt':
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
STREAM_URL_TTL_SEC = 21600
# PATCH-YTDLP-RESOLVE-TIMEOUT-01: yt-dlp.get_stream_url() sebelumnya tidak punya batas waktu
YTDLP_RESOLVE_TIMEOUT_SEC = 25

WEB_HOST = os.environ.get("YTGUI_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("YTGUI_PORT", 8765))

ADMIN_USERNAME = os.environ.get("YTGUI_ADMIN_USER", "admin")

TRUSTED_PROXY = os.environ.get("TRUSTED_PROXY", "false").lower() == "true"

IS_PASSWORD_AUTO_GENERATED = False
_password_file = BASE_DIR / "cache" / "admin_password.txt"

if "YTGUI_ADMIN_PASS" in os.environ:
    _raw_env_pass = os.environ["YTGUI_ADMIN_PASS"]
    if _raw_env_pass.startswith("pbkdf2:sha256:"):
        ADMIN_PASSWORD = _raw_env_pass
    else:
        # TASK-1.2: Hash password ENV var agar tidak disimpan sebagai plaintext.
        # Ini wajib setelah TASK-1.1 menghapus plaintext fallback di verify_password.
        from core.security import hash_password
        ADMIN_PASSWORD = hash_password(_raw_env_pass)
else:
    IS_PASSWORD_AUTO_GENERATED = True
    if _password_file.exists():
        with open(_password_file, "r", encoding="utf-8") as f:
            ADMIN_PASSWORD = f.read().strip()
    else:
        import secrets
        from core.security import hash_password

        raw_password = secrets.token_urlsafe(12)
        ADMIN_PASSWORD = hash_password(raw_password)
        _password_file.parent.mkdir(parents=True, exist_ok=True)
        with open(_password_file, "w", encoding="utf-8") as f:
            f.write(ADMIN_PASSWORD)
        try:
            import stat
            _password_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

        print(f"\n==========================================")
        print(f"PASSWORD ADMIN GENERATED: {raw_password}")
        print(f"Harap simpan password ini! Tidak akan ditampilkan lagi.")
        print(f"==========================================\n")
