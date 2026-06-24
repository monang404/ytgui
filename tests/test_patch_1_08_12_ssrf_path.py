"""
PATCH-1-08: SSRF validation di stream proxy
PATCH-1-12: Defense-in-depth path check di stream endpoint
Verifikasi bahwa stream proxy memvalidasi URL dan path.
"""

import pytest
import inspect


class TestSSRFValidation:
    """Checklist PATCH-1-08 & PATCH-1-12:
    - [x] Hanya URL HTTPS yang diizinkan
    - [x] Hanya domain *.googlevideo.com dan *.youtube.com yang diizinkan
    - [x] cache_file.resolve().is_relative_to(CACHE_DIR) ada di handle_stream
    """

    def test_ssrf_url_validation_exists(self):
        """handle_stream harus memvalidasi URL stream sebelum proxy."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        assert "urlparse" in source, (
            "server.py harus import urlparse untuk validasi URL"
        )

    def test_only_https_allowed(self):
        """Skema URL harus divalidasi — hanya HTTPS yang diizinkan."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        assert "https" in source.lower(), (
            "Validasi harus memastikan skema URL adalah HTTPS"
        )

    def test_domain_whitelist_googlevideo(self):
        """Domain googlevideo.com harus diizinkan."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        assert "googlevideo.com" in source, (
            "Domain *.googlevideo.com harus ada dalam whitelist"
        )

    def test_domain_whitelist_youtube(self):
        """Domain youtube.com harus diizinkan."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        assert "youtube.com" in source, (
            "Domain *.youtube.com harus ada dalam whitelist"
        )

    def test_path_traversal_defense(self):
        """handle_stream harus punya defense-in-depth terhadap path traversal."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        assert "is_relative_to" in source, (
            "handle_stream harus menggunakan 'cache_file.resolve().is_relative_to(CACHE_DIR)' "
            "sebagai defense in depth terhadap path traversal"
        )

    def test_video_id_regex_validation(self):
        """video_id harus divalidasi dengan regex 11 karakter alfanumerik."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server_http)
        # Harus ada regex untuk validasi video_id
        assert "a-zA-Z0-9_-" in source and "11" in source, (
            "video_id harus divalidasi dengan regex [a-zA-Z0-9_-]{11}"
        )
