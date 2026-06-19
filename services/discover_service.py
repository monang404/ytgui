"""
Purpose: Menyediakan data discover (recent dan favorites).
Subscribes to: (tidak ada)
Publishes: (tidak ada)
"""

import aiosqlite
from core.state import TrackInfo
from cache.db import Database

class DiscoverService:
    def __init__(self, db: Database):
        self.db = db

    async def get_recent(self, n: int) -> list[TrackInfo]:
        """Mengambil n lagu yang terakhir diputar dari DB."""
        if not getattr(self.db, '_conn', None):
            return []
            
        tracks = []
        try:
            async with self.db._conn.execute(
                "SELECT * FROM tracks ORDER BY last_played DESC LIMIT ?", (n,)
            ) as cursor:
                async for row in cursor:
                    d = dict(row)
                    tracks.append(TrackInfo(
                        video_id=d["video_id"],
                        title=d["title"],
                        artist=d["artist"],
                        duration=d["duration"],
                        thumbnail=d["thumbnail"],
                        local_path=d["local_path"],
                        stream_url=d["stream_url"],
                        view_count=d["view_count"]
                    ))
        except Exception:
            pass
        return tracks

    async def get_favorites(self, n: int) -> list[TrackInfo]:
        """Mengambil n lagu dengan play_count tertinggi dari DB."""
        if not getattr(self.db, '_conn', None):
            return []
            
        tracks = []
        try:
            async with self.db._conn.execute(
                "SELECT * FROM tracks WHERE play_count > 0 ORDER BY play_count DESC LIMIT ?", (n,)
            ) as cursor:
                async for row in cursor:
                    d = dict(row)
                    tracks.append(TrackInfo(
                        video_id=d["video_id"],
                        title=d["title"],
                        artist=d["artist"],
                        duration=d["duration"],
                        thumbnail=d["thumbnail"],
                        local_path=d["local_path"],
                        stream_url=d["stream_url"],
                        view_count=d["view_count"]
                    ))
        except Exception:
            pass
        return tracks
