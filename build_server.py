import os
os.makedirs("server/handlers", exist_ok=True)

with open("server/__init__.py", "w") as f:
    f.write("")

with open("server/handlers/__init__.py", "w") as f:
    f.write("")

def write_f(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

write_f("server/serializers.py", """\
from typing import Optional
from core.state import AppState, TrackInfo, AudioOutput

def track_to_dict(track: Optional[TrackInfo]) -> Optional[dict]:
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

def state_to_dict(state: AppState) -> dict:
    return {
        "status": state.status.name,
        "playback_mode": state.playback_mode.name,
        "current_track": track_to_dict(state.current_track),
        "position": state.position,
        "duration": state.duration,
        "volume": state.volume,
        "audio_output": getattr(state, "audio_output", AudioOutput.DEVICE).value,
        "sponsorblock_active": state.sponsorblock_active,
        "queue": [track_to_dict(t) for t in state.queue],
        "radio_queue": [track_to_dict(t) for t in state.radio_queue],
        "history_count": len(state.history),
        "lyrics_lines": list(state.lyrics_lines),
        "lyrics_index": state.lyrics_index,
        "lyrics_offset": state.lyrics_offset,
        "active_tab": state.active_tab,
        "error_msg": state.error_msg,
        "is_online": state.is_online,
        "download_progress": state.download_progress,
    }

def dict_to_track(data: dict) -> Optional[TrackInfo]:
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
""")

write_f("server/middleware.py", """\
import time
from core.observability import ACTIVE_WEBSOCKETS

def check_rate_limit(manager, client_ip: str, now: float) -> bool:
    cmd_history = manager.command_history.get(client_ip, [])
    cmd_history = [t for t in cmd_history if now - t < 60]
    if not cmd_history:
        manager.command_history.pop(client_ip, None)
    else:
        manager.command_history[client_ip] = cmd_history
    if len(cmd_history) >= 30:
        return False
    cmd_history.append(now)
    manager.command_history[client_ip] = cmd_history
    return True
""")

write_f("server/handlers/auth.py", """\
import json
import time
import secrets
from config import ADMIN_USERNAME, ADMIN_PASSWORD
from core.security import verify_password

async def handle_auth(ws, data, manager, client_ip, db, now):
    token = data.get("token")
    if token and db:
        if await db.verify_session(token):
            manager.authenticated_connections.add(ws)
            await ws.send_str(json.dumps({
                "type": "auth_status",
                "data": {"success": True, "token": token}
            }))
            return

    attempts = manager.login_attempts.get(client_ip, [])
    attempts = [t for t in attempts if now - t < 300]
    if not attempts:
        manager.login_attempts.pop(client_ip, None)
    else:
        manager.login_attempts[client_ip] = attempts
    if len(attempts) >= 5:
        await ws.send_str(json.dumps({
            "type": "auth_status",
            "data": {"success": False, "message": "Terlalu banyak percobaan login. Coba lagi dalam 5 menit."}
        }))
        return

    username = data.get("username", "")
    password = data.get("password", "")
    if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD):
        new_token = secrets.token_hex(16)
        if db:
            await db.create_session(new_token, int(now) + 86400)
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

def require_auth(manager, ws) -> bool:
    return ws in manager.authenticated_connections
""")

write_f("server/handlers/http.py", """\
import re
import time
import structlog
from pathlib import Path
from aiohttp import web
from config import CACHE_DIR, STREAM_URL_TTL_SEC
from core.observability import get_metrics_content

logger = structlog.get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent.parent / "web" / "static"

async def serve_index(request):
    resp = web.FileResponse(STATIC_DIR / "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp

async def health_check(request):
    db = request.app["db"]
    db_status = "connected" if db.conn else "disconnected"
    
    rm = request.app["room_manager"]
    try:
        rooms = getattr(rm, "_rooms", {})
        if rooms:
            first_room = next(iter(rooms.values()))
            mpv_ok = getattr(getattr(first_room, "mpv", None), "is_connected", False)
        else:
            mpv_ok = True
    except Exception:
        mpv_ok = False
    mpv_status = "connected" if mpv_ok else "not_started"
    
    return web.json_response({
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "mpv": mpv_status
    })

async def serve_stream(request):
    video_id = request.match_info.get("video_id")
    if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
        return web.HTTPBadRequest(text="Invalid video_id")

    cache_file = CACHE_DIR / f"{video_id}.mp3"
    try:
        if not cache_file.resolve().is_relative_to(CACHE_DIR.resolve()):
            return web.HTTPForbidden(text="Akses ditolak")
    except Exception:
        return web.HTTPBadRequest(text="Path tidak valid")

    if cache_file.exists():
        return web.FileResponse(
            cache_file,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    db = request.app["db"]
    ytdlp = request.app["ytdlp"]
    stream_url = None

    row = await db.get_track(video_id)
    if row and row.stream_url and row.stream_url_ts:
        if time.time() - row.stream_url_ts < STREAM_URL_TTL_SEC:
            stream_url = row.stream_url

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
            from urllib.parse import urlparse
            parsed_url = urlparse(stream_url)
            if parsed_url.scheme != "https":
                raise ValueError("Skema URL harus HTTPS")
            domain = parsed_url.netloc.lower()
            if not (domain.endswith(".googlevideo.com") or domain.endswith(".youtube.com")):
                raise ValueError(f"Domain tidak sah: {domain}")
        except Exception as e:
            logger.error(f"SSRF terdeteksi atau URL stream tidak valid: {stream_url} - {e}")
            return web.HTTPForbidden(text="URL stream tidak valid")

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

async def serve_metrics(request):
    import os as _os
    client_ip = request.remote
    _localhost_ips = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
    metrics_token = _os.environ.get("YTGUI_METRICS_TOKEN")
    is_local = client_ip in _localhost_ips
    has_valid_token = (
        metrics_token
        and request.headers.get("X-Metrics-Token") == metrics_token
    )
    if not is_local and not has_valid_token:
        return web.HTTPForbidden(text="Akses ditolak: metrics hanya untuk localhost atau gunakan X-Metrics-Token")

    content, content_type = get_metrics_content()
    ct = content_type.split(";")[0].strip()
    return web.Response(body=content, content_type=ct)
""")

write_f("server/handlers/websocket.py", """\
import json
import time
import structlog
import re
from aiohttp import web
import aiohttp
from core.observability import ACTIVE_WEBSOCKETS
from core.command_bus import (
    command_bus, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_VOLUME_SET,
    CMD_DOWNLOAD, CMD_SET_MODE, CMD_SET_OUTPUT, CMD_SET_SPONSORBLOCK, CMD_QUEUE_SELECT,
    CMD_QUEUE_ADD, CMD_QUEUE_REMOVE, CMD_QUEUE_REORDER, CMD_RADIO_RANDOMIZE, CMD_LYRICS_OFFSET
)
from core.state import PlaybackMode, AudioOutput
from server.serializers import state_to_dict, dict_to_track, track_to_dict
from server.middleware import check_rate_limit
from server.handlers.auth import handle_auth, require_auth
from services.discover_service import DiscoverService

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.authenticated_connections = set()
        self.session_tokens = {}
        self.login_attempts = {}
        self.command_history = {}

    async def connect(self, ws, room_id):
        self.active_connections.append((ws, room_id))
        ACTIVE_WEBSOCKETS.labels(room_id=room_id).inc()
        logger.info(f"WebSocket connected to room {room_id}. Total clients: {len(self.active_connections)}")

    def disconnect(self, ws):
        disconnected_rooms = [r for w, r in self.active_connections if w == ws]
        for r in disconnected_rooms:
            ACTIVE_WEBSOCKETS.labels(room_id=r).dec()
            
        self.active_connections = [(w, r) for w, r in self.active_connections if w != ws]
        if ws in self.authenticated_connections:
            self.authenticated_connections.remove(ws)
        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict, room_id: str = None):
        data = json.dumps(message, ensure_ascii=False)
        dead = []
        for ws, r_id in self.active_connections:
            if room_id is None or r_id == room_id:
                try:
                    await ws.send_str(data)
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

_ROOM_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
MAX_ROOMS = 10

async def ws_handler(request):
    room_id = request.query.get("room", "default")
    if not _ROOM_ID_RE.match(room_id):
        return web.HTTPBadRequest(text="Invalid room_id: hanya huruf, angka, '-', '_', maksimum 64 karakter")
        
    room_manager = request.app["room_manager"]
    manager = request.app["manager"]
    db = request.app["db"]
    ytdlp = request.app["ytdlp"]
    
    if room_id not in room_manager.rooms and len(room_manager.rooms) >= MAX_ROOMS:
        return web.HTTPTooManyRequests(text="Batas maksimum room tercapai")

    room = await room_manager.get_or_create_room(room_id)
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await manager.connect(ws, room_id)

    try:
        await ws.send_str(json.dumps({
            "type": "state",
            "data": state_to_dict(room.state),
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
                await handle_ws_message(data, ws, request.remote, room.state, ytdlp, manager, db, room_id)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(ws)

    return ws

async def handle_ws_message(msg: dict, ws, client_ip: str, state, ytdlp, manager, db, room_id: str):
    msg_type = msg.get("type")
    action = msg.get("action", "")
    data = msg.get("data", {})

    if msg_type != "cmd":
        return

    now = time.time()
    if action == "auth":
        await handle_auth(ws, data, manager, client_ip, db, now)
        return

    if not require_auth(manager, ws):
        await ws.send_str(json.dumps({
            "type": "error",
            "data": "Akses ditolak. Silakan login sebagai Admin.",
        }))
        return

    if not check_rate_limit(manager, client_ip, now):
        await ws.send_str(json.dumps({
            "type": "error",
            "data": "Terlalu banyak permintaan. Mohon tunggu sesaat."
        }))
        return

    try:
        if action == "search":
            query = data.get("query", "").strip()
            if query:
                results = await ytdlp.search(query, max_results=10)
                await ws.send_str(json.dumps({
                    "type": "search_results",
                    "data": [track_to_dict(t) for t in results],
                }, ensure_ascii=False))

        elif action == "discover":
            ds = DiscoverService(db)
            recent = await ds.get_recent(15)
            favorites = await ds.get_favorites(15)
            cached = await ds.get_cached(15)
            await ws.send_str(json.dumps({
                "type": "discover_data",
                "data": {
                    "recent": [track_to_dict(t) for t in recent],
                    "favorites": [track_to_dict(t) for t in favorites],
                    "cached_tracks": [track_to_dict(t) for t in cached]
                }
            }, ensure_ascii=False))

        elif action == "play_track":
            track = dict_to_track(data)
            if track:
                await command_bus.execute(CMD_PLAY_TRACK, room_id, track)

        elif action == "toggle_pause":
            await command_bus.execute(CMD_TOGGLE_PAUSE, room_id)

        elif action == "next":
            await command_bus.execute(CMD_NEXT, room_id, data)

        elif action == "prev":
            await command_bus.execute(CMD_PREV, room_id)

        elif action == "stop":
            await command_bus.execute(CMD_STOP, room_id)

        elif action == "seek":
            position = data.get("position", 0)
            await command_bus.execute(CMD_SEEK, room_id, float(position))

        elif action == "volume_up":
            await command_bus.execute(CMD_VOLUME_UP, room_id)

        elif action == "volume_down":
            await command_bus.execute(CMD_VOLUME_DOWN, room_id)

        elif action == "volume_set":
            vol = data.get("volume", 80)
            await command_bus.execute(CMD_VOLUME_SET, room_id, {"volume": int(vol)})

        elif action == "download":
            await command_bus.execute(CMD_DOWNLOAD, room_id)

        elif action == "set_mode":
            mode_str = data.get("mode", "queue").upper()
            mode = PlaybackMode.RADIO if mode_str == "RADIO" else PlaybackMode.QUEUE
            await command_bus.execute(CMD_SET_MODE, room_id, mode)

        elif action == "queue_select":
            index = data.get("index", 0)
            await command_bus.execute(CMD_QUEUE_SELECT, room_id, int(index))

        elif action == "queue_remove":
            index = data.get("index", 0)
            await command_bus.execute(CMD_QUEUE_REMOVE, room_id, int(index))

        elif action == "queue_add":
            track = dict_to_track(data)
            if track:
                await command_bus.execute(CMD_QUEUE_ADD, room_id, track)

        elif action == "queue_reorder":
            from_idx = int(data.get("from_index", 0))
            to_idx = int(data.get("to_index", 0))
            await command_bus.execute(CMD_QUEUE_REORDER, room_id, {"from_index": from_idx, "to_index": to_idx})

        elif action == "radio_randomize":
            seed_artist = data.get("seed_artist")
            await command_bus.execute(CMD_RADIO_RANDOMIZE, room_id, {"seed_artist": seed_artist})

        elif action == "set_output":
            output_str = data.get("output", "device")
            output_val = AudioOutput.BROWSER if output_str == "browser" else AudioOutput.DEVICE
            await command_bus.execute(CMD_SET_OUTPUT, room_id, output_val)

        elif action == "set_sponsorblock":
            enabled = data.get("enabled", True)
            await command_bus.execute(CMD_SET_SPONSORBLOCK, room_id, bool(enabled))

        elif action == "lyrics_offset":
            offset = data.get("offset", 0.0)
            await command_bus.execute(CMD_LYRICS_OFFSET, room_id, {"offset": float(offset)})

    except Exception as e:
        logger.error(f"Error handling WS command '{action}': {e}", exc_info=True)
        try:
            await ws.send_str(json.dumps({
                "type": "error",
                "data": str(e),
            }))
        except Exception:
            pass
""")

write_f("server/app.py", """\
import asyncio
import time
import structlog
from pathlib import Path
from aiohttp import web
import aiohttp

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
    app["http_session"] = aiohttp.ClientSession()

    async def on_cleanup(app):
        await app["http_session"].close()
    app.on_cleanup.append(on_cleanup)

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
        if track and track.video_id:
            safe_create_task(_prefetch_stream_url(track.video_id), name=f"prefetch_{track.video_id}")
            
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
""")

print("Server files created!")
