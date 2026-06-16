import os
import time
from cache.db import Database
from engine.ytdlp_client import YtDlpClient
from core.state import TrackInfo

# URL expires after 6 hours, we cache for 4 hours
STREAM_URL_TTL = 4 * 3600

class CacheResolver:
    """
    Priority Rules:
    1. Local file exists -> return local_path
    2. Stream URL is fresh -> return stream_url
    3. Stale -> fetch new stream URL from yt-dlp, save to DB, return it
    """

    def __init__(self, db: Database, ytdlp: YtDlpClient):
        self.db = db
        self.ytdlp = ytdlp

    async def resolve(self, track: TrackInfo) -> str:
        """Returns the playback URI (either local path or streaming URL)."""
        row = await self.db.get_track(track.video_id)
        
        # Rule 1: Local file
        if row and row.get("local_path"):
            path = row["local_path"]
            if os.path.isfile(path):
                track.local_path = path
                return path

        # Rule 2: Cached Stream URL
        if row and row.get("stream_url") and row.get("stream_url_ts"):
            age = time.time() - row["stream_url_ts"]
            if age < STREAM_URL_TTL:
                track.stream_url = row["stream_url"]
                return row["stream_url"]

        # Rule 3: Fetch fresh URL
        url = await self.ytdlp.get_stream_url(track.video_id)
        track.stream_url = url
        await self.db.upsert_track(track, stream_url=url)
        return url
