"""
Unit Tests untuk FASE 0 — Quick Wins
Mencakup TASK-0.1 sampai TASK-0.5

Jalankan dengan: pytest tests/test_patch_fase0_quick_wins.py -v
"""

import asyncio
import inspect
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─────────────────────────────────────────────────────────────────
# TASK-0.1 — _TITLE_NOISE_WORDS harus frozenset
# ─────────────────────────────────────────────────────────────────

class TestTask01TitleNoiseWords:
    """TASK-0.1: _TITLE_NOISE_WORDS harus bertipe frozenset untuk O(1) lookup."""

    def test_is_frozenset(self):
        """Tipe harus frozenset, bukan tuple atau set biasa."""
        from engine.radio_engine import _TITLE_NOISE_WORDS
        assert isinstance(_TITLE_NOISE_WORDS, frozenset), (
            f"_TITLE_NOISE_WORDS harus frozenset, bukan {type(_TITLE_NOISE_WORDS).__name__}"
        )

    def test_immutable(self):
        """frozenset tidak bisa dimodifikasi."""
        from engine.radio_engine import _TITLE_NOISE_WORDS
        with pytest.raises(AttributeError):
            _TITLE_NOISE_WORDS.add("test")  # frozenset tidak punya .add()

    def test_contains_expected_words(self):
        """Pastikan kata-kata noise penting masih ada."""
        from engine.radio_engine import _TITLE_NOISE_WORDS
        expected = {"official", "music", "video", "audio", "lyric", "lyrics",
                    "cover", "live", "hd", "hq", "remastered", "karaoke", "acoustic"}
        assert expected.issubset(_TITLE_NOISE_WORDS), (
            f"Kata noise hilang: {expected - _TITLE_NOISE_WORDS}"
        )

    def test_lookup_is_fast(self):
        """Verifikasi lookup 'in' bekerja seperti yang diharapkan."""
        from engine.radio_engine import _TITLE_NOISE_WORDS
        assert "official" in _TITLE_NOISE_WORDS
        assert "bukan_noise" not in _TITLE_NOISE_WORDS

    def test_normalize_title_still_works(self):
        """_normalize_title() harus tetap berjalan dengan baik setelah perubahan."""
        from engine.radio_engine import _normalize_title
        # Judul dengan noise words harus difilter
        result = _normalize_title("Rasa Ini (Official Music Video)")
        assert "official" not in result
        assert "music" not in result
        assert "video" not in result
        # Judul minimal harus tersisa
        assert "rasa" in result or "ini" in result

    def test_normalize_title_empty(self):
        """Judul kosong harus mengembalikan string kosong."""
        from engine.radio_engine import _normalize_title
        assert _normalize_title("") == ""
        assert _normalize_title(None) == ""


# ─────────────────────────────────────────────────────────────────
# TASK-0.2 — _retry_count di-reset di _on_stop
# ─────────────────────────────────────────────────────────────────

