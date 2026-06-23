"""
PATCH-0-04: Fix TTL mismatch — konstanta STREAM_URL_TTL_SEC
Verifikasi bahwa ada satu konstanta TTL yang dipakai konsisten
di config, resolver, dan server.
"""

import pytest
import inspect


class TestTTLConstantConsistency:
    """Checklist PATCH-0-04:
    - [x] config.py punya konstanta STREAM_URL_TTL_SEC = 21600
    - [x] resolver.py pakai STREAM_URL_TTL_SEC (bukan magic number)
    - [x] web/server.py pakai STREAM_URL_TTL_SEC (bukan 7200)
    """

    def test_config_has_stream_url_ttl_sec(self):
        """config.py harus export konstanta STREAM_URL_TTL_SEC."""
        from config import STREAM_URL_TTL_SEC
        assert STREAM_URL_TTL_SEC == 21600, (
            f"STREAM_URL_TTL_SEC harus 21600 (6 jam), ditemukan {STREAM_URL_TTL_SEC}"
        )

    def test_resolver_uses_config_constant(self):
        """resolver.py harus import dan menggunakan STREAM_URL_TTL_SEC dari config."""
        from cache import resolver
        source = inspect.getsource(resolver)
        assert "STREAM_URL_TTL_SEC" in source, (
            "resolver.py harus menggunakan STREAM_URL_TTL_SEC dari config, bukan magic number"
        )
        # Pastikan tidak ada magic number 7200 atau 21600 langsung
        # (kecuali dalam komentar)
        lines = source.split("\n")
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert "7200" not in stripped, (
                f"resolver.py masih menggunakan magic number 7200: {stripped}"
            )

    def test_server_uses_config_constant(self):
        """web/server.py harus import dan menggunakan STREAM_URL_TTL_SEC dari config."""
        from web import server
        source = inspect.getsource(server)
        assert "STREAM_URL_TTL_SEC" in source, (
            "server.py harus menggunakan STREAM_URL_TTL_SEC dari config, bukan magic number"
        )
        # Pastikan magic number 7200 tidak ada dalam kode (selain komentar)
        lines = source.split("\n")
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#") or stripped.startswith("\"\"\""):
                continue
            assert "7200" not in stripped, (
                f"server.py masih menggunakan magic number 7200: {stripped}"
            )

    def test_no_hardcoded_ttl_in_resolver(self):
        """resolver.py TIDAK BOLEH ada angka 21600 hardcoded (harus dari config)."""
        from cache import resolver
        source = inspect.getsource(resolver)
        lines = source.split("\n")
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert "21600" not in stripped, (
                f"resolver.py masih hardcode 21600, seharusnya pakai STREAM_URL_TTL_SEC: {stripped}"
            )
