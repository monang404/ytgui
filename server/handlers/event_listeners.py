import time
import structlog
from core.events import (
    TrackStartedEvent, TrackProgressEvent, QueueUpdatedEvent, LyricsUpdatedEvent,
    DownloadCompleteEvent, LogMessageEvent, TrackPauseChangedEvent
)
from core.task_utils import safe_create_task

from server.services.stream_prefetch import StreamPrefetchService
from server.services.broadcast_service import BroadcastService

logger = structlog.get_logger(__name__)

def setup_event_listeners(
    playback_controller, 
    prefetch_service: StreamPrefetchService, 
    broadcast_service: BroadcastService
):
    last_progress = 0.0

    async def _on_track_started(event: TrackStartedEvent):
        state = playback_controller.state
        _next = None
        if state.queue:
            _next = state.queue[0]
        elif state.radio_queue:
            _next = state.radio_queue[0]
        if _next and _next.video_id:
            safe_create_task(prefetch_service.prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")
            
        await broadcast_service.broadcast_state(state)

    async def _on_track_progress(event: TrackProgressEvent):
        nonlocal last_progress
        position = event.position
        now = time.monotonic()
        if now - last_progress < 0.33:
            return
        last_progress = now
        await broadcast_service.broadcast_progress(position, playback_controller.state.status.name)

    async def _on_queue_updated(event: QueueUpdatedEvent):
        await broadcast_service.broadcast_state(playback_controller.state)

    async def _on_lyrics_updated(event: LyricsUpdatedEvent):
        await broadcast_service.broadcast_lyrics(playback_controller.state)

    async def _on_download_complete(event: DownloadCompleteEvent):
        await broadcast_service.broadcast_state(playback_controller.state)

    async def _on_log_message(event: LogMessageEvent):
        msg = event.message
        playback_controller.state.error_msg = msg
        await broadcast_service.broadcast_log(msg)

    async def _on_pause_changed(event: TrackPauseChangedEvent):
        await broadcast_service.broadcast_progress(playback_controller.state.position, playback_controller.state.status.name)

    bus = playback_controller.bus
    bus.subscribe(TrackStartedEvent, _on_track_started)
    bus.subscribe(TrackProgressEvent, _on_track_progress)
    bus.subscribe(QueueUpdatedEvent, _on_queue_updated)
    bus.subscribe(LyricsUpdatedEvent, _on_lyrics_updated)
    bus.subscribe(DownloadCompleteEvent, _on_download_complete)
    bus.subscribe(LogMessageEvent, _on_log_message)
    bus.subscribe(TrackPauseChangedEvent, _on_pause_changed)
    logger.info("EventBus subscriptions set up for Web Server")
