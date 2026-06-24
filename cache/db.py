import aiosqlite
import time
import structlog
from pathlib import Path
from core.state import TrackInfo
from config import DB_PATH

logger = structlog.get_logger(__name__)

class Database:
    """
    CRITICAL-04 fix: Uses a single persistent connection instead of
    opening a new connection for every operation.
    MED-10 fix: Added separate increment_play_count method.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._schema_path = Path(__file__).parent / "schema.sql"
        self._conn = None

    @property
    def conn(self):
        return self._conn

    async def init(self):
        """Initializes the database using the schema.sql file."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        
        with open(self._schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        await self._conn.executescript(schema_sql)
        
        # Eviction Policy: Hapus lagu yang tidak diputar > 30 hari, bukan favorit, dan belum di-download
        thirty_days_ago = int(time.time()) - (30 * 24 * 3600)
        await self._conn.execute(
            "DELETE FROM tracks WHERE last_played < ? AND play_count = 0 AND local_path IS NULL",
            (thirty_days_ago,)
        )
        await self._conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    async def close(self):
        """Close the persistent connection gracefully."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def get_track(self, video_id: str) -> TrackInfo | None:
        """Retrieves track metadata from the database as a TrackInfo entity."""
        async with self._conn.execute(
            "SELECT * FROM tracks WHERE video_id = ?", (video_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return TrackInfo(
                video_id=row["video_id"],
                title=row["title"],
                artist=row["artist"],
                duration=row["duration"],
                thumbnail=row["thumbnail"],
                local_path=row["local_path"],
                stream_url=row["stream_url"],
                view_count=row["view_count"],
                stream_url_ts=row["stream_url_ts"],
                play_count=row["play_count"],
                last_played=row["last_played"],
            )

    async def upsert_track(self, track: TrackInfo, stream_url: str = None, local_path: str = None):
        """Inserts or updates a track record (metadata + cache URLs only)."""
        ts = int(time.time())
        query = """
            INSERT INTO tracks (
                video_id, title, artist, duration, view_count, thumbnail, 
                stream_url, stream_url_ts, local_path, last_played, play_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(video_id) DO UPDATE SET
                title=excluded.title,
                artist=excluded.artist,
                duration=excluded.duration,
                view_count=excluded.view_count,
                thumbnail=excluded.thumbnail,
                stream_url=COALESCE(excluded.stream_url, tracks.stream_url),
                stream_url_ts=COALESCE(excluded.stream_url_ts, tracks.stream_url_ts),
                local_path=COALESCE(excluded.local_path, tracks.local_path),
                last_played=excluded.last_played
        """
        await self._conn.execute(query, (
            track.video_id, track.title, track.artist, track.duration,
            track.view_count, track.thumbnail, stream_url, ts if stream_url else None,
            local_path, ts
        ))
        await self._conn.commit()

    async def update_stream_url_only(self, video_id: str, stream_url: str):
        """Hanya update stream_url tanpa mengubah metadata (mencegah overwite dengan 'Temp')."""
        ts = int(time.time())
        await self._conn.execute(
            "UPDATE tracks SET stream_url=?, stream_url_ts=? WHERE video_id=?",
            (stream_url, ts, video_id)
        )
        await self._conn.commit()

    async def increment_play_count(self, video_id: str):
        """MED-10 fix: Only called when a track actually starts playing."""
        ts = int(time.time())
        await self._conn.execute(
            "UPDATE tracks SET play_count = play_count + 1, last_played = ? WHERE video_id = ?",
            (ts, video_id)
        )
        await self._conn.commit()

    async def create_session(self, token: str, expires_at: int):
        await self._conn.execute(
            "INSERT INTO sessions (token, expires_at) VALUES (?, ?)",
            (token, expires_at)
        )
        await self._conn.commit()

    async def verify_session(self, token: str) -> bool:
        now = int(time.time())
        async with self._conn.execute(
            "SELECT expires_at FROM sessions WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["expires_at"] > now:
                return True
            if row:
                await self.delete_session(token)
            return False

    async def delete_session(self, token: str):
        await self._conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        await self._conn.commit()
        
    async def cleanup_sessions(self):
        now = int(time.time())
        await self._conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        await self._conn.commit()