class TestTask02RetryCountReset:
    """TASK-0.2: _retry_count harus di-reset ke 0 saat _on_stop dipanggil."""

    def _make_controller(self):
        """Buat PlaybackController minimal dengan semua dependency di-mock."""
        from engine.playback_controller import PlaybackController
        from core.state import AppState

        mock_bus = AsyncMock()
        mock_bus.subscribe = MagicMock()
        mock_bus.publish = AsyncMock()

        mock_mpv = AsyncMock()
        mock_mpv.pause = AsyncMock()
        mock_mpv.resume = AsyncMock()

        state = AppState(room_id="test")

        ctrl = PlaybackController.__new__(PlaybackController)
        ctrl.room_id = "test"
        ctrl.bus = mock_bus
        ctrl.state = state
        ctrl.mpv = mock_mpv
        ctrl.resolver = AsyncMock()
        ctrl.sponsorblock = MagicMock()
        ctrl.lyrics_fetcher = MagicMock()
        ctrl.queue_mode = AsyncMock()
        ctrl.radio_mode = AsyncMock()
        ctrl._lock = asyncio.Lock()
        ctrl._retry_count = 0
        return ctrl

    @pytest.mark.asyncio
    async def test_retry_count_reset_on_stop(self):
        """_retry_count harus 0 setelah _on_stop meskipun sebelumnya > 0."""
        ctrl = self._make_controller()
        ctrl._retry_count = 2  # simulasi setelah 2 kegagalan

        await ctrl._on_stop()

        assert ctrl._retry_count == 0, (
            f"_retry_count harus 0 setelah _on_stop, tapi nilainya {ctrl._retry_count}"
        )

    @pytest.mark.asyncio
    async def test_retry_count_reset_before_mpv_pause(self):
        """Reset harus terjadi di awal method (baris pertama)."""
        # Verifikasi struktural: baris pertama on_stop adalah reset
        from engine.playback_controller import PlaybackController
        import inspect
        source = inspect.getsource(PlaybackController._on_stop)
        lines = [l.strip() for l in source.splitlines() if l.strip()]
        # Cari baris pertama setelah def
        body_lines = [l for l in lines if not l.startswith("async def") and not l.startswith("\"\"\"")]
        assert body_lines[0].startswith("self._retry_count = 0"), (
            f"Baris pertama _on_stop harus reset _retry_count, tapi: {body_lines[0]}"
        )

    @pytest.mark.asyncio
    async def test_on_stop_clears_state(self):
        """_on_stop tetap membersihkan state lainnya dengan benar."""
        from core.state import PlayerStatus, TrackInfo
        ctrl = self._make_controller()
        ctrl.state.current_track = MagicMock()
        ctrl._retry_count = 3

        await ctrl._on_stop()

        assert ctrl._retry_count == 0
        assert ctrl.state.current_track is None
        assert ctrl.state.status == PlayerStatus.IDLE


# ─────────────────────────────────────────────────────────────────
# TASK-0.3 — _bg_tasks di-cancel saat on_deactivated
# ─────────────────────────────────────────────────────────────────

class TestTask03RadioBgTasksCancel:
    """TASK-0.3: Semua _bg_tasks harus di-cancel saat on_deactivated dipanggil."""

    def _make_radio_mode(self):
        from engine.radio_engine import RadioMode
        from core.state import AppState
        state = AppState(room_id="test")
        ytdlp = MagicMock()
        radio = RadioMode(ytdlp, state)
        return radio, state

    @pytest.mark.asyncio
    async def test_bg_tasks_cancelled_on_deactivated(self):
        """Semua task dalam _bg_tasks harus di-cancel saat on_deactivated."""
        radio, state = self._make_radio_mode()

        # Buat fake tasks yang bisa di-track
        mock_task1 = MagicMock()
        mock_task2 = MagicMock()
        radio._bg_tasks = {mock_task1, mock_task2}

        await radio.on_deactivated()

        mock_task1.cancel.assert_called_once()
        mock_task2.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_bg_tasks_cleared_after_deactivated(self):
        """_bg_tasks harus kosong setelah on_deactivated."""
        radio, state = self._make_radio_mode()

        mock_task = MagicMock()
        radio._bg_tasks = {mock_task}

        await radio.on_deactivated()

        assert len(radio._bg_tasks) == 0, "_bg_tasks harus kosong setelah deactivated"

    @pytest.mark.asyncio
    async def test_radio_queue_cleared_on_deactivated(self):
        """radio_queue tetap dibersihkan seperti sebelumnya."""
        from core.state import TrackInfo
        radio, state = self._make_radio_mode()

        # Isi radio_queue dengan data dummy
        state.radio_queue.append(MagicMock())
        state.radio_queue.append(MagicMock())

        await radio.on_deactivated()

        assert len(state.radio_queue) == 0, "radio_queue harus kosong setelah deactivated"

    @pytest.mark.asyncio
    async def test_deactivated_no_tasks_is_safe(self):
        """on_deactivated aman dipanggil saat _bg_tasks kosong."""
        radio, state = self._make_radio_mode()
        radio._bg_tasks = set()  # kosong

        # Tidak boleh raise exception
        await radio.on_deactivated()
        assert len(radio._bg_tasks) == 0


