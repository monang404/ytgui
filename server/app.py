import asyncio
import time
import structlog
from pathlib import Path
from aiohttp import web

from core.events import (
    TrackStartedEvent, TrackProgressEvent, QueueUpdatedEvent, LyricsUpdatedEvent,
    DownloadCompleteEvent, LogMessageEvent, TrackPauseChangedEvent
)
from core.task_utils import safe_create_task
from server.serializers import state_to_dict
from server.handlers.http import serve_index, health_check, serve_stream, serve_metrics
from server.handlers.websocket import ws_handler, ConnectionManager
from config import CACHE_DIR, STREAM_URL_TTL_SEC
from core.ports import MediaExtractorPort, DatabasePort
from core.room_manager import RoomManager

logger = structlog.get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"

def create_app(room_manager: RoomManager, ytdlp: MediaExtractorPort, db: DatabasePort) -> web.Application:
    app = web.Application()
    manager = ConnectionManager()

    app["room_manager"] = room_manager
    app["ytdlp"] = ytdlp
    app["db"] = db
    app["manager"] = manager
    # Bug #9 fix: ClientSession sudah dibuat di main.py dan di-pass ke plugins.
    # Tidak perlu buat session baru di sini agar tidak ada resource leak.

    last_progress_per_room: dict[str, float] = {}

    async def _prefetch_stream_url(video_id: str):
        row = await db.get_track(video_id)
        if row and row.stream_url and row.stream_url_ts:
            if time.time() - row.stream_url_ts < STREAM_URL_TTL_SEC:
                return
        try:
            url = await ytdlp.get_stream_url(video_id)
            await db.update_stream_url_only(video_id, url)
        except Exception as e:
            logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")

    async def _on_track_started(event: TrackStartedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        track = event.track
        # B-03: prefetch URL untuk track BERIKUTNYA di queue atau radio_queue
        # (current track sudah di-resolve oleh CacheResolver sesaat sebelumnya)
        _next = None
        if room.state.queue:
            _next = room.state.queue[0]
        elif room.state.radio_queue:
            _next = room.state.radio_queue[0]
        if _next and _next.video_id:
            safe_create_task(_prefetch_stream_url(_next.video_id), name=f"prefetch_next_{_next.video_id}")
            
        await manager.broadcast({
            "type": "state",
            "data": state_to_dict(room.state),
        }, room_id=event.room_id)

    async def _on_track_progress(event: TrackProgressEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        position = event.position
        now = time.monotonic()
        room_id_key = event.room_id or "default"
        if now - last_progress_per_room.get(room_id_key, 0.0) < 0.33:
            return
        last_progress_per_room[room_id_key] = now
        await manager.broadcast({
            "type": "progress",
            "data": {
                "position": position,
                "status": room.state.status.name,
                "server_ts": time.time(),
            },
        }, room_id=event.room_id)

    async def _on_queue_updated(event: QueueUpdatedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await manager.broadcast({
            "type": "state",
            "data": state_to_dict(room.state),
        }, room_id=event.room_id)

    async def _on_lyrics_updated(event: LyricsUpdatedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await manager.broadcast({
            "type": "lyrics",
            "data": {
                "lyrics_lines": list(room.state.lyrics_lines),
                "lyrics_timestamps": list(room.state.lyrics_timestamps),
                "lyrics_index": room.state.lyrics_index,
                "lyrics_offset": room.state.lyrics_offset,
                "lyrics_loading": getattr(room.state, "lyrics_loading", False),
            },
        }, room_id=event.room_id)

    async def _on_download_complete(event: DownloadCompleteEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await manager.broadcast({
            "type": "state",
            "data": state_to_dict(room.state),
        }, room_id=event.room_id)

    async def _on_log_message(event: LogMessageEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        msg = event.message
        room.state.error_msg = msg
        await manager.broadcast({
            "type": "log",
            "data": msg,
        }, room_id=event.room_id)

    async def _on_pause_changed(event: TrackPauseChangedEvent):
        room = room_manager.rooms.get(event.room_id)
        if not room: return
        await manager.broadcast({
            "type": "progress",
            "data": {
                "position": room.state.position,
                "status": room.state.status.name,
                "server_ts": time.time(),
            },
        }, room_id=event.room_id)

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

    app.router.add_get("/", serve_index)
    app.router.add_get("/admin", serve_index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/api/stream/{video_id}", serve_stream)
    app.router.add_get("/health", health_check)
    app.router.add_get("/metrics", serve_metrics)
    app.router.add_static("/static", STATIC_DIR, name="static")

    return app

async def run_server(app: web.Application, host: str = "0.0.0.0", port: int = 8765):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Web server running on http://{host}:{port}")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()
