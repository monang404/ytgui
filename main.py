import asyncio
import logging
import structlog
import stat
import sys
import aiohttp
from logging.handlers import RotatingFileHandler
from core.log_config import setup_logging
from core.state import AppState, PlayerStatus, AudioOutput
from core.event_bus import bus
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from engine.download_manager import DownloadManager
from engine.command_router import CommandRouter
from integrations.termux_notification import TermuxNowPlaying
from core.task_utils import safe_create_task
from core.room_manager import RoomManager
from config import BASE_DIR, WEB_HOST, WEB_PORT

setup_logging()

try:
    log_path = BASE_DIR / "ytplayer.log"
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
        structlog.get_logger(__name__).error(f"mpv not available: {e}")
        state.error_msg = (
            "MPV tidak ditemukan. Jalankan: pkg install mpv (Termux) "
            "atau install MPV dan tambahkan ke PATH (Windows/Linux)."
        )
        state.status = PlayerStatus.ERROR
    
    # 3. Shared HTTP session
    http_session = aiohttp.ClientSession()
    
    # 4. Initialize Room Manager
    print("  [4/5] Menyusun Room Manager (Multi-room)...")
    room_manager = RoomManager(db, ytdlp, http_session)
    
    # Pre-create default room
    default_room = await room_manager.get_or_create_room("default")
    
    # 5. Global Services
    download_manager = DownloadManager(bus, default_room.state, ytdlp)
    command_router = CommandRouter(room_manager)
    
    # Termux now-playing notification (no-op outside Termux)
    nowplaying = TermuxNowPlaying(default_room.event_bus, default_room.state)
    await nowplaying.start()

    # Connectivity Check
    async def check_connectivity():
        while True:
            try:
                async with http_session.get(
                    "https://connectivitycheck.gstatic.com/generate_204",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as r:
                    is_online = (r.status == 204)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                is_online = False
            except Exception as e:
                structlog.get_logger(__name__).warning(f"Connectivity check unexpected error: {e}")
                is_online = False
            
            for room in room_manager.rooms.values():
                room.state.is_online = is_online
                
            await asyncio.sleep(30)

    connectivity_task = safe_create_task(check_connectivity(), name="connectivity_checker")
    tasks = [connectivity_task]
    
    # 7.5 MPV auto-reconnect checker (Per room)
    async def mpv_reconnect_checker():
        while True:
            await asyncio.sleep(5)
            for room in list(room_manager.rooms.values()):
                if not getattr(room.mpv, "is_connected", False) and room.state.status != PlayerStatus.ERROR:
                    structlog.get_logger(__name__).warning(f"MPV terputus di room {room.room_id}! Mencoba reconnect...")
                    try:
                        await room.mpv.close()
                    except Exception:
                        pass
                    try:
                        await room.mpv.connect()
                        if room.state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED) and room.state.current_track:
                            uri = await room.resolver.resolve(room.state.current_track)
                            await room.mpv.play(uri)
                            await room.mpv.seek(room.state.position)
                            if getattr(room.state, "audio_output", AudioOutput.DEVICE) == AudioOutput.BROWSER:
                                await room.mpv.set_volume(0)
                            else:
                                await room.mpv.set_volume(room.state.volume)
                            if room.state.status == PlayerStatus.PLAYING:
                                await room.mpv.resume()
                    except Exception as e:
                        structlog.get_logger(__name__).error(f"MPV reconnect failed for room {room.room_id}: {e}")

    tasks.append(safe_create_task(mpv_reconnect_checker(), name="mpv_reconnect_checker"))
    
    # 8. Start Web Server
    try:
        from web.server import create_app, run_server
        
        app = create_app(room_manager, ytdlp, db)
        
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
                    structlog.get_logger(__name__).error(f"Task {t.get_coro().__name__} crashed: {e}")
                    print(f"\n[FATAL ERROR] App crashed due to task failure: {e}")
                    traceback.print_exception(type(e), e, e.__traceback__)

        # Cancel remaining tasks
        for t in tasks:
            t.cancel()
        
        # Cleanup resources
        await nowplaying.cleanup()
        await room_manager.shutdown()
        ytdlp.cancel_download()
        await http_session.close()
        await db.close()
        
        structlog.get_logger(__name__).info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
