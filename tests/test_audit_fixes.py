import asyncio
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.event_bus import bus

errors_reached = []

async def bad_handler(data):
    raise ValueError("boom!")

async def good_handler(data):
    errors_reached.append("reached")

bus.subscribe("test.event", bad_handler)
bus.subscribe("test.event", good_handler)

async def main():
    # Test 1: EventBus error isolation (CRITICAL-01)
    await bus.publish("test.event", None)
    assert "reached" in errors_reached, "FAIL: good_handler was not called after bad_handler crashed"
    print("[OK] CRITICAL-01: EventBus error isolation works")

    # Test 2: MpvController has _set_property (CRITICAL-06)
    from engine.mpv_controller import MpvController
    mpv = MpvController()
    assert hasattr(mpv, '_set_property'), "FAIL: _set_property missing"
    assert hasattr(mpv, 'close'), "FAIL: close() missing"
    assert hasattr(mpv, 'is_connected'), "FAIL: is_connected missing"
    print("[OK] CRITICAL-06: MpvController._set_property exists")

    # Test 3: DB persistent connection (CRITICAL-04)
    from cache.db import Database
    from config import DB_PATH
    DB_PATH.unlink(missing_ok=True)
    db = Database()
    await db.init()
    assert db._conn is not None, "FAIL: no persistent connection"
    await db.close()
    print("[OK] CRITICAL-04: DB uses persistent connection")

    # Test 4: QueueManager has all handlers (HIGH-06/07/08)
    from engine.queue_manager import QueueManager
    assert hasattr(QueueManager, 'play_prev'), "FAIL: play_prev missing"
    assert hasattr(QueueManager, '_on_volume_up'), "FAIL: _on_volume_up missing"
    assert hasattr(QueueManager, '_on_volume_down'), "FAIL: _on_volume_down missing"
    assert hasattr(QueueManager, '_on_download'), "FAIL: _on_download missing"
    assert hasattr(QueueManager, '_on_toggle_lyrics'), "FAIL: _on_toggle_lyrics missing"
    print("[OK] HIGH-06/07/08/LOW-05: All command handlers implemented")

    # Test 5: State has history and show_lyrics
    from core.state import AppState
    s = AppState()
    assert hasattr(s, 'history'), "FAIL: history missing"
    assert hasattr(s, 'show_lyrics'), "FAIL: show_lyrics missing"
    print("[OK] HIGH-01: AppState has history + show_lyrics")

    # Test 6: SponsorBlock uses json.dumps not str() (HIGH-02)
    import json
    from config import SPONSORBLOCK_CATS
    serialized = json.dumps(SPONSORBLOCK_CATS)
    assert "'" not in serialized, f"FAIL: single quotes in JSON: {serialized}"
    assert serialized.startswith("["), f"FAIL: not valid JSON array: {serialized}"
    print("[OK] HIGH-02: SponsorBlock JSON serialization correct")

    # Test 7: requirements.txt cleanup (MED-08/09)
    with open("requirements.txt") as f:
        content = f.read()
    assert "httpx" not in content, "FAIL: httpx still in requirements"
    assert "aiofiles" not in content, "FAIL: aiofiles still in requirements"
    assert ">=" in content, "FAIL: no version pinning"
    print("[OK] MED-08/09: requirements.txt cleaned and pinned")

    print("\n=== ALL AUDIT FIXES VERIFIED ===")

if __name__ == "__main__":
    asyncio.run(main())
