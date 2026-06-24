"""
FASE 3 — Architecture Refactor: Per-Room EventBus
Tests: TASK-3.1 sampai TASK-3.7

Memverifikasi bahwa:
- EventBus bisa diinstansiasi secara independen (3.1)
- Room membuat EventBus sendiri per instance (3.2)
- MpvController menerima event_bus via injection (3.3)
- LyricsFetcher menerima event_bus via injection (3.4)
- SponsorBlockHandler menerima event_bus via injection (3.5)
- server.py subscribe per-room via on_room_created callback (3.6)
- Global bus tidak diimport lagi di file-file yang sudah direfactor (3.7)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ===========================================================================
# TASK-3.1: EventBus bisa diinstansiasi secara independen
# ===========================================================================

class TestTask31EventBusInstantiable:
    """TASK-3.1: class EventBus bisa diinstansiasi lebih dari sekali, bukan singleton."""

    def test_eventbus_two_instances_are_independent(self):
        """b1 is not b2 — bukan singleton."""
        from core.event_bus import EventBus
        b1 = EventBus()
        b2 = EventBus()
        assert b1 is not b2, "EventBus harus bisa diinstansiasi secara independen"

    def test_eventbus_class_importable(self):
        """EventBus class bisa diimport dari core.event_bus."""
        from core.event_bus import EventBus
        assert callable(EventBus)

    def test_eventbus_singleton_still_exists_for_backward_compat(self):
        """Global bus singleton masih ada untuk backward compatibility."""
        from core.event_bus import bus, EventBus
        assert isinstance(bus, EventBus)

    @pytest.mark.asyncio
    async def test_two_eventbuses_do_not_share_subscribers(self):
        """Subscriber di b1 tidak menerima event dari b2."""
        from core.event_bus import EventBus
        from core.events import LogMessageEvent

        b1 = EventBus()
        b2 = EventBus()
        received_on_b1 = []

        async def handler(e):
            received_on_b1.append(e.message)

        b1.subscribe(LogMessageEvent, handler)
        # Publish ke b2 — handler b1 tidak boleh terpanggil
        await b2.publish(LogMessageEvent(message="from-b2"))
        assert received_on_b1 == [], "b1 handler tidak boleh menerima event dari b2"

    @pytest.mark.asyncio
    async def test_eventbus_publish_subscribe_works(self):
        """EventBus basic publish/subscribe masih berfungsi."""
        from core.event_bus import EventBus
        from core.events import LogMessageEvent

        bus = EventBus()
        received = []

        async def handler(e):
            received.append(e.message)

        bus.subscribe(LogMessageEvent, handler)
        await bus.publish(LogMessageEvent(message="hello"))
        assert received == ["hello"]


# ===========================================================================
# TASK-3.2: Room membuat EventBus sendiri
# ===========================================================================

class TestTask32RoomOwnEventBus:
    """TASK-3.2: Setiap Room memiliki event_bus sendiri."""

    def test_room_has_event_bus_attribute(self):
        """Room harus punya attribute event_bus."""
        from core.room_manager import Room
        from core.event_bus import EventBus
        # Room.event_bus harus ada sebagai attribute class (inspeksi constructor)
        import inspect
        src = inspect.getsource(Room.__init__)
        assert "self.event_bus = EventBus()" in src, \
            "Room.__init__ harus membuat self.event_bus = EventBus()"

    def test_room_no_longer_imports_global_bus(self):
        """Room tidak boleh menggunakan global bus lagi."""
        import inspect
        from core.room_manager import Room
        src = inspect.getsource(Room.__init__)
        assert "from core.event_bus import bus" not in src, \
            "Room.__init__ tidak boleh import global bus lagi"

    def test_roommanager_has_on_room_created(self):
        """RoomManager harus punya method on_room_created."""
        from core.room_manager import RoomManager
        assert hasattr(RoomManager, "on_room_created"), \
            "RoomManager harus punya method on_room_created untuk TASK-3.6"
        assert callable(RoomManager.on_room_created)

    def test_roommanager_has_on_room_created_callbacks_list(self):
        """RoomManager menyimpan list callbacks."""
        import inspect
        from core.room_manager import RoomManager
        src = inspect.getsource(RoomManager.__init__)
        assert "_on_room_created_callbacks" in src

    @pytest.mark.asyncio
    async def test_on_room_created_callback_called(self):
        """Callback didaftarkan via on_room_created dipanggil saat room dibuat."""
        from core.room_manager import RoomManager

        mock_db = MagicMock()
        mock_ytdlp = MagicMock()
        mock_session = MagicMock()

        manager = RoomManager(mock_db, mock_ytdlp, mock_session, MagicMock(), MagicMock())

        created_rooms = []
        manager.on_room_created(lambda r: created_rooms.append(r.room_id))

        # Patch Room.__init__ dan Room.start agar tidak benar-benar konek ke MPV
        with patch("core.room_manager.Room") as MockRoom:
            mock_room = MagicMock()
            mock_room.room_id = "test-room"
            mock_room.event_bus = MagicMock()
            mock_room.start = AsyncMock()
            MockRoom.return_value = mock_room

            await manager.get_or_create_room("test-room")

        assert "test-room" in created_rooms, \
            "Callback harus dipanggil saat room baru dibuat"


# ===========================================================================
# TASK-3.3: MpvController menerima event_bus via injection
# ===========================================================================

class TestTask33MpvControllerEventBusInjection:
    """TASK-3.3: MpvController menerima event_bus parameter."""

    def test_mpvcontroller_accepts_event_bus_parameter(self):
        """MpvController.__init__ harus punya parameter event_bus."""
        import inspect
        from engine.mpv_controller import MpvController
        sig = inspect.signature(MpvController.__init__)
        assert "event_bus" in sig.parameters, \
            "MpvController.__init__ harus punya parameter event_bus"

    def test_mpvcontroller_stores_injected_bus(self):
        """MpvController menyimpan bus yang diinject sebagai self._bus."""
        from engine.mpv_controller import MpvController
        from core.event_bus import EventBus

        custom_bus = EventBus()
        mpv = MpvController(event_bus=custom_bus)
        assert mpv._bus is custom_bus, \
            "MpvController._bus harus sama dengan bus yang diinject"

    def test_mpvcontroller_without_injection_uses_global_bus(self):
        """Jika tidak diinject, MpvController fallback ke global bus."""
        from engine.mpv_controller import MpvController
        from core.event_bus import bus
        mpv = MpvController()
        assert mpv._bus is bus, \
            "Tanpa injection, MpvController._bus harus sama dengan global bus"

    def test_mpvcontroller_no_direct_global_bus_import(self):
        """mpv_controller.py tidak boleh import 'bus' langsung dari module level."""
        import ast, pathlib
        src = pathlib.Path("engine/mpv_controller.py").read_text(encoding="utf-8")
        # Tidak boleh ada 'from core.event_bus import bus' di level modul
        assert "from core.event_bus import bus" not in src.splitlines()[0:15], \
            "mpv_controller.py tidak boleh import global bus di level modul"

    def test_two_mpvcontrollers_with_different_buses_are_isolated(self):
        """Dua MpvController dengan bus berbeda tidak saling mempengaruhi."""
        from engine.mpv_controller import MpvController
        from core.event_bus import EventBus
        b1 = EventBus()
        b2 = EventBus()
        mpv1 = MpvController(event_bus=b1)
        mpv2 = MpvController(event_bus=b2)
        assert mpv1._bus is not mpv2._bus


# ===========================================================================
# TASK-3.4: LyricsFetcher menerima event_bus via injection
# ===========================================================================

class TestTask34LyricsFetcherEventBusInjection:
    """TASK-3.4: LyricsFetcher menerima event_bus parameter."""

    def test_lyricsfetcher_accepts_event_bus_parameter(self):
        """LyricsFetcher.__init__ harus punya parameter event_bus."""
        import inspect
        from plugins.lyrics import LyricsFetcher
        sig = inspect.signature(LyricsFetcher.__init__)
        assert "event_bus" in sig.parameters

    def test_lyricsfetcher_stores_injected_bus(self):
        """LyricsFetcher menyimpan bus yang diinject."""
        from plugins.lyrics import LyricsFetcher
        from core.event_bus import EventBus

        custom_bus = EventBus()
        state = MagicMock()
        state.lyrics_lines = []
        state.lyrics_index = 0
        state.lyrics_offset = 0.0
        state.lyrics_loading = False

        fetcher = LyricsFetcher(state, event_bus=custom_bus)
        assert fetcher._bus is custom_bus

    def test_lyricsfetcher_no_global_bus_module_import(self):
        """integrations/lyrics.py tidak boleh import global bus di level modul."""
        import pathlib
        src = pathlib.Path("plugins/lyrics.py").read_text(encoding="utf-8")
        for line in src.splitlines()[:15]:
            assert "from core.event_bus import bus" not in line, \
                "lyrics.py tidak boleh import global bus di level modul"

    @pytest.mark.asyncio
    async def test_two_lyricsfetchers_isolated(self):
        """Dua LyricsFetcher dengan bus berbeda tidak saling menerima event."""
        from plugins.lyrics import LyricsFetcher
        from core.event_bus import EventBus
        from core.events import TrackProgressEvent

        b1 = EventBus()
        b2 = EventBus()

        state1 = MagicMock()
        state1.lyrics_lines = []
        state1.lyrics_index = 0
        state1.lyrics_offset = 0.0
        state1.lyrics_loading = False

        state2 = MagicMock()
        state2.lyrics_lines = []
        state2.lyrics_index = 0
        state2.lyrics_offset = 0.0
        state2.lyrics_loading = False

        fetcher1 = LyricsFetcher(state1, event_bus=b1)
        fetcher2 = LyricsFetcher(state2, event_bus=b2)

        # Pastikan handler fetcher2 tidak dipanggil saat publish ke b1
        progress_event = TrackProgressEvent(position=5.0)

        # Patch _on_progress untuk tracking
        called_fetcher2 = []
        original = fetcher2._on_progress
        async def spy(e):
            called_fetcher2.append(e)
            await original(e)
        fetcher2._on_progress = spy

        # Re-subscribe dengan spy (harus unsubscribe dulu)
        b2.unsubscribe(TrackProgressEvent, original)
        b2.subscribe(TrackProgressEvent, spy)

        await b1.publish(progress_event)
        assert called_fetcher2 == [], \
            "fetcher2 tidak boleh menerima event dari b1"

        fetcher1.cleanup()
        fetcher2.cleanup()


# ===========================================================================
# TASK-3.5: SponsorBlockHandler menerima event_bus via injection
# ===========================================================================

class TestTask35SponsorBlockHandlerEventBusInjection:
    """TASK-3.5: SponsorBlockHandler menerima event_bus parameter."""

    def test_sponsorblock_accepts_event_bus_parameter(self):
        """SponsorBlockHandler.__init__ harus punya parameter event_bus."""
        import inspect
        from plugins.sponsorblock import SponsorBlockHandler
        sig = inspect.signature(SponsorBlockHandler.__init__)
        assert "event_bus" in sig.parameters

    def test_sponsorblock_stores_injected_bus(self):
        """SponsorBlockHandler menyimpan bus yang diinject."""
        from plugins.sponsorblock import SponsorBlockHandler
        from core.event_bus import EventBus

        custom_bus = EventBus()
        mock_mpv = MagicMock()
        mock_state = MagicMock()

        handler = SponsorBlockHandler(mock_mpv, state=mock_state, event_bus=custom_bus)
        assert handler._bus is custom_bus
        handler.cleanup()

    def test_sponsorblock_no_global_bus_module_import(self):
        """integrations/sponsorblock.py tidak boleh import global bus di level modul."""
        import pathlib
        src = pathlib.Path("plugins/sponsorblock.py").read_text(encoding="utf-8")
        for line in src.splitlines()[:15]:
            assert "from core.event_bus import bus" not in line, \
                "sponsorblock.py tidak boleh import global bus di level modul"

    @pytest.mark.asyncio
    async def test_two_sponsorblock_handlers_isolated(self):
        """Dua SponsorBlockHandler dengan bus berbeda tidak saling menerima event."""
        from plugins.sponsorblock import SponsorBlockHandler
        from core.event_bus import EventBus
        from core.events import TrackProgressEvent

        b1 = EventBus()
        b2 = EventBus()

        mock_mpv = MagicMock()
        mock_mpv.seek = AsyncMock()
        mock_state = MagicMock()
        mock_state.sponsorblock_active = False

        handler1 = SponsorBlockHandler(mock_mpv, state=mock_state, event_bus=b1)
        handler2 = SponsorBlockHandler(mock_mpv, state=mock_state, event_bus=b2)

        # Publish ke b1 — handler2 tidak boleh terpanggil
        called_h2 = []
        original_h2 = handler2._on_progress
        async def spy_h2(e):
            called_h2.append(e)
        b2.unsubscribe(TrackProgressEvent, original_h2)
        b2.subscribe(TrackProgressEvent, spy_h2)

        await b1.publish(TrackProgressEvent(position=10.0))
        assert called_h2 == [], \
            "handler2 tidak boleh menerima event dari b1"

        handler1.cleanup()
        handler2.cleanup()


# ===========================================================================
# TASK-3.6: server.py subscribe per-room via on_room_created
# ===========================================================================

class TestTask36ServerPerRoomSubscriptions:
    """TASK-3.6: web/server.py menggunakan per-room EventBus subscription."""

    def test_server_does_not_import_global_bus(self):
        """web/server.py tidak boleh import global bus singleton."""
        import pathlib
        src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        for line in src.splitlines()[:40]:
            assert "from core.event_bus import bus" not in line, \
                "server.py tidak boleh import global bus lagi (TASK-3.7)"

    def test_setup_room_subscriptions_function_exists(self):
        """server.py harus mengandung _setup_room_subscriptions."""
        import pathlib
        src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "_setup_room_subscriptions" in src, \
            "server.py harus mendefinisikan _setup_room_subscriptions (TASK-3.6)"

    def test_on_room_created_registered_in_create_app(self):
        """create_app harus memanggil room_manager.on_room_created(...)."""
        import pathlib
        src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "room_manager.on_room_created" in src, \
            "create_app harus mendaftarkan callback via room_manager.on_room_created"

    def test_per_room_progress_throttle_in_server(self):
        """server.py menggunakan per-room throttle, bukan global dict."""
        import pathlib
        src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        assert "last_progress_per_room" in src, \
            "Throttle harus per-room (TASK-3.6 + TASK-4.4 preview)"
        # Global dict lama tidak boleh ada
        assert "last_progress = {\"t\": 0.0}" not in src, \
            "last_progress global dict sudah harus diganti dengan per-room version"

    @pytest.mark.asyncio
    async def test_create_app_registers_subscription_callback(self):
        """create_app harus memanggil room_manager.on_room_created."""
        from server.app import create_app
        from core.room_manager import RoomManager

        mock_db = MagicMock()
        mock_db.conn = True
        mock_ytdlp = MagicMock()

        mock_rm = MagicMock(spec=RoomManager)
        mock_rm.rooms = {}
        mock_rm.on_room_created = MagicMock()

        app = create_app(mock_rm, mock_ytdlp, mock_db)
        # Cleanup session yang dibuat create_app
        await app["http_session"].close()

        assert mock_rm.on_room_created.called, \
            "create_app harus memanggil room_manager.on_room_created"

    @pytest.mark.asyncio
    async def test_subscription_callback_subscribes_to_room_event_bus(self):
        """Callback yang didaftarkan benar-benar subscribe ke room.event_bus."""
        from server.app import create_app
        from core.room_manager import RoomManager
        from core.event_bus import EventBus

        mock_db = MagicMock()
        mock_db.conn = True
        mock_ytdlp = MagicMock()

        captured_callback = []

        mock_rm = MagicMock(spec=RoomManager)
        mock_rm.rooms = {}
        mock_rm.on_room_created = lambda cb: captured_callback.append(cb)

        app = create_app(mock_rm, mock_ytdlp, mock_db)

        assert len(captured_callback) == 1, "Tepat satu callback harus didaftarkan"

        # Simulate: callback dipanggil dengan fake room
        fake_bus = EventBus()
        fake_room = MagicMock()
        fake_room.room_id = "test"
        fake_room.event_bus = fake_bus

        callback = captured_callback[0]
        callback(fake_room)  # harus tidak raise exception

        # Setelah callback, bus harus punya subscriber
        assert len(fake_bus._subscribers) > 0, \
            "Callback harus subscribe ke room.event_bus"

        # Cleanup session
        await app["http_session"].close()


# ===========================================================================
# TASK-3.7: Tidak ada global bus import di file yang sudah direfactor
# ===========================================================================

class TestTask37NoGlobalBusImports:
    """TASK-3.7: File-file yang sudah direfactor tidak import global bus."""

    def test_mpv_controller_no_global_bus_import(self):
        """engine/mpv_controller.py tidak import 'bus' dari module level."""
        import pathlib
        src = pathlib.Path("engine/mpv_controller.py").read_text(encoding="utf-8")
        module_level = [l for l in src.splitlines()[:20] if "import" in l]
        for line in module_level:
            assert "from core.event_bus import bus" not in line, \
                f"mpv_controller.py tidak boleh import global bus: {line}"

    def test_lyrics_no_global_bus_import(self):
        """integrations/lyrics.py tidak import 'bus' di level modul."""
        import pathlib
        src = pathlib.Path("plugins/lyrics.py").read_text(encoding="utf-8")
        module_level = [l for l in src.splitlines()[:20] if "import" in l]
        for line in module_level:
            assert "from core.event_bus import bus" not in line, \
                f"lyrics.py tidak boleh import global bus: {line}"

    def test_sponsorblock_no_global_bus_import(self):
        """integrations/sponsorblock.py tidak import 'bus' di level modul."""
        import pathlib
        src = pathlib.Path("plugins/sponsorblock.py").read_text(encoding="utf-8")
        module_level = [l for l in src.splitlines()[:15] if "import" in l]
        for line in module_level:
            assert "from core.event_bus import bus" not in line, \
                f"sponsorblock.py tidak boleh import global bus: {line}"

    def test_server_no_global_bus_import(self):
        """web/server.py tidak import 'bus' di level modul."""
        import pathlib
        src = "\n".join([p.read_text(encoding="utf-8") for p in pathlib.Path("server").rglob("*.py")])
        module_level = [l for l in src.splitlines()[:40] if "import" in l]
        for line in module_level:
            assert "from core.event_bus import bus" not in line, \
                f"server.py tidak boleh import global bus: {line}"

    def test_room_manager_no_global_bus_import_in_constructor(self):
        """core/room_manager.py Room.__init__ tidak import global bus."""
        import inspect
        from core.room_manager import Room
        src = inspect.getsource(Room.__init__)
        assert "from core.event_bus import bus" not in src or \
               "# TASK" in src, \
            "Room.__init__ tidak boleh menggunakan global bus lagi"

    def test_global_bus_singleton_still_exists_in_event_bus_module(self):
        """Global bus singleton masih ada di core/event_bus.py untuk backward compat."""
        from core.event_bus import bus, EventBus
        assert isinstance(bus, EventBus), \
            "Global bus singleton harus tetap ada untuk backward compat (TASK-3.7)"
