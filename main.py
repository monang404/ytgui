import asyncio
import logging
import signal
import aiohttp
import stat
from logging.handlers import RotatingFileHandler
from core.state import AppState, PlayerStatus
from tui.dashboard import Dashboard
from core.event_bus import bus, CMD_SEARCH, SEARCH_RESULTS, LOG_MESSAGE, CMD_QUIT
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.autoplay import AutoplayEngine
from engine.queue_manager import QueueManager
from config import BASE_DIR

log_path = BASE_DIR / "ytplayer.log"
_log_handler = RotatingFileHandler(
    log_path,
    maxBytes=1 * 1024 * 1024,  # 1 MB per file
    backupCount=2,              # simpan maksimal 2 backup
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
    db = Database()
    await db.init()
    
    # 2. Initialize Core Engine
    ytdlp = YtDlpClient()
    mpv = MpvController()
    mpv_connected = False
    try:
        await mpv.connect()
        mpv_connected = True
    except Exception as e:
        logging.getLogger(__name__).error(f"mpv not available: {e}")
        state.error_msg = (
            "MPV tidak ditemukan. Jalankan: pkg install mpv (Termux) "
            "atau install MPV dan tambahkan ke PATH (Windows/Linux)."
        )
        state.status = PlayerStatus.ERROR
    
    # 3. Shared HTTP session (MED-01 fix)
    http_session = aiohttp.ClientSession()
    
    # 4. Initialize Integrations & Resolver
    resolver = CacheResolver(db, ytdlp)
    sponsorblock = SponsorBlockHandler(mpv, session=http_session)
    lyrics_fetcher = LyricsFetcher(state, session=http_session)
    autoplay = AutoplayEngine(ytdlp, state)
    
    # 5. Initialize Queue Manager (now receives ytdlp and db for download)
    qm = QueueManager(state, mpv, ytdlp, db, resolver, sponsorblock, lyrics_fetcher)

    # 6. Wire up user Search command -> YtDlp
    async def handle_search(query: str):
        await bus.publish(LOG_MESSAGE, f"Searching: {query}...")
        try:
            results = await ytdlp.search(query, max_results=10)
            state.is_online = True
            if results:
                await bus.publish(SEARCH_RESULTS, results)
            else:
                await bus.publish(LOG_MESSAGE, "No results found.")
        except Exception as e:
            state.is_online = False
            from engine.queue_manager import QueueManager
            user_msg = QueueManager._user_friendly_error(e)
            state.error_msg = user_msg
            await bus.publish(LOG_MESSAGE, f"Search failed: {user_msg}")

    bus.subscribe(CMD_SEARCH, handle_search)

    # 7. Start TUI
    dashboard = Dashboard(state)

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
    
    # CRITICAL-05 fix: Graceful shutdown with proper cleanup
    try:
        await dashboard.run_async()
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
        pass  # LOW-04: Clean exit on Ctrl+C at top level
