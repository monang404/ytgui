import asyncio
import logging
import stat
import sys
import aiohttp
from logging.handlers import RotatingFileHandler
from core.state import AppState, PlayerStatus
from core.event_bus import bus, CMD_SEARCH, LOG_MESSAGE, CMD_QUIT
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
from config import BASE_DIR

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
    no_tui = "--no-tui" in sys.argv
    
    # 1. Initialize DB
    db = Database()
    await db.init()
    
    # 2. Initialize Core Engine
    ytdlp = YtDlpClient()
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
    resolver = CacheResolver(db, ytdlp)
    sponsorblock = SponsorBlockHandler(mpv, session=http_session)
    lyrics_fetcher = LyricsFetcher(state, session=http_session)
    
    # 5. Engine Modes & Services
    queue_mode = QueueMode()
    radio_mode = RadioMode(ytdlp, state)
    volume_service = VolumeService(bus, mpv)
    download_manager = DownloadManager(bus, state, ytdlp)
    
    # 6. Initialize Playback Controller
    controller = PlaybackController(
        bus, state, mpv, resolver, sponsorblock, lyrics_fetcher, queue_mode, radio_mode
    )

    # 7. Wire up Search Handler
    async def handle_search(query: str):
        await bus.publish(LOG_MESSAGE, f"Searching: {query}...")
        try:
            results = await ytdlp.search(query, max_results=10)
            state.is_online = True
            if results:
                # Set queue from results[1:] and play the first result
                state.queue = results[1:]
                await controller.play_track(results[0])
            else:
                await bus.publish(LOG_MESSAGE, "No results found.")
        except Exception as e:
            state.is_online = False
            state.error_msg = f"Search failed: {e}"
            await bus.publish(LOG_MESSAGE, f"Search failed: {e}")

    bus.subscribe(CMD_SEARCH, handle_search)

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

    connectivity_task = asyncio.create_task(check_connectivity())
    tasks = [connectivity_task]
    
    # 8. Start App
    try:
        if no_tui:
            print(f"Running in --no-tui mode. Logs available at {log_path}")
            print("To quit, press Ctrl+C")
            
            # Send a test search to verify it works
            asyncio.create_task(bus.publish(CMD_SEARCH, "top hits music"))
            
            # Run loop for 10 seconds then exit for testing purposes
            for _ in range(15):
                await asyncio.sleep(1)
            print("Test timeout reached, exiting.")
            return
        else:
            from tui.app import YTGuiApp
            app = YTGuiApp(state, ytdlp, db)
            await app.run_async()
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
