"""
Purpose: FastAPI + WebSocket server that bridges the Engine Layer with the Browser UI.
Subscribes to: TRACK_STARTED, TRACK_PROGRESS, QUEUE_UPDATED, LYRICS_UPDATED,
               DOWNLOAD_COMPLETE, LOG_MESSAGE, "track.pause.changed"
Publishes: CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP,
           CMD_SEEK, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_SET_MODE,
           CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE, CMD_QUEUE_ADD, CMD_RADIO_RANDOMIZE
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.event_bus import (
    bus, TRACK_STARTED, TRACK_PROGRESS, QUEUE_UPDATED, LYRICS_UPDATED,
    DOWNLOAD_COMPLETE, LOG_MESSAGE, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_VOLUME_UP, CMD_VOLUME_DOWN,
    CMD_DOWNLOAD, CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE,
    CMD_QUEUE_ADD, CMD_RADIO_RANDOMIZE
)
from core.state import AppState, PlayerStatus, PlaybackMode, TrackInfo

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _track_to_dict(track: Optional[TrackInfo]) -> Optional[dict]:
    if not track:
        return None
    return {
        "video_id": track.video_id,
        "title": track.title,
        "artist": track.artist,
        "duration": track.duration,
        "thumbnail": track.thumbnail,
        "local_path": track.local_path,
        "stream_url": track.stream_url,
        "view_count": track.view_count,
    }


def _state_to_dict(state: AppState) -> dict:
    return {
        "status": state.status.name,
        "playback_mode": state.playback_mode.name,
        "current_track": _track_to_dict(state.current_track),
        "position": state.position,
        "volume": state.volume,
        "sponsorblock_active": state.sponsorblock_active,
        "queue": [_track_to_dict(t) for t in state.queue],
        "radio_queue": [_track_to_dict(t) for t in state.radio_queue],
        "history_count": len(state.history),
        "lyrics_lines": list(state.lyrics_lines),
        "lyrics_index": state.lyrics_index,
        "lyrics_offset": state.lyrics_offset,
        "active_tab": state.active_tab,
        "error_msg": state.error_msg,
        "is_online": state.is_online,
        "download_progress": state.download_progress,
    }


class ConnectionManager:
    """Manages WebSocket connections to all browser clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        data = json.dumps(message, ensure_ascii=False)
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.disconnect(conn)


def create_app(state: AppState, ytdlp, db, controller) -> FastAPI:
    app = FastAPI(title="YTGUI Web", docs_url=None, redoc_url=None)
    manager = ConnectionManager()

    # Store references for route handlers
    app.state.app_state = state
    app.state.ytdlp = ytdlp
    app.state.db = db
    app.state.controller = controller
    app.state.manager = manager

    # --- Progress throttle ---
    _last_progress_broadcast = {"t": 0.0}

    # --- EventBus → WebSocket bridge ---
    async def _on_track_started(track):
        await manager.broadcast({
            "type": "state",
            "data": _state_to_dict(state),
        })

    async def _on_track_progress(position: float):
        now = time.monotonic()
        if now - _last_progress_broadcast["t"] < 0.33:
            return  # Throttle: max ~3 updates/sec
        _last_progress_broadcast["t"] = now
        state.position = position
        await manager.broadcast({
            "type": "progress",
            "data": {
                "position": position,
                "status": state.status.name,
            },
        })

    async def _on_queue_updated(_data=None):
        await manager.broadcast({
            "type": "state",
            "data": _state_to_dict(state),
        })

    async def _on_lyrics_updated(_data=None):
        await manager.broadcast({
            "type": "lyrics",
            "data": {
                "lyrics_lines": list(state.lyrics_lines),
                "lyrics_index": state.lyrics_index,
                "lyrics_offset": state.lyrics_offset,
                "lyrics_loading": getattr(state, "lyrics_loading", False),
            },
        })

    async def _on_download_complete(track):
        await manager.broadcast({
            "type": "state",
            "data": _state_to_dict(state),
        })

    async def _on_log_message(msg: str):
        state.error_msg = msg
        await manager.broadcast({
            "type": "log",
            "data": msg,
        })

    async def _on_pause_changed(paused: bool):
        await manager.broadcast({
            "type": "progress",
            "data": {
                "position": state.position,
                "status": state.status.name,
            },
        })

    # Subscribe to EventBus
    bus.subscribe(TRACK_STARTED, _on_track_started)
    bus.subscribe(TRACK_PROGRESS, _on_track_progress)
    bus.subscribe(QUEUE_UPDATED, _on_queue_updated)
    bus.subscribe(LYRICS_UPDATED, _on_lyrics_updated)
    bus.subscribe(DOWNLOAD_COMPLETE, _on_download_complete)
    bus.subscribe(LOG_MESSAGE, _on_log_message)
    bus.subscribe("track.pause.changed", _on_pause_changed)

    # --- Routes ---

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    # Mount static files AFTER the root route
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # --- WebSocket endpoint ---

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)

        # Send initial state on connect
        try:
            await websocket.send_text(json.dumps({
                "type": "state",
                "data": _state_to_dict(state),
            }, ensure_ascii=False))
        except Exception:
            manager.disconnect(websocket)
            return

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                await _handle_ws_message(msg, websocket, state, ytdlp, db)

        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    return app


