import time
import structlog
from core.events import (
    TrackStartedEvent, TrackProgressEvent, QueueUpdatedEvent, LyricsUpdatedEvent,
    DownloadCompleteEvent, LogMessageEvent, TrackPauseChangedEvent
)
from core.task_utils import safe_create_task
from core.room_manager import RoomManager
from server.services.stream_prefetch import StreamPrefetchService
from server.services.broadcast_service import BroadcastService

logger = structlog.get_logger(__name__)

def setup_event_listeners(
    room_manager: RoomManager, 
    prefetch_service: StreamPrefetchService, 
    broadcast_service: BroadcastService
):
    last_progress_per_room: dict[str, float] = {}

    async def _on_track_started(event: TrackStartedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        # B-03: prefetch URL untuk track BERIKUTNYA di queue atau radio_queue
        # (current track sudah di-resolve oleh CacheResolver sesaat sebelumnya)
        _next = None
        if room.state.queue:
            _next = room.state.queue[0]
        elif room.state.radio_queue:
            _next = room.state.radio_queue[0]
        if _next and _next.video_id:
            safe_create_task(prefetch_service.prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")
            
        await broadcast_service.broadcast_state(room.state, event.room_id)

    async def _on_track_progress(event: TrackProgressEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        position = event.position
        now = time.monotonic()
        room_id_key = event.room_id or "default"
        if now - last_progress_per_room.get(room_id_key, 0.0) < 0.33:
            return
        last_progress_per_room[room_id_key] = now
        await broadcast_service.broadcast_progress(position, room.state.status.name, event.room_id)

    async def _on_queue_updated(event: QueueUpdatedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await broadcast_service.broadcast_state(room.state, event.room_id)

    async def _on_lyrics_updated(event: LyricsUpdatedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await broadcast_service.broadcast_lyrics(room.state, event.room_id)

    async def _on_download_complete(event: DownloadCompleteEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await broadcast_service.broadcast_state(room.state, event.room_id)

    async def _on_log_message(event: LogMessageEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        msg = event.message
        room.state.error_msg = msg
        await broadcast_service.broadcast_log(msg, event.room_id)

    async def _on_pause_changed(event: TrackPauseChangedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await broadcast_service.broadcast_progress(room.state.position, room.state.status.name, event.room_id)

    def _setup_room_subscriptions(room):
        room.event_bus.subscribe(TrackStartedEvent, _on_track_started)
        room.event_bus.subscribe(TrackProgressEvent, _on_track_progress)
        room.event_bus.subscribe(QueueUpdatedEvent, _on_queue_updated)
        room.event_bus.subscribe(LyricsUpdatedEvent, _on_lyrics_updated)
        room.event_bus.subscribe(DownloadCompleteEvent, _on_download_complete)
        room.event_bus.subscribe(LogMessageEvent, _on_log_message)
        room.event_bus.subscribe(TrackPauseChangedEvent, _on_pause_changed)
        logger.info(f"Per-room EventBus subscriptions set up for room: {room.room_id}")

    room_manager.on_room_created(_setup_room_subscriptions)
    for room in room_manager.rooms.values():
        _setup_room_subscriptions(room)
