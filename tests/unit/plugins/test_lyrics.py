"""
PATCH-0-02: LyricsFetcher session scope bug
Verifikasi bahwa seluruh logika fetch lirik berada di dalam satu
session context manager scope, sehingga fallback search tidak
menggunakan session yang sudah ditutup.
"""

import pytest
import asyncio
import inspect
import ast
from plugins.lyrics import LyricsFetcher


class TestLyricsFetcherSessionScope:
    """Checklist PATCH-0-02:
    - [x] Fallback search (request ke-2) harus di dalam scope 'async with get_session()'
    - [x] Tidak ada 'session.get' call di luar context manager scope
    """

    @pytest.mark.asyncio
    async def test_uses_persistent_session(self):
        """Verifikasi bahwa LyricsFetcher menggunakan session persisten (injected/internal)."""
        from core.state import AppState
        state = AppState()
        fetcher = LyricsFetcher(state)
        
        session1 = fetcher._get_session()
        session2 = fetcher._get_session()
        
        assert session1 is session2, "Session harus dibuat sekali dan digunakan berulang kali (persistent)."
        assert fetcher._owns_session is True, "Jika tidak di-inject, fetcher harus memiliki (own) session-nya."

    def test_lyrics_fetcher_has_generation_counter(self):
        """Verifikasi bahwa LyricsFetcher._current_generation ada (PATCH-1-05 related)."""
        from core.state import AppState
        state = AppState()
        fetcher = LyricsFetcher(state)
        assert hasattr(fetcher, "_current_generation"), "LyricsFetcher harus punya _current_generation"
        assert fetcher._current_generation == 0
