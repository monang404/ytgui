import asyncio
import os
import sys

# Ensure ytcli is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.event_bus import bus, SEARCH_RESULTS, CMD_NEXT, CMD_PREV, CMD_TOGGLE_RADIO, CMD_DOWNLOAD, TRACK_PROGRESS, QUEUE_EMPTY, CMD_VOLUME_UP, SKIP_SEGMENT
from core.state import AppState, TrackInfo, PlayerStatus
from cache.db import Database
from config import DB_PATH

class MockMpv:
    def __init__(self):
        self.is_connected = True
        self.played = []
        self.volume = 80
        self.seeked = []
        
    async def play(self, uri):
        self.played.append(uri)
    async def set_volume(self, vol):
        self.volume = vol
    async def seek(self, pos):
        self.seeked.append(pos)
    async def pause(self): pass

class MockYtDlp:
    def __init__(self):
        self.downloaded = []
    
    async def search(self, query, max_results=10):
        # Return fake results based on query
        return [
            TrackInfo(video_id=f"vid_{i}", title=f"Result {i} for {query}", artist="Test Artist", duration=200)
            for i in range(3)
        ]
        
    async def get_stream_url(self, video_id):
        return f"https://mockstream/{video_id}"
        
    async def download_mp3(self, video_id, on_progress=None):
        self.downloaded.append(video_id)
        return f"/mock/path/{video_id}.mp3"

class MockResolver:
    def __init__(self, db):
        self.db = db
        
    async def resolve(self, track):
        if track.local_path: return track.local_path
        # Simulate real resolver by upserting track to DB
        await self.db.upsert_track(track, stream_url=f"mock_stream_{track.video_id}")
        return f"mock_resolved_url_{track.video_id}"

class MockSponsorBlock:
    def __init__(self):
        self.called = []
        self.segments = [(30.0, 45.0)] # Mock a sponsored segment
        bus.subscribe(TRACK_PROGRESS, self._on_progress)

    async def fetch_segments(self, video_id):
        self.called.append(video_id)

    async def _on_progress(self, pos):
        for start, end in self.segments:
            if start <= pos <= start + 0.6:
                await bus.publish(SKIP_SEGMENT, (start, end))

class MockLyrics:
    def __init__(self, state):
        self.state = state
        self.called = []
        bus.subscribe(TRACK_PROGRESS, self._on_progress)
        
    async def fetch(self, title, artist, duration):
        self.called.append(title)
        self.state.lyrics_lines = ["Line 1", "Line 2", "Line 3"]
        self.lyrics_data = [(10.0, "Line 1"), (20.0, "Line 2"), (30.0, "Line 3")]
        
    async def _on_progress(self, pos):
        if not hasattr(self, 'lyrics_data'): return
        active = 0
        for i, (t, _) in enumerate(self.lyrics_data):
            if t <= pos: active = i
            else: break
        self.state.lyrics_index = active


