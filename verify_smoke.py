import asyncio
import sys
import os
import logging
from unittest.mock import patch

# Mock sys.stdout/stdin to prevent Textual from trying to initialize a real terminal
os.environ["TEXTUAL_DRIVER"] = "textual.drivers.headless_driver:HeadlessDriver"

async def run_smoke_test():
    print("Starting smoke test for 5 seconds...")
    from main import main
    try:
        await asyncio.wait_for(main(), timeout=5.0)
    except asyncio.TimeoutError:
        print("Timeout reached, graceful exit triggered.")
    except Exception as e:
        print(f"Smoke test encountered error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("Smoke test finished.")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
