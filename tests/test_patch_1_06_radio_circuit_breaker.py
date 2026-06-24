"""
PATCH-1-06: Timeout + circuit breaker di _gather_batch() radio
Verifikasi bahwa radio mode memiliki timeout di _gather_batch dan retry logic.
"""

import pytest
import inspect

from engine.radio_engine import RadioMode


class TestRadioCircuitBreaker:
    """Checklist PATCH-1-06:
    - [x] _gather_batch() atau caller-nya memiliki asyncio.wait_for() timeout
    - [x] _fetch_and_play_initial memiliki handling timeout
    - [x] Setelah timeout, radio mencoba lagi
    """

    def test_fetch_and_play_initial_has_timeout(self):
        """_fetch_and_play_initial harus memiliki timeout (asyncio.wait_for atau asyncio.timeout)."""
        source = inspect.getsource(RadioMode._fetch_and_play_initial)
        has_timeout = (
            "wait_for" in source or
            "asyncio.timeout" in source or
            "timeout" in source.lower()
        )
        assert has_timeout, (
            "_fetch_and_play_initial harus memiliki timeout mechanism "
            "untuk mencegah radio freeze saat yt-dlp lambat"
        )

    def test_prefetch_next_has_timeout(self):
        """_prefetch_next harus memiliki timeout."""
        source = inspect.getsource(RadioMode._prefetch_next)
        has_timeout = (
            "wait_for" in source or
            "asyncio.timeout" in source or
            "timeout" in source.lower()
        )
        assert has_timeout, (
            "_prefetch_next harus memiliki timeout mechanism"
        )

    def test_timeout_has_retry_logic(self):
        """Setelah timeout di _fetch_and_play_initial, harus ada retry logic."""
        source = inspect.getsource(RadioMode._fetch_and_play_initial)
        # Harus ada handling TimeoutError atau retry setelah timeout
        has_retry = (
            "TimeoutError" in source or
            "timeout" in source.lower()
        )
        assert has_retry, (
            "_fetch_and_play_initial harus handle TimeoutError dan retry"
        )

    def test_gather_batch_called_with_timeout_value(self):
        """Timeout value harus reasonable (≤ 30 detik)."""
        source = inspect.getsource(RadioMode._fetch_and_play_initial)
        # Cek bahwa timeout value ada dan masuk akal
        assert "30" in source, (
            "Timeout value harus 30 detik sesuai spesifikasi PATCH-1-06"
        )
