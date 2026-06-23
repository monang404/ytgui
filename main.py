import asyncio
import logging
import stat
import sys
import aiohttp
from logging.handlers import RotatingFileHandler
from core.state import AppState, PlayerStatus
from core.event_bus import bus, LOG_MESSAGE, CMD_QUIT
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.queue_mode import QueueMode
from engine.radio_mode import RadioMode
from engine.volume_service import VolumeService
from engine.download_manager import DownloadManager
from engine.playback_controller import PlaybackController
from integrations.termux_notification import TermuxNowPlaying
from core.task_utils import safe_create_task
from config import BASE_DIR, WEB_HOST, WEB_PORT

log_path = BASE_DIR / "ytplayer.log"
_log_handler = RotatingFileHandler(
    log_path,
    maxBytes=1 * 1024 * 1024,
    backupCount=2,
    encoding="utf-8"
)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
))
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger().addHandler(_log_handler)

try:
    log_path.touch(exist_ok=True)
    log_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
except OSError:
    pass

async def main():
    state = AppState()
    
    # 1. Initialize DB
    print("  [1/5] Membuka database perpustakaan...")
    db = Database()
    await db.init()
    
    # 2. Initialize Core Engine
    print("  [2/5] Menginisialisasi YT-DLP Engine...")
    ytdlp = YtDlpClient()
    
    print("  [3/5] Menghubungkan ke audio player (MPV)...")
    mpv = MpvController()
    try:
        await mpv.connect()
    except Exception as e:
        logging.getLogger(__name__).error(f"mpv not available: {e}")
        state.error_msg = (
            "MPV tidak ditemukan. Jalankan: pkg install mpv (Termux) "
            "atau install MPV dan tambahkan ke PATH (Windows/Linux)."
        )
        state.status = PlayerStatus.ERROR
    
    # 3. Shared HTTP session
    http_session = aiohttp.ClientSession()
    
    # 4. Initialize Integrations & Resolver
    print("  [4/5] Memuat modul SponsorBlock & Lyrics Fetcher...")
    resolver = CacheResolver(db, ytdlp)
    sponsorblock = SponsorBlockHandler(mpv, state=state, session=http_session)
    lyrics_fetcher = LyricsFetcher(state, session=http_session)
    
    # 5. Engine Modes & Services
    queue_mode = QueueMode()
    radio_mode = RadioMode(ytdlp, state)
    volume_service = VolumeService(bus, mpv, state)
    download_manager = DownloadManager(bus, state, ytdlp)
    
    # 6. Initialize Playback Controller
    print("  [5/5] Menyusun Playback Controller...")
    controller = PlaybackController(
        bus, state, mpv, resolver, sponsorblock, lyrics_fetcher, queue_mode, radio_mode
    )

    # 6.5 Termux now-playing notification (no-op outside Termux)
    nowplaying = TermuxNowPlaying(bus, state)
    await nowplaying.start()

    # 7. Search Handler removed (moved to SearchTab)

    # Connectivity Check
    async def check_connectivity():
        while True:
            try:
                async with http_session.get(
                    "https://connectivitycheck.gstatic.com/generate_204",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as r:
                    state.is_online = (r.status == 204)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                state.is_online = False
            except Exception as e:
                logging.getLogger(__name__).warning(f"Connectivity check unexpected error: {e}")
                state.is_online = False
            await asyncio.sleep(30)

    connectivity_task = safe_create_task(check_connectivity(), name="connectivity_checker")
    tasks = [connectivity_task]
    
    # 7.5 MPV auto-reconnect checker
    async def mpv_reconnect_checker():
        while True:
            await asyncio.sleep(5)
            if not getattr(mpv, "is_connected", False) and state.status != PlayerStatus.ERROR:
                logging.getLogger(__name__).warning("MPV terputus! Mencoba reconnect...")
                try:
                    await mpv.close()
                except Exception:
                    pass
                try:
                    await mpv.connect()
                    if state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED) and state.current_track:
                        uri = await resolver.resolve(state.current_track)
                        await mpv.play(uri)
                        await mpv.seek(state.position)
                        if getattr(state, "audio_output", "device") == "browser":
                            await mpv.set_volume(0)
                        else:
                            await mpv.set_volume(state.volume)
                        if state.status == PlayerStatus.PLAYING:
                            await mpv.resume()
                except Exception as e:
                    logging.getLogger(__name__).error(f"MPV reconnect failed: {e}")

    tasks.append(safe_create_task(mpv_reconnect_checker(), name="mpv_reconnect_checker"))
    
    # 8. Start Web Server
    try:
        from web.server import create_app, run_server
        
        app = create_app(state, ytdlp, db, controller)
        
        host = WEB_HOST
        port = WEB_PORT
        
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            display_host = s.getsockname()[0]
            s.close()
        except Exception:
            display_host = host if host != "0.0.0.0" else "127.0.0.1"
            
        url_client = f"http://{display_host}:{port}"
        url_admin = f"http://{display_host}:{port}/admin"
        print(f"╔══════════════════════════════════════════════════╗")
        print(f"║   YTGUI Web Server                               ║")
        print(f"║   Client : {url_client:<37} ║")
        print(f"║   Admin  : {url_admin:<37} ║")
        
        from config import ADMIN_USERNAME, ADMIN_PASSWORD, IS_PASSWORD_AUTO_GENERATED
        if IS_PASSWORD_AUTO_GENERATED:
            print(f"║                                                  ║")
            print(f"║   Kredensial Mode Admin:                         ║")
            print(f"║   User: {ADMIN_USERNAME:<40} ║")
            print(f"║   Pass: {ADMIN_PASSWORD:<40} ║")
            print(f"║   (Tersimpan: cache/admin_password.txt)          ║")
        print(f"╚══════════════════════════════════════════════════╝")
        
        await run_server(app, host=host, port=port)

    except asyncio.CancelledError:
        pass
    finally:
        import traceback
        for t in tasks:
            if t.done() and not t.cancelled():
                e = t.exception()
                if e:
                    logging.getLogger(__name__).error(f"Task {t.get_coro().__name__} crashed: {e}")
                    print(f"\n[FATAL ERROR] App crashed due to task failure: {e}")
                    traceback.print_exception(type(e), e, e.__traceback__)

        # Cancel remaining tasks
        for t in tasks:
            t.cancel()
        
        # Cleanup resources
        lyrics_fetcher.cleanup()
        sponsorblock.cleanup()
        await nowplaying.cleanup()
        ytdlp.cancel_download()
        await http_session.close()
        await mpv.close()
        await db.close()
        
        logging.getLogger(__name__).info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
