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
        
        # Migrasi: Tambahkan kolom is_favorite jika belum ada
        try:
            await self._conn.execute("ALTER TABLE tracks ADD COLUMN is_favorite INTEGER DEFAULT 0")
            await self._conn.commit()
        except Exception:
            pass
            
        # Migrasi: Tambahkan kolom click_count untuk artists
        try:
            await self._conn.execute("ALTER TABLE artists ADD COLUMN click_count INTEGER DEFAULT 0")
            await self._conn.commit()
        except Exception:
            pass
        
        logger.info(f"Database initialized at {self.db_path}")

    async def evict_stale_tracks(self) -> int:
        """Hapus track yang benar-benar tidak aktif:
        - Tidak pernah diputar (play_count = 0)
        - Tidak pernah di-cache stream dalam 30 hari terakhir
        - Bukan favorit dan bukan file lokal
        Mengembalikan jumlah baris yang dihapus.
        """
        thirty_days_ago = int(time.time()) - (30 * 24 * 3600)
        cursor = await self._conn.execute(
            """DELETE FROM tracks
               WHERE play_count = 0
                 AND local_path IS NULL
                 AND (is_favorite = 0 OR is_favorite IS NULL)
                 AND (
                     -- stream_url stale atau tidak pernah ada
                     stream_url_ts IS NULL
                     OR stream_url_ts < ?
                 )""",
            (thirty_days_ago,)
        )
        await self._conn.commit()
        deleted = cursor.rowcount
        if deleted:
            logger.info(f"Eviction: {deleted} track stale dihapus dari cache DB")
        return deleted

    async def close(self):
        """Close the persistent connection gracefully."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def increment_artist_click(self, artist_name: str):
        """Increment the click count for a given artist."""
        if not self._conn: return
        try:
            await self._conn.execute(
                "UPDATE artists SET click_count = COALESCE(click_count, 0) + 1 WHERE nama = ?", (artist_name,)
            )
            await self._conn.commit()
        except Exception as e:
            logger.error(f"Error incrementing artist click: {e}")

    async def get_track(self, video_id: str) -> TrackInfo | None:
        """Retrieves track metadata from the database as a TrackInfo entity."""
        async with self._conn.execute(
            "SELECT * FROM tracks WHERE video_id = ?", (video_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            is_fav = 0
            if "is_favorite" in row.keys():
                is_fav = row["is_favorite"] or 0
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
                is_favorite=is_fav,
            )

    async def upsert_track(self, track: TrackInfo, stream_url: str = None, local_path: str = None):
        """Inserts or updates a track record (metadata + cache URLs only)."""
        ts = int(time.time())
        query = """
            INSERT INTO tracks (
                video_id, title, artist, duration, view_count, thumbnail,
                stream_url, stream_url_ts, local_path, last_played
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    async def get_all_artists(self, kategori: str | None = None) -> list[str]:
        """Ambil semua nama artis dari DB untuk seed radio mode.

        Args:
            kategori: filter 'individu' atau 'band'. None = semua.

        Returns:
            List nama artis (string), siap dipakai random.choice/shuffle.
        """
        if kategori:
            query = "SELECT nama FROM artists WHERE kategori = ? ORDER BY id"
            params = (kategori,)
        else:
            query = "SELECT nama FROM artists ORDER BY id"
            params = ()

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        return [row["nama"] for row in rows]

    async def get_random_songs(
        self, limit: int = 12, exclude_ids: set[str] = None, artist: str = None, max_per_artist: int = 3
    ) -> list[TrackInfo]:
        """Ambil lagu acak langsung dari database untuk Radio Mode, dengan limit per artis."""
        if exclude_ids is None:
            exclude_ids = set()
            
        placeholders = ','.join('?' for _ in exclude_ids)
        query = f"""
            WITH RankedSongs AS (
                SELECT s.youtube_id, s.judul, s.duration, a.nama,
                       ROW_NUMBER() OVER (PARTITION BY s.artist_id ORDER BY RANDOM()) as rn
                FROM songs s
                JOIN artists a ON s.artist_id = a.id
                WHERE 1=1
        """
        params = []
        if exclude_ids:
            query += f" AND s.youtube_id NOT IN ({placeholders})"
            params.extend(exclude_ids)
            
        query += """
            )
            SELECT youtube_id, judul, duration, nama
            FROM RankedSongs
            WHERE rn <= ?
        """
        params.append(max_per_artist)
        
        if artist:
            query += " ORDER BY CASE WHEN nama = ? THEN 0 ELSE 1 END, RANDOM() LIMIT ?"
            params.extend([artist, limit])
        else:
            query += " ORDER BY RANDOM() LIMIT ?"
            params.append(limit)

        async with self._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        tracks = []
        for row in rows:
            tracks.append(TrackInfo(
                video_id=row["youtube_id"],
                title=row["judul"],
                artist=row["nama"],
                duration=row["duration"],
                thumbnail=f"https://i.ytimg.com/vi/{row['youtube_id']}/mqdefault.jpg"
            ))
        return tracks

    async def get_artist_songs_strict(self, artist: str, limit: int = 10) -> list[TrackInfo]:
        """Ambil lagu khusus dari artis tertentu saja (bukan campuran)."""
        query = """
            SELECT s.youtube_id, s.judul, s.duration, a.nama
            FROM songs s
            JOIN artists a ON s.artist_id = a.id
            WHERE a.nama = ?
            ORDER BY RANDOM() LIMIT ?
        """
        async with self._conn.execute(query, (artist, limit)) as cursor:
            rows = await cursor.fetchall()

        tracks = []
        for row in rows:
            tracks.append(TrackInfo(
                video_id=row["youtube_id"],
                title=row["judul"],
                artist=row["nama"],
                duration=row["duration"],
                thumbnail=f"https://i.ytimg.com/vi/{row['youtube_id']}/mqdefault.jpg"
            ))
        return tracks




    async def toggle_favorite(self, video_id: str) -> int:
        """Toggles the favorite status of a track dan kembalikan state baru (0 atau 1).
        Atomic: satu UPDATE statement — tidak ada SELECT+UPDATE race condition.
        """
        # Cek dulu apakah track ada
        async with self._conn.execute(
            "SELECT 1 FROM tracks WHERE video_id = ?", (video_id,)
        ) as cursor:
            if not await cursor.fetchone():
                return 0

        # Atomic toggle dalam satu statement: 1-0=1, 1-1=0
        await self._conn.execute(
            "UPDATE tracks SET is_favorite = 1 - COALESCE(is_favorite, 0) WHERE video_id = ?",
            (video_id,)
        )
        await self._conn.commit()

        # Baca nilai baru setelah update
        async with self._conn.execute(
            "SELECT is_favorite FROM tracks WHERE video_id = ?", (video_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return int(row["is_favorite"] or 0) if row else 0
