import asyncio
import os
import sys
import time

os.environ["TEXTUAL_DRIVER"] = "textual.drivers.headless_driver:HeadlessDriver"

from core.state import AppState
from tui.dashboard import Dashboard
from core.event_bus import bus, CMD_NEXT, CMD_PREV, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_QUEUE_SELECT
from engine.mpv_controller import MpvController
from cache.db import Database

async def run_stress_test():
    print("Starting stress test (1000 rapid events)...")
    state = AppState()
    db = Database()
    await db.init()
    
    mpv = MpvController()
    dashboard = Dashboard(state)
    
    # Mock queue
    for i in range(100):
        # We just need dummy objects with a title and duration
        class DummyTrack:
            title = f"Track {i}"
            duration = 180
            local_path = None
            view_count = None
            artist = "Unknown"
        state.queue.append(DummyTrack())
    
    async with dashboard.run_test() as pilot:
        start_time = time.time()
        
        # Rapidly spam events
        for i in range(1000):
            await bus.publish(CMD_NEXT)
            await bus.publish(CMD_PREV)
            await bus.publish(CMD_VOLUME_UP)
            await bus.publish(CMD_VOLUME_DOWN)
            if i % 10 == 0:
                await bus.publish(CMD_QUEUE_SELECT, i % 100)
                
        # Wait a bit for event loop to clear
        await asyncio.sleep(2)
        end_time = time.time()
        
        print(f"Stress test completed in {end_time - start_time:.2f} seconds.")
        print("No crashes detected during rapid event firing.")
        
        await pilot.press("ctrl+c")
        await asyncio.sleep(1)
        
    await db.close()

if __name__ == "__main__":
    asyncio.run(run_stress_test())
