"""
PATCH-1-04: Fix _on_queue_remove tidak punya lock (HIDDEN-05)
Verifikasi bahwa _on_queue_remove menggunakan self._lock.
"""

import pytest
import inspect

from engine.playback import PlaybackController


class TestQueueRemoveLock:
    """Checklist PATCH-1-04:
    - [x] Kode _on_queue_remove menggunakan 'async with self._lock:'
    """

    def test_on_queue_remove_uses_lock(self):
        """_on_queue_remove HARUS menggunakan 'async with self._lock'."""
        source = inspect.getsource(PlaybackController._on_queue_remove)
        assert "async with self._lock" in source, (
            "_on_queue_remove HARUS menggunakan 'async with self._lock:' "
            "untuk mencegah race condition dengan _on_queue_select"
        )

    def test_on_queue_select_uses_lock(self):
        """_on_queue_select juga HARUS menggunakan self._lock (sanity check)."""
        source = inspect.getsource(PlaybackController._on_queue_select)
        assert "async with self._lock" in source, (
            "_on_queue_select harus menggunakan 'async with self._lock:'"
        )

    def test_on_next_uses_lock(self):
        """_on_next juga HARUS menggunakan self._lock (sanity check)."""
        source = inspect.getsource(PlaybackController._on_next)
        assert "async with self._lock" in source, (
            "_on_next harus menggunakan 'async with self._lock:'"
        )
