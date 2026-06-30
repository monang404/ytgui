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
        data = json.dumps(message, ensure_ascii=False)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
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
                await handle_ws_message(data, ws, request.remote, state, ytdlp, manager, db)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(ws)

    return ws

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
            featured_artists = await ds.get_featured_artists(100)
            featured_genres = await ds.get_featured_genres(100)
            await ws.send_str(json.dumps({
                "type": "discover_data",
                "data": {
                    "recent": [track_to_dict(t) for t in recent],
                    "favorites": [track_to_dict(t) for t in favorites],
                    "cached_tracks": [track_to_dict(t) for t in cached],
                    "featured_artists": featured_artists,
                    "featured_genres": featured_genres
                }
            }, ensure_ascii=False))

        elif action == "toggle_favorite":
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
                
                # Update current track if it's the one that got toggled
                if state.current_track and state.current_track.video_id == video_id:
                    state.current_track.is_favorite = is_fav
                    await manager.broadcast({
                        "type": "state",
                        "data": state_to_dict(state)
                    })
                
                # Broadcast updated discover data
                ds = DiscoverService(db)
                recent = await ds.get_recent(15)
                favorites = await ds.get_favorites(15)
                cached = await ds.get_cached(15)
                featured_artists = await ds.get_featured_artists(100)
                featured_genres = await ds.get_featured_genres(100)
                await manager.broadcast({
                    "type": "discover_data",
                    "data": {
                        "recent": [track_to_dict(t) for t in recent],
                        "favorites": [track_to_dict(t) for t in favorites],
                        "cached_tracks": [track_to_dict(t) for t in cached],
                        "featured_artists": featured_artists,
                        "featured_genres": featured_genres
                    }
                })

        elif action == "enqueue_genre_songs":
            genre_name = data.get("genre")
            if genre_name:
                await db.increment_genre_click(genre_name)
                songs = await db.get_genre_songs(genre_name, total_limit=12, max_per_artist=3)
                
                if songs:
                    await command_bus.execute(CMD_SET_MODE, PlaybackMode.QUEUE)
                    state.queue.clear()
                    
                    for track in songs:
                        await command_bus.execute(CMD_QUEUE_ADD, track)
                        
                    await command_bus.execute(CMD_QUEUE_SELECT, 0)

        elif action == "play_track":
            track = dict_to_track(data)
            if track:
                await command_bus.execute(CMD_PLAY_TRACK, track)

        elif action == "toggle_pause":
            await command_bus.execute(CMD_TOGGLE_PAUSE)

        elif action == "next":
            await command_bus.execute(CMD_NEXT, data)

        elif action == "prev":
            await command_bus.execute(CMD_PREV)

        elif action == "stop":
            await command_bus.execute(CMD_STOP)

        elif action == "seek":
            position = data.get("position", 0)
            await command_bus.execute(CMD_SEEK, float(position))

        elif action == "volume_up":
            await command_bus.execute(CMD_VOLUME_UP)

        elif action == "volume_down":
            await command_bus.execute(CMD_VOLUME_DOWN)

        elif action == "volume_set":
            vol = data.get("volume", 80)
            await command_bus.execute(CMD_VOLUME_SET, {"volume": int(vol)})

        elif action == "download":
            await command_bus.execute(CMD_DOWNLOAD)

        elif action == "set_mode":
            mode_str = data.get("mode", "queue").upper()
            mode = PlaybackMode.RADIO if mode_str == "RADIO" else PlaybackMode.QUEUE
            await command_bus.execute(CMD_SET_MODE, mode)

        elif action == "queue_select":
            index = data.get("index", 0)
            await command_bus.execute(CMD_QUEUE_SELECT, int(index))

        elif action == "queue_remove":
            index = data.get("index", 0)
            await command_bus.execute(CMD_QUEUE_REMOVE, int(index))

        elif action == "queue_add":
            track = dict_to_track(data)
            if track:
                await command_bus.execute(CMD_QUEUE_ADD, track)

        elif action == "queue_reorder":
            from_idx = int(data.get("from_index", 0))
            to_idx = int(data.get("to_index", 0))
            await command_bus.execute(CMD_QUEUE_REORDER, {"from_index": from_idx, "to_index": to_idx})

        elif action == "enqueue_artist_songs":
            artist_name = data.get("artist")
            if artist_name:
                songs = await db.get_artist_songs_strict(artist=artist_name, limit=10)
                if songs:
                    await db.increment_artist_click(artist_name)
                    
                    await command_bus.execute(CMD_SET_MODE, PlaybackMode.QUEUE)
                    state.queue.clear()
                    
                    for track in songs:
                        await command_bus.execute(CMD_QUEUE_ADD, track)
                        
                    await command_bus.execute(CMD_QUEUE_SELECT, 0)

        elif action == "radio_randomize":
            seed_artist = data.get("seed_artist")
            await command_bus.execute(CMD_RADIO_RANDOMIZE, {"seed_artist": seed_artist})

        elif action == "set_output":
            output_str = data.get("output", "device")
            output_val = AudioOutput.BROWSER if output_str == "browser" else AudioOutput.DEVICE
            await command_bus.execute(CMD_SET_OUTPUT, output_val)

        elif action == "set_sponsorblock":
            enabled = data.get("enabled", True)
            await command_bus.execute(CMD_SET_SPONSORBLOCK, bool(enabled))

        elif action == "lyrics_offset":
            offset = data.get("offset", 0.0)
            await command_bus.execute(CMD_LYRICS_OFFSET, {"offset": float(offset)})

    except Exception as e:
        logger.error(f"Error handling WS command '{action}': {e}", exc_info=True)
        try:
            await ws.send_str(json.dumps({
                "type": "error",
                "data": str(e),
            }))
        except Exception:
            pass
