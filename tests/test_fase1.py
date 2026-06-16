import asyncio
import sys
import os

# Add parent directory to path so we can import modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.event_bus import bus, SEARCH_RESULTS
from engine.ytdlp_client import YtDlpClient

async def main():
    print("Starting Fase 1 Test...")
    
    # Test 1: EventBus
    print("\n--- Test 1: EventBus ---")
    event_received = False
    
    async def handle_search_results(data):
        nonlocal event_received
        event_received = True
        print(f"[OK] EventBus received: {len(data)} results")
        
    bus.subscribe(SEARCH_RESULTS, handle_search_results)
    
    # Test 2: YtDlpClient
    print("\n--- Test 2: YtDlpClient ---")
    client = YtDlpClient()
    print("Searching for 'nasi goreng song'...")
    try:
        results = await client.search("nasi goreng song", max_results=3)
        if len(results) > 0:
            print(f"[OK] Search OK. Found: {results[0].title} by {results[0].artist}")
            await bus.publish(SEARCH_RESULTS, results)
        else:
            print("[FAIL] Search returned no results.")
    except Exception as e:
        print(f"[FAIL] Search failed: {e}")

    if event_received:
        print("\n[OK] All Fase 1 core components are working correctly.")
    else:
        print("\n[FAIL] EventBus did not trigger handler.")

if __name__ == "__main__":
    asyncio.run(main())