async def run_scenarios():
    print("--- MULAI DEBUG SKENARIO ---")
    
    # Setup fresh state & test DB
    from pathlib import Path
    import cache.db
    import time
    cache.db.DB_PATH = Path(f"cache/test_integration_{int(time.time())}.db")

    state = AppState()
    db = Database(db_path=cache.db.DB_PATH)
    await db.init()
    
    mpv = MockMpv()
    ytdlp = MockYtDlp()
    resolver = MockResolver(db)
    
    sponsor = MockSponsorBlock()
    lyrics = MockLyrics(state)
    
    from engine.queue_manager import QueueManager
    from engine.autoplay import AutoplayEngine
    
    qm = QueueManager(state, mpv, ytdlp, db, resolver, sponsor, lyrics)
    auto = AutoplayEngine(ytdlp, state)
    
    # Subscribe to test specific events
    skips = []
    bus.subscribe(SKIP_SEGMENT, lambda d: skips.append(d))

    # --- Skenario 1: Search & Populate Queue ---
    print("\n[Skenario 1] Search Results -> Queue Manager")
    fake_results = await ytdlp.search("Coldplay")
    await bus.publish(SEARCH_RESULTS, fake_results)
    
    # Wait for event loop to process
    await asyncio.sleep(0.1)
    
    assert state.current_track.video_id == "vid_0", "First result should play immediately"
    assert len(state.queue) == 2, "Remaining results should go to queue"
    print("[OK] Berhasil: Lagu pertama masuk player, sisanya ke antrean.")

    # --- Skenario 2: Playback & Integrations (DB, Lyrics, SponsorBlock) ---
    print("\n[Skenario 2] Integrations Fired on Playback")
    await asyncio.sleep(0.1) # Let background tasks run
    
    # DB Play count
    db_track = await db.get_track("vid_0")
    assert db_track['play_count'] == 1, f"Play count should increment, but got {db_track['play_count']}"
    
    # Integrations called
    assert "vid_0" in sponsor.called, "SponsorBlock should be fetched"
    assert "Result 0 for Coldplay" in lyrics.called, "Lyrics should be fetched"
    print("[OK] Berhasil: Metadata lirik & sponsor diambil, PlayCount tersimpan di DB.")

    # --- Skenario 3: Progress, Lyrics Sync & Sponsor Skip ---
    print("\n[Skenario 3] Simulasi Waktu Berjalan")
    # Send mock time pos = 25 seconds
    await bus.publish(TRACK_PROGRESS, 25.0)
    await asyncio.sleep(0.05)
    assert state.lyrics_index == 1, "Lirik harus sinkron ke Line 2 di detik 25"
    
    # Send mock time pos = 30.1 seconds (Inside sponsor segment 30.0 - 45.0)
    await bus.publish(TRACK_PROGRESS, 30.1)
    await asyncio.sleep(0.05)
    assert len(skips) > 0, "Harusnya trigger skip segmen"
    print("[OK] Berhasil: Sinkronisasi lirik jalan, segmen iklan/sponsor otomatis diskip.")

    # --- Skenario 4: Navigation (Next & Prev) ---
    print("\n[Skenario 4] Navigasi Antrean")
    await bus.publish(CMD_NEXT, None)
    await asyncio.sleep(0.05)
    assert state.current_track.video_id == "vid_1", "Should play next track"
    assert len(state.history) == 1, "Previous track should go to history"
    
    await bus.publish(CMD_PREV, None)
    await asyncio.sleep(0.05)
    assert state.current_track.video_id == "vid_0", "Should return to previous track"
    print("[OK] Berhasil: Tombol Next & Prev berfungsi sempurna.")

    # --- Skenario 5: Radio Mode / Autoplay ---
    print("\n[Skenario 5] Radio Mode")
    state.queue.clear()
    await bus.publish(CMD_TOGGLE_RADIO, None)
    await asyncio.sleep(0.05)
    # the toggle should trigger queue_low logic
    assert len(state.queue) > 0, "Radio mode should fetch new tracks when queue is empty"
    print(f"[OK] Berhasil: Radio mencari otomatis. {len(state.queue)} lagu ditambahkan.")

    # --- Skenario 6: Volume & Download ---
    print("\n[Skenario 6] Action Buttons")
    await bus.publish(CMD_VOLUME_UP, None)
    await asyncio.sleep(0.05)
    assert state.volume == 85, "Volume naik"
    
    await bus.publish(CMD_DOWNLOAD, None)
    await asyncio.sleep(0.1)
    assert "vid_0" in ytdlp.downloaded, "Harus panggil yt-dlp download"
    assert state.current_track.local_path is not None, "Local path terupdate di state"
    
    db_track = await db.get_track("vid_0")
    assert db_track['local_path'] is not None, "Local path tersimpan di DB cache"
    print("[OK] Berhasil: Volume up fungsi, Download menyimpannya di DB Cache.")

    await db.close()
    print("\n--- SEMUA SKENARIO BERJALAN MULUS TANPA ERROR ---")

if __name__ == "__main__":
    asyncio.run(run_scenarios())
