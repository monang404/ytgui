import asyncio
import structlog
from typing import Dict, Callable, List

from core.state import AppState
from core.event_bus import EventBus
from core.command_bus import CommandBus
from engine.mpv_controller import MpvController
from engine.queue_manager import QueueMode
from engine.radio_engine import RadioMode
from engine.volume_service import VolumeService
from engine.playback import PlaybackController
from cache.resolver import CacheResolver

logger = structlog.get_logger(__name__)

class Room:
    """Represents a single independent playback session (Multi-room).
    
    TASK-3.2: Setiap Room membuat EventBus sendiri sehingga event dari
    satu room tidak bocor ke room lain (isolasi penuh).
    """
    
    def __init__(self, room_id: str, db, ytdlp, http_session, sponsorblock_factory, lyrics_factory):
        self.room_id = room_id
        self.state = AppState(room_id=room_id)
        
        # TASK-3.2: Per-room EventBus — isolasi penuh antar room
        self.event_bus = EventBus()
        
        # Room-specific components — semua mendapat bus yang sama (per-room)
        # A-04: port unik per-room agar multi-room Windows tidak conflict
        _win_port = str(12345 + (abs(hash(room_id)) % 800))
        self.mpv = MpvController(
            socket_path=f"/tmp/mpv-socket-{room_id}",
            tcp_port=_win_port,
            event_bus=self.event_bus,  # TASK-3.3: inject per-room bus
            room_id=room_id,           # BACKEND-FIX-02: agar events punya room_id benar
        )
        
        self.resolver = CacheResolver(db, ytdlp)
        self.sponsorblock = sponsorblock_factory(
            self.mpv, state=self.state, session=http_session,
            event_bus=self.event_bus  # TASK-3.5: inject per-room bus
        )
        self.lyrics_fetcher = lyrics_factory(
            self.state, session=http_session,
            event_bus=self.event_bus  # TASK-3.4: inject per-room bus
        )
        
        self.queue_mode = QueueMode()
        self.radio_mode = RadioMode(ytdlp, self.state, db=db)
        
        # TASK-3.2: Inject per-room bus ke VolumeService dan PlaybackController
        self.volume_service = VolumeService(self.event_bus, self.mpv, self.state)
        self.controller = PlaybackController(
            self.room_id, self.event_bus, self.state, self.mpv, self.resolver,
            self.sponsorblock, self.lyrics_fetcher, self.queue_mode, self.radio_mode
        )
        
    async def start(self):
        try:
            await self.mpv.connect()
        except Exception as e:
            logger.warning(f"MPV failed to start in room {self.room_id}: {e}")
            
    async def stop(self):
        await self.mpv.close()
        self.lyrics_fetcher.cleanup()
        self.sponsorblock.cleanup()

class RoomManager:
    """Mengelola multiple room.
    
    TASK-3.6: Menyediakan mekanisme callback `on_room_created` agar
    web/server.py bisa subscribe ke event_bus per-room setiap kali
    room baru dibuat.
    """
    
    def __init__(self, db, ytdlp, http_session, sponsorblock_factory, lyrics_factory):
        self.db = db
        self.ytdlp = ytdlp
        self.http_session = http_session
        self.sponsorblock_factory = sponsorblock_factory
        self.lyrics_factory = lyrics_factory
        self.rooms: Dict[str, Room] = {}
        # TASK-3.6: Callbacks dipanggil saat room baru dibuat
        self._on_room_created_callbacks: List[Callable[[Room], None]] = []
        
    def on_room_created(self, callback: Callable[[Room], None]):
        """Register callback yang dipanggil setiap kali room baru dibuat.
        Digunakan oleh web/server.py untuk subscribe ke room.event_bus.
        """
        self._on_room_created_callbacks.append(callback)
        
    async def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            logger.info(f"Creating new room: {room_id}")
            room = Room(room_id, self.db, self.ytdlp, self.http_session, self.sponsorblock_factory, self.lyrics_factory)
            await room.start()
            self.rooms[room_id] = room
            # TASK-3.6: Notify server untuk subscribe per-room
            for cb in self._on_room_created_callbacks:
                try:
                    cb(room)
                except Exception as e:
                    logger.error(f"on_room_created callback error: {e}")
        return self.rooms[room_id]
        
    async def shutdown(self):
        for room in self.rooms.values():
            await room.stop()
        self.rooms.clear()

