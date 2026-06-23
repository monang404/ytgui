import asyncio
import structlog
from typing import Dict

from core.state import AppState
from core.event_bus import EventBus
from core.command_bus import CommandBus
from engine.mpv_controller import MpvController
from engine.queue_mode import QueueMode
from engine.radio_mode import RadioMode
from engine.volume_service import VolumeService
from engine.playback_controller import PlaybackController
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from cache.resolver import CacheResolver

logger = structlog.get_logger(__name__)

class Room:
    """Represents a single independent playback session (Multi-room)."""
    
    def __init__(self, room_id: str, db, ytdlp, http_session):
        self.room_id = room_id
        self.state = AppState(room_id=room_id)
        
        # Room-specific components
        self.mpv = MpvController(socket_path=f"/tmp/mpv-socket-{room_id}")
        
        self.resolver = CacheResolver(db, ytdlp)
        self.sponsorblock = SponsorBlockHandler(self.mpv, state=self.state, session=http_session)
        self.lyrics_fetcher = LyricsFetcher(self.state, session=http_session)
        
        self.queue_mode = QueueMode()
        self.radio_mode = RadioMode(ytdlp, self.state)
        
        # Inject global bus
        from core.event_bus import bus
        self.volume_service = VolumeService(bus, self.mpv, self.state)
        self.controller = PlaybackController(
            self.room_id, bus, self.state, self.mpv, self.resolver,
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
    """Mengelola multiple room."""
    
    def __init__(self, db, ytdlp, http_session):
        self.db = db
        self.ytdlp = ytdlp
        self.http_session = http_session
        self.rooms: Dict[str, Room] = {}
        
    async def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            logger.info(f"Creating new room: {room_id}")
            room = Room(room_id, self.db, self.ytdlp, self.http_session)
            await room.start()
            self.rooms[room_id] = room
        return self.rooms[room_id]
        
    async def shutdown(self):
        for room in self.rooms.values():
            await room.stop()
        self.rooms.clear()
