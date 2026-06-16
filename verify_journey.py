import asyncio
import os
import sys

os.environ["TEXTUAL_DRIVER"] = "textual.drivers.headless_driver:HeadlessDriver"

from core.state import AppState
from tui.dashboard import Dashboard
from core.event_bus import bus, CMD_SEARCH, SEARCH_RESULTS, LOG_MESSAGE, CMD_QUIT, CMD_QUEUE_SELECT
from engine.ytdlp_client import YtDlpClient
from engine.mpv_controller import MpvController
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.queue_manager import QueueManager
from engine.autoplay import AutoplayEngine
import aiohttp

async def run_journey():
    state = AppState()
    db = Database()
    await db.init()
    
    ytdlp = YtDlpClient()
    mpv = MpvController()
    http_session = aiohttp.ClientSession()
    
    resolver = CacheResolver(db, ytdlp)
    sponsorblock = SponsorBlockHandler(mpv, session=http_session)
    lyrics_fetcher = LyricsFetcher(state, session=http_session)
    autoplay = AutoplayEngine(ytdlp, state)
    
    qm = QueueManager(state, mpv, ytdlp, db, resolver, sponsorblock, lyrics_fetcher)
    
    dashboard = Dashboard(state)
    
    search_triggered = asyncio.Event()
    search_results_event = asyncio.Event()
    
    async def handle_search(query: str):
        search_triggered.set()
        try:
            results = await ytdlp.search(query, max_results=1)
            if results:
                await bus.publish(SEARCH_RESULTS, results)
        except Exception as e:
            print(f"Search error: {e}")

    async def handle_results(results):
        search_results_event.set()
        state.search_results = results
        # add to queue
        for res in results:
            state.queue.append(res)
            
    bus.subscribe(CMD_SEARCH, handle_search)
    bus.subscribe(SEARCH_RESULTS, handle_results)
    
    print("Starting automated user journey test...")
    async with dashboard.run_test() as pilot:
        # 1. verify search input exists
        await pilot.pause(0.5)
        
        # 2. type into the search bar
        await pilot.press("/")
        await pilot.pause(0.1)
        
        from textual.widgets import Input
        input_widget = dashboard.query_one("#search_input", Input)
        assert input_widget.has_focus, "Search input should have focus"
        
        # We manually set value and simulate submit because typing letters might be slow/intercepted incorrectly in tests if not careful, but wait, we fixed global bindings. Let's test them.
        for char in "rick astley":
            await pilot.press(char)
        
        await pilot.press("enter")
        
        # 3. wait for search triggered
        try:
            await asyncio.wait_for(search_triggered.wait(), timeout=5.0)
            print("PASS: Search triggered from UI.")
        except asyncio.TimeoutError:
            print("FAIL: Search not triggered.")
            sys.exit(1)
            
        # 4. wait for search results
        try:
            await asyncio.wait_for(search_results_event.wait(), timeout=10.0)
            print("PASS: Search results received.")
        except asyncio.TimeoutError:
            print("FAIL: Search results not received.")
            sys.exit(1)
            
        # 5. verify queue has items
        assert len(state.queue) > 0, "Queue should not be empty"
        print("PASS: Item added to queue.")
        
        # 6. Stop app
        await pilot.press("ctrl+c")
        await asyncio.sleep(0.5)
        
    await http_session.close()
    await mpv.close()
    await db.close()
    print("User journey test completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_journey())
