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

from config import CACHE_DIR, STREAM_URL_TTL_SEC
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
        "is_cached": bool(track.local_path),
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
        self.authenticated_connections: set[web.WebSocketResponse] = set()
        self.session_tokens: dict[str, float] = {}
        self.login_attempts: dict[str, list[float]] = {}
        self.command_history: dict[str, list[float]] = {}

    async def connect(self, ws: web.WebSocketResponse):
        self.active_connections.append(ws)
        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, ws: web.WebSocketResponse):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        if ws in self.authenticated_connections:
            self.authenticated_connections.remove(ws)
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
    app["http_session"] = aiohttp.ClientSession()

    async def on_cleanup(app):
        await app["http_session"].close()
    app.on_cleanup.append(on_cleanup)

    # --- Progress throttle ---
    last_progress = {"t": 0.0}

    # --- EventBus → WebSocket bridge ---
    async def _prefetch_stream_url(video_id: str):
        """Resolve dan cache stream URL di background, sebelum client request."""
        row = await db.get_track(video_id)
        if row and row.get("stream_url") and row.get("stream_url_ts"):
            if time.time() - row["stream_url_ts"] < STREAM_URL_TTL_SEC:
                return  # sudah ada, skip
        try:
            url = await ytdlp.get_stream_url(video_id)
            await db.update_stream_url_only(video_id, url)
        except Exception as e:
            logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")

    async def _on_track_started(track):
        if track and track.video_id:
            asyncio.create_task(_prefetch_stream_url(track.video_id))
            
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
        resp = web.FileResponse(STATIC_DIR / "index.html")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

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
                    await _handle_ws_message(data, ws, request.remote, state, ytdlp, manager)
                elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                    break
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            manager.disconnect(ws)

        return ws

    # --- Route: Health Check Endpoint ---
    async def handle_health(request):
        db = request.app["db"]
        db_status = "connected" if db.conn else "disconnected"
        
        controller = request.app["controller"]
        mpv_status = "connected" if controller.mpv and getattr(controller.mpv, "is_connected", False) else "disconnected"
        
        return web.json_response({
            "status": "ok" if db_status == "connected" and mpv_status == "connected" else "degraded",
            "db": db_status,
            "mpv": mpv_status
        })

    # --- Route: Stream Endpoint ---
    async def handle_stream(request):
        video_id = request.match_info.get("video_id")
        if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
            return web.HTTPBadRequest(text="Invalid video_id")

        cache_file = CACHE_DIR / f"{video_id}.mp3"
        if cache_file.exists():
            return web.FileResponse(
                cache_file,
                headers={"Access-Control-Allow-Origin": "*"}
            )

        db = request.app["db"]
        ytdlp = request.app["ytdlp"]
        stream_url = None

        row = await db.get_track(video_id)
        if row and row.get("stream_url") and row.get("stream_url_ts"):
            if time.time() - row["stream_url_ts"] < STREAM_URL_TTL_SEC:
                stream_url = row["stream_url"]

        http_session = request.app.get("http_session")
        if not http_session:
            return web.HTTPFound(stream_url or "")

        for attempt in range(2):
            if not stream_url:
                try:
                    stream_url = await ytdlp.get_stream_url(video_id)
                    await db.update_stream_url_only(video_id, stream_url)
                except Exception as e:
                    if attempt == 1:
                        return web.HTTPInternalServerError(text=f"Gagal mencari stream: {e}")
                    continue

            try:
                headers = {}
                if "Range" in request.headers:
                    headers["Range"] = request.headers["Range"]

                async with http_session.get(stream_url, headers=headers) as upstream:
                    if upstream.status in (403, 410) and attempt == 0:
                        logger.warning(f"YouTube stream URL expired ({upstream.status}), refetching...")
                        stream_url = None
                        continue

                    response = web.StreamResponse(
                        status=upstream.status,
                        headers={
                            "Content-Type": upstream.headers.get("Content-Type", "audio/mpeg"),
                            "Accept-Ranges": "bytes",
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "private, max-age=3600",
                        }
                    )
                    
                    if "Content-Range" in upstream.headers:
                        response.headers["Content-Range"] = upstream.headers["Content-Range"]
                    if "Content-Length" in upstream.headers:
                        try:
                            response.content_length = int(upstream.headers["Content-Length"])
                        except ValueError:
                            pass

                    await response.prepare(request)

                    async for chunk in upstream.content.iter_chunked(16384):
                        await response.write(chunk)

                    await response.write_eof()
                    return response

            except Exception as e:
                logger.warning(f"Proxy stream error untuk {video_id}: {e}")
                if attempt == 0:
                    stream_url = None
                    continue
                return web.HTTPInternalServerError(text="Proxy stream error")

    # --- Register routes ---
    app.router.add_get("/", handle_index)
    app.router.add_get("/admin", handle_index)
    app.router.add_get("/ws", handle_websocket)
    app.router.add_get("/api/stream/{video_id}", handle_stream)
    app.router.add_get("/health", handle_health)
    app.router.add_static("/static", STATIC_DIR, name="static")

    return app


