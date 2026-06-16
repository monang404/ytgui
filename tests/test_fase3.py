import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.state import TrackInfo
from cache.db import Database
from cache.resolver import CacheResolver
from config import DB_PATH

# Mock YtDlpClient to avoid hitting network during cache test
class MockYtDlpClient:
    async def get_stream_url(self, video_id: str) -> str:
        # Simulate network delay
        await asyncio.sleep(0.5)
        return f"https://mocked.youtube.com/stream/{video_id}"

async def main():
    print("Starting Fase 3 Test: Caching & DB...")

    # Cleanup previous test DB if it exists
    if DB_PATH.exists():
        DB_PATH.unlink()

    # 1. Init DB
    db = Database()
    await db.init()
    print("[OK] Database initialized successfully.")

    ytdlp = MockYtDlpClient()
    resolver = CacheResolver(db, ytdlp)

    # 2. Test Track Resolving (Cache Miss)
    track = TrackInfo(
        video_id="dummy123",
        title="Test Song",
        artist="Tester",
        duration=180
    )

    print("\nResolving track for the first time (should take ~0.5s)...")
    start_time = asyncio.get_event_loop().time()
    url1 = await resolver.resolve(track)
    elapsed1 = asyncio.get_event_loop().time() - start_time
    print(f"Result: {url1} (took {elapsed1:.2f}s)")
    
    if elapsed1 >= 0.5:
        print("[OK] Cache MISS behaved correctly.")
    else:
        print("[FAIL] Resolved too quickly, mock not hit.")

    # 3. Test Track Resolving (Cache Hit)
    print("\nResolving track for the second time (should be instant)...")
    start_time = asyncio.get_event_loop().time()
    url2 = await resolver.resolve(track)
    elapsed2 = asyncio.get_event_loop().time() - start_time
    print(f"Result: {url2} (took {elapsed2:.2f}s)")

    if url1 == url2 and elapsed2 < 0.1:
        print("[OK] Cache HIT behaved correctly. Network bypassed.")
    else:
        print("[FAIL] Cache HIT failed.")

    # 4. Verify DB Entry
    row = await db.get_track("dummy123")
    if row and row["play_count"] == 1 and row["stream_url"] == url1:
        print("\n[OK] Database entry verified successfully.")
    else:
        print(f"\n[FAIL] Database entry incorrect: {row}")

if __name__ == "__main__":
    asyncio.run(main())
