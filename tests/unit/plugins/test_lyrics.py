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

    def test_fetch_method_has_single_session_scope(self):
        """Verifikasi bahwa method fetch() hanya punya satu 'async with get_session()'
        dan semua session.get() ada di dalamnya (source code analysis)."""
        source = inspect.getsource(LyricsFetcher.fetch)
        
        # Hitung jumlah 'async with get_session()' — harus hanya 1
        scope_count = source.count("async with get_session()")
        assert scope_count == 1, (
            f"Harus ada tepat 1 'async with get_session()' scope, ditemukan {scope_count}. "
            "Semua request harus di dalam satu scope."
        )

    def test_no_session_get_outside_context_manager(self):
        """Verifikasi bahwa tidak ada session.get() yang dipanggil
        setelah context manager selesai — analisis indent level."""
        source = inspect.getsource(LyricsFetcher.fetch)
        lines = source.split("\n")
        
        in_context_manager = False
        context_indent = 0
        session_get_outside = False

        for line in lines:
            stripped = line.lstrip()
            current_indent = len(line) - len(stripped)
            
            if "async with get_session()" in line:
                in_context_manager = True
                context_indent = current_indent
                continue
            
            # Jika kita keluar dari indent context manager
            if in_context_manager and stripped and current_indent <= context_indent and "except" not in stripped and "finally" not in stripped:
                in_context_manager = False
            
            # Cek apakah ada session.get di luar context manager
            if not in_context_manager and "session.get" in stripped:
                session_get_outside = True
                break
        
        assert not session_get_outside, (
            "Ditemukan 'session.get()' di luar scope 'async with get_session()'. "
            "Ini akan menyebabkan RuntimeError: Session is closed. "
            "Semua request harus di dalam satu context manager."
        )

    def test_lyrics_fetcher_has_generation_counter(self):
        """Verifikasi bahwa LyricsFetcher._current_generation ada (PATCH-1-05 related)."""
        from core.state import AppState
        state = AppState()
        fetcher = LyricsFetcher(state)
        assert hasattr(fetcher, "_current_generation"), "LyricsFetcher harus punya _current_generation"
        assert fetcher._current_generation == 0
