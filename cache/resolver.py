import os
from cache.db import Database
from engine.ytdlp_client import YtDlpClient
from core.state import TrackInfo

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
        """Returns the playback URI (local path atau YouTube URL untuk MPV)."""
        row = await self.db.get_track(track.video_id)
        
        # Rule 1: Local file — ini yang benar-benar berguna
        if row and row.get("local_path"):
            path = row["local_path"]
            if os.path.isfile(path):
                track.local_path = path
                return path

        # Rule 2: Selalu pakai YouTube URL (MPV + yt-dlp hook akan handle)
        url = f"https://www.youtube.com/watch?v={track.video_id}"
        track.stream_url = url
        # Simpan metadata track ke DB (tanpa stream_url)
        await self.db.upsert_track(track)
        return url
