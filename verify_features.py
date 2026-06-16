import asyncio
import os
import sys

os.environ["TEXTUAL_DRIVER"] = "textual.drivers.headless_driver:HeadlessDriver"

from core.state import AppState
from tui.dashboard import Dashboard
from core.event_bus import bus, CMD_SEARCH, SEARCH_RESULTS, LOG_MESSAGE, CMD_QUIT, CMD_QUEUE_SELECT, CMD_TOGGLE_PAUSE
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.autoplay import AutoplayEngine
from engine.queue_manager import QueueManager

async def run_feature_tests():
    print("Starting feature tests...")
    state = AppState()
    db = Database()
    await db.init()
    ytdlp = YtDlpClient()
    mpv = MpvController()
    try:
        await mpv.connect()
    except Exception as e:
        print(f"Mpv connect failed (expected in test env): {e}")
    
    import aiohttp
    http_session = aiohttp.ClientSession()
    resolver = CacheResolver(db, ytdlp)
    sponsorblock = SponsorBlockHandler(mpv, session=http_session)
    lyrics_fetcher = LyricsFetcher(state, session=http_session)
    autoplay = AutoplayEngine(ytdlp, state)
    qm = QueueManager(state, mpv, ytdlp, db, resolver, sponsorblock, lyrics_fetcher)
    
    async def handle_search(query: str):
        print(f"Executing search for: {query}")
        try:
            results = await ytdlp.search(query, max_results=2)
            if results:
                await bus.publish(SEARCH_RESULTS, results)
                # Fallback to populating queue since Search UI is missing
                for r in results:
                    state.queue.append(r)
                print("Search results populated.")
        except Exception as e:
            print("Search error:", e)

    bus.subscribe(CMD_SEARCH, handle_search)
    dashboard = Dashboard(state)
    
    async with dashboard.run_test() as pilot:
        print("Triggering search command...")
        await bus.publish(CMD_SEARCH, "test audio")
        await asyncio.sleep(5)
        
        print(f"Queue length after search: {len(state.queue)}")
        if len(state.queue) > 0:
            print("Selecting item from queue (index 0)...")
            await bus.publish(CMD_QUEUE_SELECT, 0)
            await asyncio.sleep(2)
        
        print("Testing basic controls (toggle pause)...")
        await bus.publish(CMD_TOGGLE_PAUSE)
        await asyncio.sleep(1)
        
        print("Sending quit signal...")
        await pilot.press("ctrl+c")
        await asyncio.sleep(1)
        
    await http_session.close()
    await mpv.close()
    await db.close()
    print("Feature tests completed.")

if __name__ == "__main__":
    asyncio.run(run_feature_tests())
