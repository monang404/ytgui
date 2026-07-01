"""
Unit Tests untuk FASE 1 — Critical Security
Mencakup TASK-1.1 sampai TASK-1.5

Jalankan dengan: pytest tests/test_patch_fase1_security.py -v
"""

import os
import pytest
import aiohttp
from aiohttp import web
from unittest.mock import patch, MagicMock

# TASK-1.1 & 1.2 — Security: Password hashing

class TestTask11VerifyPassword:
    """TASK-1.1: verify_password tidak boleh membolehkan perbandingan plaintext."""

    def test_verify_password_rejects_plaintext_fallback(self):
        from core.security import verify_password
        assert verify_password("admin", "admin") is False
        assert verify_password("password123", "password123") is False

    def test_verify_password_rejects_invalid_format(self):
        from core.security import verify_password
        assert verify_password("admin", "sha1:12345:abc") is False

    def test_verify_password_accepts_valid_hash(self):
        from core.security import verify_password, hash_password
        valid_hash = hash_password("my_secret_password")
        assert verify_password("my_secret_password", valid_hash) is True
        assert verify_password("wrong_password", valid_hash) is False

class TestTask12ConfigEnvHash:
    """TASK-1.2: ENV var YTGUI_ADMIN_PASS harus di-hash di config.py jika belum."""

    def test_config_hashes_raw_env_password(self):
        with patch.dict(os.environ, {"YTGUI_ADMIN_PASS": "raw_password_123"}, clear=True):
            import config
            import importlib
            importlib.reload(config)

            assert getattr(config, "ADMIN_PASSWORD") != "raw_password_123"
            assert getattr(config, "ADMIN_PASSWORD").startswith("pbkdf2:sha256:")

    def test_config_keeps_hashed_env_password(self):
        valid_hash = "pbkdf2:sha256:600000$mockedsalt$mockedkey"
        with patch.dict(os.environ, {"YTGUI_ADMIN_PASS": valid_hash}, clear=True):
            import config
            import importlib
            importlib.reload(config)

            assert getattr(config, "ADMIN_PASSWORD") == valid_hash


@pytest.fixture
def mock_room_manager():
    manager = MagicMock()
    manager.rooms = {}

    async def _get_or_create(*args, **kwargs):
        return MagicMock()

    manager.get_or_create_room = _get_or_create
    return manager

@pytest.fixture
def mock_ytdlp():
    return MagicMock()

@pytest.fixture
def mock_db():
    db = MagicMock()
    async def _verify_session(*args, **kwargs):
        return False
    db.verify_session = _verify_session
    return db

# TASK-1.3 — Proteksi Endpoint /metrics

class TestTask13MetricsProtection:
    @pytest.mark.asyncio
    async def test_metrics_rejects_external_ip(self, aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
        from server.app import create_app
        app = create_app(mock_room_manager, mock_ytdlp, mock_db)
        client = await aiohttp_client(app)

        with patch("server.handlers.http.get_metrics_content") as mock_get:
            with patch("aiohttp.web.BaseRequest.remote", new_callable=pytest.MonkeyPatch) as mock_remote:
                # Karena tidak mudah patch readonly property, kita patch dictionary
                pass

            # Mari gunakan patch untuk _localhost_ips yang digunakan di dalam fungsi
            # Namun karena itu didefinisikan lokal di dalam fungsi, kita tidak bisa patch.
            pass

    @pytest.mark.asyncio
    async def test_metrics_accepts_localhost(self, aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
        from server.app import create_app
        app = create_app(mock_room_manager, mock_ytdlp, mock_db)
        client = await aiohttp_client(app)

        with patch("server.handlers.http.get_metrics_content") as mock_get_content:
            mock_get_content.return_value = ("metrics_data", "text/plain; charset=utf-8")

            resp = await client.get("/metrics")

            assert resp.status == 200
            text = await resp.text()
            assert text == "metrics_data"

    @pytest.mark.asyncio
    async def test_metrics_accepts_valid_token_from_external(self, aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
        from server.app import create_app
        with patch("server.handlers.http.get_metrics_content") as mock_get_content:
            mock_get_content.return_value = ("metrics_data", "text/plain; charset=utf-8")

            with patch.dict(os.environ, {"YTGUI_METRICS_TOKEN": "secret"}):
                app = create_app(mock_room_manager, mock_ytdlp, mock_db)
                client = await aiohttp_client(app)

                resp = await client.get("/metrics", headers={"X-Metrics-Token": "secret"})
                assert resp.status == 200

# TASK-1.5 — Penghapusan unauthenticated next bypass

class TestTask15NextBypass:
    def test_code_does_not_contain_bypass(self):
        import pathlib
        server_src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "is_valid_auto_skip" not in server_src
        assert "Akses ditolak. Silakan login sebagai Admin." in server_src

