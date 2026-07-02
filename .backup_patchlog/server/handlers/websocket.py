import json
import time
import structlog
import re
from aiohttp import web
import aiohttp
from config import TRUSTED_PROXY
from core.observability import ACTIVE_WEBSOCKETS
from core.command_bus import (
    command_bus, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_VOLUME_SET,
    CMD_DOWNLOAD, CMD_SET_MODE, CMD_SET_OUTPUT, CMD_SET_SPONSORBLOCK, CMD_QUEUE_SELECT,
    CMD_QUEUE_ADD, CMD_QUEUE_REPLACE, CMD_QUEUE_REMOVE, CMD_QUEUE_REORDER, CMD_RADIO_RANDOMIZE, CMD_LYRICS_OFFSET
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
        import asyncio
        self.rl_lock = asyncio.Lock()

    async def connect(self, ws):
        self.active_connections.append(ws)
        ACTIVE_WEBSOCKETS.inc()
        logger.info(f"WebSocket connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, ws):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
            ACTIVE_WEBSOCKETS.dec()
        if ws in self.authenticated_connections:
            self.authenticated_connections.remove(ws)
        logger.info(f"WebSocket disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        data = json.dumps(message, ensure_ascii=False)
        import asyncio
        async def send(ws):
            try:
                await ws.send_str(data)
                return None
            except Exception as e:
                return e

        results = await asyncio.gather(*(send(ws) for ws in self.active_connections), return_exceptions=True)
        
        dead = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                dead.append(self.active_connections[i])
                
        for ws in dead:
            self.disconnect(ws)

async def ws_handler(request):
    playback_controller = request.app["playback_controller"]
    state = request.app["state"]
    manager = request.app["manager"]
    db = request.app["db"]
    ytdlp = request.app["ytdlp"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await manager.connect(ws)

    try:
        await ws.send_str(json.dumps({
            "type": "state",
            "data": state_to_dict(state),
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
                client_ip = request.remote
                if TRUSTED_PROXY and "X-Forwarded-For" in request.headers:
                    client_ip = request.headers.get("X-Forwarded-For").split(",")[0].strip()
                await handle_ws_message(data, ws, client_ip, state, ytdlp, manager, db)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(ws)

    return ws


async def _build_discover_payload(db):
    ds = DiscoverService(db)
    recent = await ds.get_recent(15)
    favorites = await ds.get_favorites(15)
    cached = await ds.get_cached(15)
    featured_artists = await ds.get_featured_artists(100)
    featured_genres = await ds.get_featured_genres(100)
    return {
        "type": "discover_data",
        "data": {
            "recent": [track_to_dict(t) for t in recent],
            "favorites": [track_to_dict(t) for t in favorites],
            "cached_tracks": [track_to_dict(t) for t in cached],
            "featured_artists": featured_artists,
            "featured_genres": featured_genres
        }
    }

async def broadcast_discover_data(manager, db):
    payload = await _build_discover_payload(db)
    await manager.broadcast(payload)

_ws_handlers = {}

def register_ws_handler(action: str):
    def decorator(func):
        _ws_handlers[action] = func
        return func
    return decorator

@register_ws_handler("search")
async def _handle_search(data, ws, client_ip, state, ytdlp, manager, db):
    query = data.get("query", "").strip()
    if query:
        results = await ytdlp.search(query, max_results=10)
        await ws.send_str(json.dumps({
            "type": "search_results",
            "data": [track_to_dict(t) for t in results],
        }, ensure_ascii=False))

@register_ws_handler("discover")
async def _handle_discover(data, ws, client_ip, state, ytdlp, manager, db):
    payload = await _build_discover_payload(db)
    await ws.send_str(json.dumps(payload, ensure_ascii=False))

@register_ws_handler("toggle_favorite")
async def _handle_toggle_favorite(data, ws, client_ip, state, ytdlp, manager, db):
    video_id = data.get("video_id")
    if video_id:
        is_fav = await db.toggle_favorite(video_id)
        await ws.send_str(json.dumps({
            "type": "favorite_status",
            "data": {
                "video_id": video_id,
                "is_favorite": bool(is_fav)
            }
        }, ensure_ascii=False))

        if state.current_track and state.current_track.video_id == video_id:
            state.current_track.is_favorite = is_fav
            await manager.broadcast({
                "type": "state",
                "data": state_to_dict(state)
            })
        await broadcast_discover_data(manager, db)

@register_ws_handler("enqueue_genre_songs")
async def _handle_enqueue_genre_songs(data, ws, client_ip, state, ytdlp, manager, db):
    genre_name = data.get("genre")
    if genre_name:
        await db.increment_genre_click(genre_name)
        songs = await db.get_genre_songs(genre_name, total_limit=12, max_per_artist=3)
        if songs:
            await command_bus.execute(CMD_SET_MODE, PlaybackMode.QUEUE)
            await command_bus.execute(CMD_QUEUE_REPLACE, songs)
            await command_bus.execute(CMD_QUEUE_SELECT, 0)

@register_ws_handler("play_track")
async def _handle_play_track(data, ws, client_ip, state, ytdlp, manager, db):
    track = dict_to_track(data)
    if track:
        await command_bus.execute(CMD_PLAY_TRACK, track)

@register_ws_handler("toggle_pause")
async def _handle_toggle_pause(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_TOGGLE_PAUSE)

@register_ws_handler("next")
async def _handle_next(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_NEXT, data)

@register_ws_handler("prev")
async def _handle_prev(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_PREV)

@register_ws_handler("stop")
async def _handle_stop(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_STOP)

@register_ws_handler("seek")
async def _handle_seek(data, ws, client_ip, state, ytdlp, manager, db):
    position = data.get("position", 0)
    await command_bus.execute(CMD_SEEK, float(position))

@register_ws_handler("volume_up")
async def _handle_volume_up(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_VOLUME_UP)

@register_ws_handler("volume_down")
async def _handle_volume_down(data, ws, client_ip, state, ytdlp, manager, db):
    await command_bus.execute(CMD_VOLUME_DOWN)

@register_ws_handler("volume_set")
async def _handle_volume_set(data, ws, client_ip, state, ytdlp, manager, db):
    vol = data.get("volume", 80)
    await command_bus.execute(CMD_VOLUME_SET, {"volume": int(vol)})

@register_ws_handler("download")
async def _handle_download(data, ws, client_ip, state, ytdlp, manager, db):
    track = dict_to_track(data) if data else None
    await command_bus.execute(CMD_DOWNLOAD, track)

@register_ws_handler("delete_download")
async def _handle_delete_download(data, ws, client_ip, state, ytdlp, manager, db):
    track = dict_to_track(data) if data else None
    if track and track.video_id:
        db_track = await db.get_track(track.video_id)
        if db_track and db_track.local_path:
            import os
            from core.utils import user_download_path

            if os.path.exists(db_track.local_path):
                try:
                    os.remove(db_track.local_path)
                except Exception as e:
                    logger.error(f"Gagal menghapus cache {db_track.local_path}: {e}")

            user_path = user_download_path(db_track.artist, db_track.title)
            if user_path.exists():
                try:
                    os.remove(str(user_path))
                except:
                    pass

            db_track.local_path = None
            await db.set_local_path(db_track.video_id, None)

            if state.current_track and state.current_track.video_id == db_track.video_id:
                state.current_track.local_path = None
                await manager.broadcast({
                    "type": "state",
                    "data": state_to_dict(state)
                })

            await broadcast_discover_data(manager, db)
            await manager.broadcast({
                "type": "log",
                "data": f"Unduhan dihapus: {db_track.title}"
            })

@register_ws_handler("set_mode")
async def _handle_set_mode(data, ws, client_ip, state, ytdlp, manager, db):
    mode_str = data.get("mode", "queue").upper()
    mode = PlaybackMode.RADIO if mode_str == "RADIO" else PlaybackMode.QUEUE
    await command_bus.execute(CMD_SET_MODE, mode)

@register_ws_handler("queue_select")
async def _handle_queue_select(data, ws, client_ip, state, ytdlp, manager, db):
    index = data.get("index", 0)
    await command_bus.execute(CMD_QUEUE_SELECT, int(index))

@register_ws_handler("queue_remove")
async def _handle_queue_remove(data, ws, client_ip, state, ytdlp, manager, db):
    index = data.get("index", 0)
    await command_bus.execute(CMD_QUEUE_REMOVE, int(index))

@register_ws_handler("queue_add")
async def _handle_queue_add(data, ws, client_ip, state, ytdlp, manager, db):
    track = dict_to_track(data)
    if track:
        await command_bus.execute(CMD_QUEUE_ADD, track)

@register_ws_handler("queue_reorder")
async def _handle_queue_reorder(data, ws, client_ip, state, ytdlp, manager, db):
    from_idx = int(data.get("from_index", 0))
    to_idx = int(data.get("to_index", 0))
    await command_bus.execute(CMD_QUEUE_REORDER, {"from_index": from_idx, "to_index": to_idx})

@register_ws_handler("enqueue_artist_songs")
async def _handle_enqueue_artist_songs(data, ws, client_ip, state, ytdlp, manager, db):
    artist_name = data.get("artist")
    if artist_name:
        songs = await db.get_artist_songs_strict(artist=artist_name, limit=10)
        if songs:
            await db.increment_artist_click(artist_name)
            first_track, rest_tracks = songs[0], songs[1:]
            await command_bus.execute(CMD_QUEUE_REPLACE, rest_tracks)
            await command_bus.execute(CMD_PLAY_TRACK, first_track)

@register_ws_handler("radio_randomize")
async def _handle_radio_randomize(data, ws, client_ip, state, ytdlp, manager, db):
    seed_artist = data.get("seed_artist")
    await command_bus.execute(CMD_RADIO_RANDOMIZE, {"seed_artist": seed_artist})

@register_ws_handler("set_output")
async def _handle_set_output(data, ws, client_ip, state, ytdlp, manager, db):
    output_str = data.get("output", "device")
    output_val = AudioOutput.BROWSER if output_str == "browser" else AudioOutput.DEVICE
    await command_bus.execute(CMD_SET_OUTPUT, output_val)

@register_ws_handler("set_sponsorblock")
async def _handle_set_sponsorblock(data, ws, client_ip, state, ytdlp, manager, db):
    enabled = data.get("enabled", True)
    await command_bus.execute(CMD_SET_SPONSORBLOCK, bool(enabled))

@register_ws_handler("lyrics_offset")
async def _handle_lyrics_offset(data, ws, client_ip, state, ytdlp, manager, db):
    offset = data.get("offset", 0.0)
    await command_bus.execute(CMD_LYRICS_OFFSET, {"offset": float(offset)})

async def handle_ws_message(msg: dict, ws, client_ip: str, state, ytdlp, manager, db):
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

    if not await check_rate_limit(manager, client_ip, now):
        await ws.send_str(json.dumps({
            "type": "error",
            "data": "Terlalu banyak permintaan. Mohon tunggu sesaat."
        }))
        return

    try:
        if action in _ws_handlers:
            await _ws_handlers[action](data, ws, client_ip, state, ytdlp, manager, db)
        else:
            logger.warning(f"Unknown WS action: {action}")
    except Exception as e:
        logger.error(f"Error handling WS command '{action}': {e}", exc_info=True)
        try:
            await ws.send_str(json.dumps({
                "type": "error",
                "data": str(e),
            }))
        except Exception:
            pass


