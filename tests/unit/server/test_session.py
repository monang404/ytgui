"""
PATCH-1-11: Session token persistence di SQLite
Verifikasi bahwa session token disimpan di SQLite (tabel sessions).
"""

import pytest
import pytest_asyncio
import asyncio
import time

from cache.db import Database
from core.state import TrackInfo


@pytest_asyncio.fixture
async def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_library.db"
    db = Database(db_path=db_path)
    await db.init()
    yield db
    await db.close()


@pytest.mark.asyncio
class TestSessionPersistence:
    """Checklist PATCH-1-11:
    - [x] Tabel 'sessions' ada di schema SQLite
    - [x] create_session, verify_session, delete_session ada di Database
    - [x] Session token yang valid bisa diverifikasi
    - [x] Session token yang expired ditolak
    - [x] cleanup_sessions menghapus token expired
    """

    async def test_sessions_table_exists(self, temp_db):
        """Tabel 'sessions' harus ada di database setelah init."""
        async with temp_db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None, "Tabel 'sessions' harus ada di schema"

    async def test_sessions_table_schema(self, temp_db):
        """Tabel sessions harus punya kolom token dan expires_at."""
        async with temp_db._conn.execute("PRAGMA table_info(sessions)") as cursor:
            columns = await cursor.fetchall()
        col_names = [c[1] for c in columns]
        assert "token" in col_names, "Kolom 'token' harus ada di tabel sessions"
        assert "expires_at" in col_names, "Kolom 'expires_at' harus ada di tabel sessions"

    async def test_create_session(self, temp_db):
        """create_session harus bisa menyimpan token."""
        token = "test_token_abc123"
        expires_at = int(time.time()) + 86400
        await temp_db.create_session(token, expires_at)

        async with temp_db._conn.execute(
            "SELECT * FROM sessions WHERE token = ?", (token,)
        ) as cursor:
            row = await cursor.fetchone()
        assert row is not None, "Token harus tersimpan di database"

    async def test_verify_session_valid(self, temp_db):
        """Session token yang valid (belum expired) harus terverifikasi."""
        token = "valid_token_123"
        expires_at = int(time.time()) + 86400
        await temp_db.create_session(token, expires_at)

        result = await temp_db.verify_session(token)
        assert result is True, "Token yang valid harus terverifikasi"

    async def test_verify_session_expired(self, temp_db):
        """Session token yang expired harus ditolak."""
        token = "expired_token_456"
        expires_at = int(time.time()) - 100
        await temp_db.create_session(token, expires_at)

        result = await temp_db.verify_session(token)
        assert result is False, "Token yang expired harus ditolak"

    async def test_verify_session_nonexistent(self, temp_db):
        """Session token yang tidak ada harus ditolak."""
        result = await temp_db.verify_session("nonexistent_token")
        assert result is False, "Token yang tidak ada harus ditolak"

    async def test_delete_session(self, temp_db):
        """delete_session harus bisa menghapus token."""
        token = "delete_me_token"
        expires_at = int(time.time()) + 86400
        await temp_db.create_session(token, expires_at)

        await temp_db.delete_session(token)

        result = await temp_db.verify_session(token)
        assert result is False, "Token yang dihapus tidak boleh terverifikasi"

    async def test_cleanup_sessions(self, temp_db):
        """cleanup_sessions harus menghapus semua token expired."""
        now = int(time.time())
        await temp_db.create_session("valid_1", now + 86400)
        await temp_db.create_session("valid_2", now + 3600)
        await temp_db.create_session("expired_1", now - 100)
        await temp_db.create_session("expired_2", now - 86400)

        await temp_db.cleanup_sessions()

        assert await temp_db.verify_session("valid_1") is True
        assert await temp_db.verify_session("valid_2") is True
        assert await temp_db.verify_session("expired_1") is False
        assert await temp_db.verify_session("expired_2") is False

    async def test_database_has_session_methods(self):
        """Database harus punya method create_session, verify_session, delete_session."""
        assert hasattr(Database, "create_session"), "Database harus punya create_session"
        assert hasattr(Database, "verify_session"), "Database harus punya verify_session"
        assert hasattr(Database, "delete_session"), "Database harus punya delete_session"
        assert hasattr(Database, "cleanup_sessions"), "Database harus punya cleanup_sessions"