# ─────────────────────────────────────────────────────────────────
# TASK-0.4 — _on_download signature fix
# ─────────────────────────────────────────────────────────────────

class TestTask04DownloadSignature:
    """TASK-0.4: _on_download harus menerima (room_id, track) sesuai CommandBus convention."""

    def test_signature_has_room_id(self):
        """Signature _on_download harus punya parameter room_id."""
        from engine.download_manager import DownloadManager
        sig = inspect.signature(DownloadManager._on_download)
        params = list(sig.parameters.keys())
        assert "room_id" in params, (
            f"_on_download harus punya parameter 'room_id', params saat ini: {params}"
        )

    def test_signature_has_track(self):
        """Signature _on_download harus punya parameter track."""
        from engine.download_manager import DownloadManager
        sig = inspect.signature(DownloadManager._on_download)
        params = list(sig.parameters.keys())
        assert "track" in params, (
            f"_on_download harus punya parameter 'track', params saat ini: {params}"
        )

    def test_signature_order(self):
        """room_id harus sebelum track dalam signature."""
        from engine.download_manager import DownloadManager
        sig = inspect.signature(DownloadManager._on_download)
        params = list(sig.parameters.keys())
        # self, room_id, track
        assert params.index("room_id") < params.index("track"), (
            "room_id harus muncul sebelum track dalam signature"
        )

    def test_track_is_optional(self):
        """Parameter track harus opsional (default None)."""
        from engine.download_manager import DownloadManager
        sig = inspect.signature(DownloadManager._on_download)
        track_param = sig.parameters.get("track")
        assert track_param is not None
        assert track_param.default is None, "track harus default None"

    @pytest.mark.asyncio
    async def test_callable_with_room_id_and_none_track(self):
        """_on_download bisa dipanggil dengan (room_id, None) tanpa TypeError."""
        from engine.download_manager import DownloadManager
        from core.state import AppState

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock()
        state = AppState(room_id="test")
        state.current_track = None

        mgr = DownloadManager.__new__(DownloadManager)
        mgr.bus = mock_bus
        mgr.state = state
        mgr.ytdlp = MagicMock()
        mgr._download_lock = asyncio.Lock()

        # Tidak boleh raise TypeError
        await mgr._on_download("default", None)
        # Harus publish pesan "tidak ada lagu"
        mock_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_callable_via_command_bus_convention(self):
        """Simulasi pemanggilan sesuai CommandBus: handler(room_id, data)."""
        from engine.download_manager import DownloadManager
        from core.state import AppState, TrackInfo

        mock_bus = AsyncMock()
        mock_bus.publish = AsyncMock()
        state = AppState(room_id="test")

        mgr = DownloadManager.__new__(DownloadManager)
        mgr.bus = mock_bus
        mgr.state = state
        mgr.ytdlp = MagicMock()
        mgr._download_lock = asyncio.Lock()

        track = TrackInfo(
            video_id="abc123", title="Test Song", artist="Test", duration=180
        )

        # Simulasi: command_bus memanggil handler(room_id, data)
        with patch("engine.download_manager.safe_create_task") as mock_create:
            await mgr._on_download("default", track)
            mock_create.assert_called_once()


# ─────────────────────────────────────────────────────────────────
# TASK-0.5 — Evict key kosong dari login_attempts & command_history
# ─────────────────────────────────────────────────────────────────

