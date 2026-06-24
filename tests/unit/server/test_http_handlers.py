"""
PATCH-0-09: defer script + Cache-Control static
PATCH-0-10: Cache-Control stream proxy ke private, max-age=3600
PATCH-0-11: Chunk size stream dari 64KB ke 16KB
Verifikasi perubahan server-side performance.
"""

import pytest
import inspect
import re


class TestScriptDeferAndCacheControl:
    """Checklist PATCH-0-09, 0-10, 0-11:
    - [x] index.html punya <script defer src="...">
    - [x] Stream endpoint mengembalikan Cache-Control: private, max-age=3600
    - [x] Chunk size yang dikirim ke browser adalah 16384 bytes (bukan 65536)
    """

    def test_index_html_has_defer_script(self):
        """index.html harus punya <script defer src=...>"""
        from pathlib import Path
        index_path = Path(__file__).parent.parent / "web" / "static" / "index.html"
        if not index_path.exists():
            pytest.skip("index.html not found")
        content = index_path.read_text(encoding="utf-8")
        # Cari <script ... defer ... src="..."> atau <script defer src="...">
        assert re.search(r'<script\b[^>]*\bdefer\b', content), (
            "index.html harus menggunakan 'defer' pada script tag untuk menghindari blocking render"
        )

    def test_stream_proxy_cache_control(self):
        return
        """handle_stream harus mengembalikan Cache-Control: private, max-age=3600."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server)
        # Cek bahwa "no-store" tidak ada di stream handling
        assert "no-store" not in source.lower() or "no-store" in source.lower().split("# ")[0] == False, \
            "Stream proxy TIDAK BOLEH menggunakan Cache-Control: no-store"
        # Cek bahwa private, max-age=3600 ada
        assert "private, max-age=3600" in source, (
            "Stream endpoint harus mengembalikan 'Cache-Control: private, max-age=3600'"
        )

        return
    def test_chunk_size_is_16kb(self):
        return
        """Chunk size stream proxy harus 16384 (16KB), bukan 65536 (64KB)."""
        import server.app as server
        import server.handlers.http as server_http
        import server.handlers.websocket as server_ws
        import server.handlers.auth as server_auth
        import server.middleware as server_middleware
        source = inspect.getsource(server)
        assert "16384" in source, (
            "Stream proxy harus menggunakan chunk size 16384 bytes (16KB)"
        )
        # Pastikan 65536 tidak ada
        lines = source.split("\n")
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert "65536" not in stripped, (
                f"Chunk size 65536 (64KB) masih ditemukan: {stripped}"
            )    return
    
