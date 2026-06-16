import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.state import AppState, TrackInfo
from core.event_bus import bus, SEARCH_RESULTS, QUEUE_EMPTY, CMD_NEXT, TRACK_PROGRESS, TRACK_ENDED
from integrations.lyrics import LyricsFetcher
from integrations.sponsorblock import SponsorBlockHandler
from engine.autoplay import AutoplayEngine

# Mock MPV
class MockMpv:
    async def seek(self, pos):
        print(f"MockMpv: Seeked to {pos}")

async def main():
    print("Starting Fase 4 Integrations Test...")
    state = AppState()
    
    # 1. Test Lyrics
    print("\n--- Test 1: Lyrics Fetcher ---")
    lf = LyricsFetcher(state)
    print("Fetching lyrics for 'Never Gonna Give You Up' by Rick Astley...")
    await lf.fetch("Never Gonna Give You Up", "Rick Astley", 212)
    if len(lf.lyrics_data) > 0:
        print(f"[OK] Fetched {len(lf.lyrics_data)} lyric lines.")
        print(f"First line: {lf.lyrics_data[0][0]}s -> {lf.lyrics_data[0][1]}")
    else:
        print("[FAIL] Failed to fetch lyrics.")

    # 2. Test SponsorBlock
    print("\n--- Test 2: SponsorBlock ---")
    sb = SponsorBlockHandler(MockMpv())
    print("Fetching segments for 'dQw4w9WgXcQ' (Rickroll)...")
    await sb.fetch_segments("dQw4w9WgXcQ")
    if len(sb.segments) > 0:
        print(f"[OK] Found {len(sb.segments)} skip segments.")
        print(f"Segment 1: {sb.segments[0][0]}s to {sb.segments[0][1]}s")
        print("Simulating playback at segment start...")
        await bus.publish(TRACK_PROGRESS, sb.segments[0][0] + 0.1) # should trigger seek
    else:
        print("[FAIL] No segments found.")

    print("\n[OK] Fase 4 components executed without crashing.")

if __name__ == "__main__":
    asyncio.run(main())
