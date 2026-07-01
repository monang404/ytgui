import asyncio
from pathlib import Path
from cache.db import Database
from core.state import TrackInfo
import sqlite3

async def main():
    db = Database(Path("data/ytgui.db"))
    await db.init()
    
    # Check current tracks with local_path
    conn = sqlite3.connect("data/ytgui.db")
    rows = conn.execute("SELECT video_id, title, local_path FROM tracks WHERE local_path IS NOT NULL").fetchall()
    print("Currently in DB:", rows)
    
    # Try inserting a test track
    t = TrackInfo(video_id='test1', title='t1', artist='a1', duration=10)
    await db.upsert_track(t, local_path='test_local_path.mp3')
    
    # Verify insertion
    row = conn.execute("SELECT local_path FROM tracks WHERE video_id='test1'").fetchone()
    print("Test insert result:", row)
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
