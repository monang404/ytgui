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
from engine.playback.controller import PlaybackController

logger = structlog.get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"

def create_app(playback_controller: PlaybackController, ytdlp: MediaExtractorPort, db: DatabasePort) -> web.Application:
    app = web.Application()
    manager = ConnectionManager()

    app["playback_controller"] = playback_controller
    app["state"] = playback_controller.state
    app["ytdlp"] = ytdlp
    app["db"] = db
    app["manager"] = manager
    # Bug #9 fix: ClientSession sudah dibuat di main.py dan di-pass ke plugins.
    # Tidak perlu buat session baru di sini agar tidak ada resource leak.

    from server.services.stream_prefetch import StreamPrefetchService
    from server.services.broadcast_service import BroadcastService
    from server.handlers.event_listeners import setup_event_listeners

    prefetch_service = StreamPrefetchService(db, ytdlp)
    broadcast_service = BroadcastService(manager)
    setup_event_listeners(playback_controller, prefetch_service, broadcast_service)

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
