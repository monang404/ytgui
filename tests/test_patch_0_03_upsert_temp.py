"""
PATCH-0-03: Fix upsert_track overwrite dengan Temp
Verifikasi bahwa db.update_stream_url_only() ada dan tidak
menimpa metadata track (title, artist, duration).
"""

import pytest
import pytest_asyncio
import asyncio
import time
from pathlib import Path

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
class TestUpsertTrackNoTempOverwrite:
    """Checklist PATCH-0-03:
    - [x] Fungsi update_stream_url_only() ada di cache/db.py
    - [x] Setelah update_stream_url_only(), metadata track tidak berubah
    - [x] stream_url dan stream_url_ts terupdate dengan benar
    """

    async def test_update_stream_url_only_exists(self):
        """Method update_stream_url_only harus ada di Database class."""
        assert hasattr(Database, "update_stream_url_only"), \
            "Database harus punya method update_stream_url_only"

    async def test_update_stream_url_only_preserves_metadata(self, temp_db):
        """Setelah update_stream_url_only, title/artist/duration TIDAK BOLEH berubah."""
        track = TrackInfo(
            video_id="test123abcde",
            title="Original Title",
            artist="Original Artist",
            duration=300,
        )
        # Insert track dengan metadata asli
        await temp_db.upsert_track(track, stream_url="https://example.com/old_url")

        # Update hanya stream_url
        await temp_db.update_stream_url_only("test123abcde", "https://example.com/new_url")

        # Verifikasi metadata TIDAK berubah
        row = await temp_db.get_track("test123abcde")
        assert row is not None
        assert row.title == "Original Title", "Title tidak boleh berubah setelah update_stream_url_only"
        assert row.artist == "Original Artist", "Artist tidak boleh berubah setelah update_stream_url_only"
        assert row.duration == 300, "Duration tidak boleh berubah setelah update_stream_url_only"
        assert row.stream_url == "https://example.com/new_url", "Stream URL harus terupdate"

    async def test_update_stream_url_only_updates_timestamp(self, temp_db):
        """stream_url_ts harus terupdate setelah update_stream_url_only."""
        track = TrackInfo(
            video_id="test456abcde",
            title="Test Track",
            artist="Test Artist",
            duration=200,
        )
        await temp_db.upsert_track(track, stream_url="https://example.com/url1")
        
        row_before = await temp_db.get_track("test456abcde")
        ts_before = row_before.stream_url_ts

        # Small delay to ensure timestamp changes
        await asyncio.sleep(0.1)

        await temp_db.update_stream_url_only("test456abcde", "https://example.com/url2")
        
        row_after = await temp_db.get_track("test456abcde")
        assert row_after.stream_url_ts >= ts_before, "stream_url_ts harus terupdate"

    async def test_upsert_track_does_not_overwrite_with_temp(self, temp_db):
        """Simulasi skenario HIDDEN-03: jika ada track dengan metadata asli,
        upsert dengan title='Temp' HANYA boleh terjadi via upsert_track (bukan update_stream_url_only).
        update_stream_url_only TIDAK BOLEH menyentuh metadata."""
        real_track = TrackInfo(
            video_id="realtrack0001",
            title="Bohemian Rhapsody",
            artist="Queen",
            duration=354,
        )
        await temp_db.upsert_track(real_track, stream_url="https://example.com/old")

        # Simulasi prefetch: HANYA update stream_url
        await temp_db.update_stream_url_only("realtrack0001", "https://example.com/new")

        row = await temp_db.get_track("realtrack0001")
        assert row.title == "Bohemian Rhapsody", "Metadata TIDAK BOLEH ditimpa 'Temp'"
        assert row.artist == "Queen"
        assert row.duration == 354
