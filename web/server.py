"""
Purpose: aiohttp web server + WebSocket bridge between Engine Layer and Browser UI.
Uses aiohttp.web which is already installed — no extra dependencies needed for Termux.

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
import re
from pathlib import Path
from typing import Optional

import aiohttp
from aiohttp import web

from config import CACHE_DIR
from core.event_bus import (
    bus, TRACK_STARTED, TRACK_PROGRESS, QUEUE_UPDATED, LYRICS_UPDATED,
    DOWNLOAD_COMPLETE, LOG_MESSAGE, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_VOLUME_UP, CMD_VOLUME_DOWN,
    CMD_DOWNLOAD, CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE,
    CMD_QUEUE_ADD, CMD_RADIO_RANDOMIZE, CMD_SET_OUTPUT
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
        "audio_output": getattr(state, "audio_output", "device"),
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


class ConnectionManager:
    """Manages WebSocket connections to all browser clients."""

    def __init__(self):
        self.active_connections: list[web.WebSocketResponse] = []

    async def connect(self, ws: web.WebSocketResponse):
        self.active_connections.append(ws)
        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, ws: web.WebSocketResponse):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        data = json.dumps(message, ensure_ascii=False)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


def create_app(state: AppState, ytdlp, db, controller) -> web.Application:
    app = web.Application()
    manager = ConnectionManager()

    # Store references
    app["app_state"] = state
    app["ytdlp"] = ytdlp
    app["db"] = db
    app["controller"] = controller
    app["manager"] = manager

    # --- Progress throttle ---
    last_progress = {"t": 0.0}

    # --- EventBus → WebSocket bridge ---
    async def _on_track_started(track):
        await manager.broadcast({
            "type": "state",
            "data": _state_to_dict(state),
        })

    async def _on_track_progress(position: float):
        now = time.monotonic()
        if now - last_progress["t"] < 0.33:
            return  # Throttle: max ~3 updates/sec
        last_progress["t"] = now
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

    # --- Route: Serve index.html ---
    async def handle_index(request):
        return web.FileResponse(STATIC_DIR / "index.html")

    # --- Route: WebSocket ---
    async def handle_websocket(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await manager.connect(ws)

        # Send initial state
        try:
            await ws.send_str(json.dumps({
                "type": "state",
                "data": _state_to_dict(state),
            }, ensure_ascii=False))
        except Exception:
            manager.disconnect(ws)
            return ws

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    await _handle_ws_message(data, ws, state, ytdlp)
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            manager.disconnect(ws)

        return ws

    # --- Route: Stream Endpoint ---
    async def handle_stream(request):
        video_id = request.match_info.get("video_id")
        if not video_id:
            return web.HTTPBadRequest(text="Missing video_id")
            
        safe_id = "".join(c for c in video_id if c.isalnum() or c in "-_")
        cache_file = CACHE_DIR / f"{safe_id}.mp3"
        
        # Jika file MP3 ada di cache, serve secara langsung
        if cache_file.exists():
            return web.FileResponse(cache_file)
            
        # Jika tidak ada di cache, cari streaming url dari DB / yt-dlp
        ytdlp = request.app["ytdlp"]
        db = request.app["db"]
        
        row = await db.get_track(video_id)
        if row and row.get("stream_url") and row.get("stream_url_ts"):
            ts = row.get("stream_url_ts")
            if time.time() - ts < 21600:
                return web.HTTPFound(row["stream_url"])
                
        try:
            url = await ytdlp.get_stream_url(video_id)
            from core.state import TrackInfo
            track = TrackInfo(video_id=video_id, title="Temp", artist="Temp", duration=0)
            await db.upsert_track(track, stream_url=url)
            return web.HTTPFound(url)
        except Exception as e:
            return web.HTTPInternalServerError(text=f"Gagal mencari stream: {e}")

    # --- Register routes ---
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_get("/api/stream/{video_id}", handle_stream)
    app.router.add_static("/static", STATIC_DIR, name="static")

    return app


async def _handle_ws_message(msg: dict, ws: web.WebSocketResponse, state: AppState, ytdlp):
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
                await ws.send_str(json.dumps({
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

        elif action == "set_output":
            output = data.get("output", "device")
            await bus.publish(CMD_SET_OUTPUT, output)

    except Exception as e:
        logger.error(f"Error handling WS command '{action}': {e}", exc_info=True)
        try:
            await ws.send_str(json.dumps({
                "type": "error",
                "data": str(e),
            }))
        except Exception:
            pass


async def run_server(app: web.Application, host: str = "0.0.0.0", port: int = 8765):
    """Run the aiohttp web server inside the existing asyncio event loop."""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Web server running on http://{host}:{port}")

    # Keep the server running until cancelled
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()