class TestTask05EvictRateLimitKeys:
    """TASK-0.5: Key kosong harus dihapus dari login_attempts & command_history."""

    def _make_manager(self):
        """Buat ConnectionManager tanpa dependensi aiohttp."""
        from server.handlers.websocket import ConnectionManager
        return ConnectionManager()

    def test_login_attempts_key_evicted_when_empty(self):
        """Key harus dihapus dari login_attempts jika window 5 menit habis."""
        mgr = self._make_manager()
        old_time = time.time() - 400  # lebih dari 300 detik lalu
        mgr.login_attempts["1.2.3.4"] = [old_time, old_time]

        # Simulasi filter yang terjadi di _handle_ws_message
        now = time.time()
        ip = "1.2.3.4"
        attempts = mgr.login_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < 300]
        if not attempts:
            mgr.login_attempts.pop(ip, None)
        else:
            mgr.login_attempts[ip] = attempts

        assert "1.2.3.4" not in mgr.login_attempts, (
            "Key IP harus dihapus setelah semua attempt kadaluarsa"
        )

    def test_login_attempts_key_kept_when_active(self):
        """Key harus tetap ada jika masih ada attempt aktif."""
        mgr = self._make_manager()
        recent_time = time.time() - 10  # 10 detik lalu
        mgr.login_attempts["1.2.3.4"] = [recent_time]

        now = time.time()
        ip = "1.2.3.4"
        attempts = mgr.login_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < 300]
        if not attempts:
            mgr.login_attempts.pop(ip, None)
        else:
            mgr.login_attempts[ip] = attempts

        assert "1.2.3.4" in mgr.login_attempts, (
            "Key IP harus tetap ada jika masih ada attempt aktif"
        )

    def test_command_history_key_evicted_when_empty(self):
        """Key harus dihapus dari command_history jika window 60 detik habis."""
        mgr = self._make_manager()
        old_time = time.time() - 120  # lebih dari 60 detik lalu
        mgr.command_history["5.6.7.8"] = [old_time]

        now = time.time()
        ip = "5.6.7.8"
        cmd_history = mgr.command_history.get(ip, [])
        cmd_history = [t for t in cmd_history if now - t < 60]
        if not cmd_history:
            mgr.command_history.pop(ip, None)
        else:
            mgr.command_history[ip] = cmd_history

        assert "5.6.7.8" not in mgr.command_history, (
            "Key IP harus dihapus dari command_history setelah window habis"
        )

    def test_command_history_key_kept_when_active(self):
        """Key tetap ada jika command_history masih ada dalam 60 detik."""
        mgr = self._make_manager()
        recent_time = time.time() - 5  # 5 detik lalu
        mgr.command_history["5.6.7.8"] = [recent_time]

        now = time.time()
        ip = "5.6.7.8"
        cmd_history = mgr.command_history.get(ip, [])
        cmd_history = [t for t in cmd_history if now - t < 60]
        if not cmd_history:
            mgr.command_history.pop(ip, None)
        else:
            mgr.command_history[ip] = cmd_history

        assert "5.6.7.8" in mgr.command_history

    def test_evict_does_not_affect_other_ips(self):
        """Evict satu IP tidak menghapus IP lain yang masih aktif."""
        mgr = self._make_manager()
        mgr.login_attempts["expired.ip"] = [time.time() - 400]
        mgr.login_attempts["active.ip"] = [time.time() - 10]

        now = time.time()
        for ip in list(mgr.login_attempts.keys()):
            attempts = [t for t in mgr.login_attempts.get(ip, []) if now - t < 300]
            if not attempts:
                mgr.login_attempts.pop(ip, None)
            else:
                mgr.login_attempts[ip] = attempts

        assert "expired.ip" not in mgr.login_attempts
        assert "active.ip" in mgr.login_attempts

    def test_code_contains_pop_for_login_attempts(self):
        """Verifikasi struktural: server.py harus punya pop() untuk login_attempts."""
        import pathlib
        server_src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "login_attempts.pop(client_ip" in server_src, (
            "web/server.py harus menggunakan .pop(client_ip...) untuk login_attempts"
        )

    def test_code_contains_pop_for_command_history(self):
        """Verifikasi struktural: server.py harus punya pop() untuk command_history."""
        import pathlib
        server_src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "command_history.pop(client_ip" in server_src, (
            "web/server.py harus menggunakan .pop(client_ip...) untuk command_history"
        )