async def _handle_ws_message(msg: dict, ws: web.WebSocketResponse, client_ip: str, state: AppState, ytdlp, manager: ConnectionManager):
    """Process incoming WebSocket commands from browser."""
    msg_type = msg.get("type")
    action = msg.get("action", "")
    data = msg.get("data", {})

    if msg_type != "cmd":
        return

    # Check authentication
    from config import ADMIN_USERNAME, ADMIN_PASSWORD
    import secrets
    import time
    
    is_authenticated = ws in manager.authenticated_connections

    try:
        now = time.time()
        
        if action == "auth":
            token = data.get("token")
            if token and token in manager.session_tokens:
                if now < manager.session_tokens[token]:
                    manager.authenticated_connections.add(ws)
                    await ws.send_str(json.dumps({
                        "type": "auth_status",
                        "data": {"success": True, "token": token}
                    }))
                    return
                else:
                    del manager.session_tokens[token]

            attempts = manager.login_attempts.get(client_ip, [])
            attempts = [t for t in attempts if now - t < 300]
            if len(attempts) >= 5:
                await ws.send_str(json.dumps({
                    "type": "auth_status",
                    "data": {"success": False, "message": "Terlalu banyak percobaan login. Coba lagi dalam 5 menit."}
                }))
                return

            username = data.get("username", "")
            password = data.get("password", "")
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                new_token = secrets.token_hex(16)
                manager.session_tokens[new_token] = now + 86400  # 24 hours expiry
                manager.authenticated_connections.add(ws)
                if client_ip in manager.login_attempts:
                    del manager.login_attempts[client_ip]
                await ws.send_str(json.dumps({
                    "type": "auth_status",
                    "data": {"success": True, "token": new_token}
                }))
            else:
                attempts.append(now)
                manager.login_attempts[client_ip] = attempts
                await ws.send_str(json.dumps({
                    "type": "auth_status",
                    "data": {"success": False, "message": "Username atau Password salah!"}
                }))
            return

        # If not authenticated, reject all other commands
        # Pengecualian: izinkan command "next" dari client HANYA jika sesuai dengan track saat ini (trigger auto-skip browser)
        if not is_authenticated:
            is_valid_auto_skip = (
                action == "next" 
                and isinstance(data, dict) 
                and data.get("video_id") == getattr(state.current_track, "video_id", None)
            )
            if not is_valid_auto_skip:
                await ws.send_str(json.dumps({
                    "type": "error",
                    "data": "Akses ditolak. Silakan login sebagai Admin.",
                }))
                return
            
        # Command Rate Limiting
        cmd_history = manager.command_history.get(client_ip, [])
        cmd_history = [t for t in cmd_history if now - t < 60]
        if len(cmd_history) >= 30:
            await ws.send_str(json.dumps({
                "type": "error",
                "data": "Terlalu banyak permintaan. Mohon tunggu sesaat."
            }))
            return
        cmd_history.append(now)
        manager.command_history[client_ip] = cmd_history
        
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
