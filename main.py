import asyncio
import logging
import signal
import aiohttp
from core.state import AppState
from tui.dashboard import Dashboard
from tui.input_handler import InputHandler
from core.event_bus import bus, CMD_SEARCH, SEARCH_RESULTS, LOG_MESSAGE
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.autoplay import AutoplayEngine
from engine.queue_manager import QueueManager
from config import BASE_DIR

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    filename=BASE_DIR / "ytplayer.log",
    filemode="a"
)

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
        logging.getLogger(__name__).warning(f"mpv not available: {e}")
    
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
            state.error_msg = str(e)
            await bus.publish(LOG_MESSAGE, f"Search failed: {e}")

    bus.subscribe(CMD_SEARCH, handle_search)

    # 7. Start TUI
    input_handler = InputHandler(state)
    dashboard = Dashboard(state, input_handler)

    async def check_connectivity():
        while True:
            try:
                async with http_session.get(
                    "https://connectivitycheck.gstatic.com/generate_204",
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as r:
                    state.is_online = (r.status == 204)
            except Exception:
                state.is_online = False
            await asyncio.sleep(30)

    tasks = [
        asyncio.create_task(dashboard.run()),
        asyncio.create_task(input_handler.run()),
        asyncio.create_task(check_connectivity())
    ]
    
    # CRITICAL-05 fix: Graceful shutdown with proper cleanup
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        # Cancel remaining tasks
        for t in tasks:
            t.cancel()
        
        # Cleanup resources
        await http_session.close()
        await mpv.close()
        await db.close()
        
        logging.getLogger(__name__).info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # LOW-04: Clean exit on Ctrl+C at top level
