import asyncio
from tui.dashboard import Dashboard
from core.state import AppState
from textual.events import Resize

async def test_interactions():
    app = Dashboard(AppState())
    
    async with app.run_test(size=(40, 30)) as pilot:
        print("1. App started.")
        await pilot.pause()
        
        print("2. Testing tab clicks...")
        await pilot.click("#tab_btn_lyrics")
        await pilot.pause()
        assert app._active_tab == "lyrics", "Tab did not switch to lyrics"
        
        await pilot.click("#tab_btn_queue")
        await pilot.pause()
        assert app._active_tab == "queue", "Tab did not switch to queue"
        
        print("3. Testing control buttons...")
        await pilot.click("#btn_pause")
        await pilot.click("#btn_next")
        await pilot.click("#btn_prev")
        await pilot.click("#btn_stop")
        await pilot.click("#btn_quit")
        await pilot.pause()
        
        print("4. Testing compact mode resize...")
        # Simulate resize to compact mode
        app.post_message(Resize(size=app.size.with_height(20), virtual_size=app.size.with_height(20)))
        await pilot.pause()
        assert app.screen.has_class("-compact"), "Screen should have -compact class"
        
        print("SUCCESS: All interactions tested without crashing.")

if __name__ == "__main__":
    asyncio.run(test_interactions())
