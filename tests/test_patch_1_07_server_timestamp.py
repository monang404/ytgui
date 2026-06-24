"""
PATCH-1-07: Server-side timestamp di progress broadcast (drift correction)
Verifikasi bahwa progress broadcast mengandung server_ts.
"""

import pytest
import inspect


class TestProgressServerTimestamp:
    """Checklist PATCH-1-07:
    - [x] Payload 'progress' dari server mengandung 'server_ts' (float)
    """

    def test_progress_broadcast_contains_server_ts(self):
        """_on_track_progress di server.py harus mengirim server_ts."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server)
        
        # Cari di bagian progress broadcast
        assert "server_ts" in source, (
            "Progress broadcast harus mengandung 'server_ts' untuk drift correction"
        )

    def test_progress_broadcast_uses_time(self):
        """server_ts harus menggunakan time.time() atau time.monotonic()."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server)
        
        # Harus import time dan menggunakannya
        has_time_call = (
            "time.time()" in source or
            "time.monotonic()" in source
        )
        assert has_time_call, (
            "server_ts harus diisi dengan time.time() atau time.monotonic()"
        )

    def test_progress_data_structure(self):
        """Payload progress harus punya position, status, dan server_ts."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server)
        
        # Cari pattern progress data yang lengkap
        assert "\"position\"" in source or "'position'" in source
        assert "\"server_ts\"" in source or "'server_ts'" in source
        assert "\"status\"" in source or "'status'" in source
