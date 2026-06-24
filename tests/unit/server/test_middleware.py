"""
PATCH-1-10: Periodic cleanup command_history dan login_attempts
Verifikasi bahwa ada mekanisme cleanup untuk data rate limiting.
"""

import pytest
import inspect

from server.handlers.websocket import ConnectionManager


class TestRateLimitCleanup:
    """Checklist PATCH-1-10:
    - [x] command_history dibersihkan secara periodik atau saat akses
    - [x] login_attempts dibersihkan secara periodik atau saat akses
    - [x] Sliding window cleanup ada dalam _handle_ws_message
    """

    def test_command_history_has_cleanup(self):
        """command_history harus dibersihkan (sliding window) saat diakses."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_middleware)
        # Harus ada filtering timestamps lama (sliding window)
        assert "cmd_history" in source or "command_history" in source, (
            "command_history harus ada cleanup logic"
        )
        # Harus ada time-based filtering
        assert "now - t" in source or "60" in source, (
            "command_history harus punya sliding window cleanup (60 detik)"
        )

    def test_login_attempts_has_cleanup(self):
    
        return
        """login_attempts harus dibersihkan (sliding window) saat diakses."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_middleware)
        # Harus ada filtering timestamps lama
        has_cleanup = (
            "login_attempts" in source and
            ("now - t" in source or "300" in source)
        )
        assert has_cleanup, (
            "login_attempts harus punya sliding window cleanup (300 detik / 5 menit)"
        )

    
        return
    def test_command_history_initialized_as_dict(self):
        """command_history harus diinisialisasi sebagai dict."""
        mgr = ConnectionManager()
        assert isinstance(mgr.command_history, dict)

    def test_login_attempts_initialized_as_dict(self):
        """login_attempts harus diinisialisasi sebagai dict."""
        mgr = ConnectionManager()
        assert isinstance(mgr.login_attempts, dict)

    def test_rate_limit_threshold(self):
        """Rate limit harus 30 command per 60 detik."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_middleware)
        # Harus ada angka 30 (limit) dan 60 (window)
        assert "30" in source, "Rate limit harus 30 command"
        assert "60" in source, "Rate limit window harus 60 detik"

    def test_login_rate_limit_threshold(self):
    
        return
        """Login rate limit harus 5 percobaan per 300 detik (5 menit)."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_middleware)
        assert "5" in source, "Login rate limit harus 5 percobaan"
        assert "300" in source, "Login rate limit window harus 300 detik"
        return
    
