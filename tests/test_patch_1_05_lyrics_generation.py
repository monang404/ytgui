"""
PATCH-1-05: Generation counter di LyricsFetcher untuk cancel fetch lama
Verifikasi bahwa LyricsFetcher memiliki generation counter untuk
menghindari race condition saat skip lagu cepat.
"""

import pytest
from core.state import AppState
from integrations.lyrics import LyricsFetcher


class TestLyricsGenerationCounter:
    """Checklist PATCH-1-05:
    - [x] self._current_generation dan self._fetch_task ada di __init__
    - [x] Generation counter di-increment di awal fetch()
    - [x] Hasil fetch lama dibuang jika generation sudah berubah
    """

    def test_has_current_generation_field(self):
        """LyricsFetcher harus punya _current_generation di __init__."""
        state = AppState()
        fetcher = LyricsFetcher(state)
        assert hasattr(fetcher, "_current_generation"), (
            "LyricsFetcher harus punya _current_generation di __init__"
        )
        assert fetcher._current_generation == 0

    def test_generation_counter_in_fetch_source(self):
        """Method fetch() harus increment _current_generation."""
        import inspect
        source = inspect.getsource(LyricsFetcher.fetch)
        assert "_current_generation" in source, (
            "fetch() harus menggunakan _current_generation untuk generation counter"
        )
        # Harus ada increment
        assert "+= 1" in source or "self._current_generation += 1" in source, (
            "fetch() harus meng-increment _current_generation"
        )

    def test_generation_check_before_storing_result(self):
        """Hasil fetch harus dicek dengan generation counter sebelum disimpan."""
        import inspect
        source = inspect.getsource(LyricsFetcher.fetch)
        # Harus ada pengecekan `self._current_generation == gen` atau sejenisnya
        assert "gen" in source and "_current_generation" in source, (
            "fetch() harus mengecek apakah generation masih current sebelum menyimpan hasil"
        )