async def _handle_ws_message(msg: dict, ws: WebSocket, state: AppState, ytdlp, db):
    """Process incoming WebSocket commands from browser."""
    msg_type = msg.get("type")
    action = msg.get("action", "")
    data = msg.get("data", {})

    if msg_type != "cmd":
        return

    try:
        if action == "search":
            query = data.get("query", "").strip()
            if query:
                results = await ytdlp.search(query, max_results=10)
                await ws.send_text(json.dumps({
                    "type": "search_results",
                    "data": [_track_to_dict(t) for t in results],
                }, ensure_ascii=False))

        elif action == "play_track":
            track = _dict_to_track(data)
            if track:
                await bus.publish(CMD_PLAY_TRACK, track)

        elif action == "toggle_pause":
            await bus.publish(CMD_TOGGLE_PAUSE)

        elif action == "next":
            await bus.publish(CMD_NEXT)

        elif action == "prev":
            await bus.publish(CMD_PREV)

        elif action == "stop":
            await bus.publish(CMD_STOP)

        elif action == "seek":
            position = data.get("position", 0)
            await bus.publish(CMD_SEEK, float(position))

        elif action == "volume_up":
            await bus.publish(CMD_VOLUME_UP)

        elif action == "volume_down":
            await bus.publish(CMD_VOLUME_DOWN)

        elif action == "download":
            await bus.publish(CMD_DOWNLOAD)

        elif action == "set_mode":
            mode_str = data.get("mode", "queue").upper()
            mode = PlaybackMode.RADIO if mode_str == "RADIO" else PlaybackMode.QUEUE
            await bus.publish(CMD_SET_MODE, mode)

        elif action == "queue_select":
            index = data.get("index", 0)
            await bus.publish(CMD_QUEUE_SELECT, int(index))

        elif action == "queue_remove":
            index = data.get("index", 0)
            await bus.publish(CMD_QUEUE_REMOVE, int(index))

        elif action == "queue_add":
            track = _dict_to_track(data)
            if track:
                await bus.publish(CMD_QUEUE_ADD, track)

        elif action == "radio_randomize":
            await bus.publish(CMD_RADIO_RANDOMIZE)

    except Exception as e:
        logger.error(f"Error handling WS command '{action}': {e}", exc_info=True)
        await ws.send_text(json.dumps({
            "type": "error",
            "data": str(e),
        }))


def _dict_to_track(data: dict) -> Optional[TrackInfo]:
    """Convert a dict from the browser into a TrackInfo object."""
    video_id = data.get("video_id")
    if not video_id:
        return None
    return TrackInfo(
        video_id=video_id,
        title=data.get("title", "Unknown"),
        artist=data.get("artist", "Unknown"),
        duration=int(data.get("duration", 0)),
        thumbnail=data.get("thumbnail"),
        local_path=data.get("local_path"),
        stream_url=data.get("stream_url"),
        view_count=data.get("view_count"),
    )


async def run_server(app: FastAPI, host: str = "0.0.0.0", port: int = 8765):
    """Run the uvicorn server inside the existing asyncio event loop."""
    import uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()
