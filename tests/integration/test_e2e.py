"""
PATCH-3-05: Integration Tests (tanpa MPV nyata)

Menggunakan aiohttp test client dan WebSocket mock untuk menguji alur:
- Koneksi WebSocket ke room
- Otentikasi admin
- Command routing (search)
- Endpoint /health dan /metrics
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from server.app import create_app
from core.room_manager import RoomManager
from core.ports import DatabasePort, MediaExtractorPort
from core.state import TrackInfo, AppState, PlayerStatus


@pytest.fixture
def mock_db():
    db = MagicMock(spec=DatabasePort)
    db.conn = True
    db.verify_session = AsyncMock(return_value=True)
    db.get_track = AsyncMock(return_value=None)
    db.increment_play_count = AsyncMock()
    db.create_session = AsyncMock()
    db.upsert_track = AsyncMock()
    return db


@pytest.fixture
def mock_ytdlp():
    ytdlp = MagicMock(spec=MediaExtractorPort)
    ytdlp.get_stream_url = AsyncMock(return_value="https://googlevideo.com/stream.mp3")
    ytdlp.search = AsyncMock(return_value=[
        TrackInfo(video_id="test1", title="Test Song", artist="Tester", duration=200, thumbnail="")
    ])
    return ytdlp


@pytest.fixture
def mock_room_manager(mock_db, mock_ytdlp):
    """Creates a fully mocked RoomManager that returns a fake room without MPV."""
    manager = MagicMock(spec=RoomManager)
    
    # Create a fake room-like object
    fake_room = MagicMock()
    fake_state = AppState(room_id="default")
    fake_room.state = fake_state
    fake_room.playback = MagicMock()
    fake_room.playback.mpv = MagicMock()
    fake_room.playback.mpv.is_connected = True
    
    # TASK-1.4: rooms dict is required by handle_websocket for room validation
    manager.rooms = {"default": fake_room}
    manager.get_or_create_room = AsyncMock(return_value=fake_room)
    return manager


@pytest.mark.asyncio
async def test_e2e_health_endpoint(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-05: Verifikasi endpoint /health."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    resp = await client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert "status" in data
    assert data["db"] == "connected"


@pytest.mark.asyncio
async def test_e2e_metrics_endpoint(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-04: Verifikasi endpoint /metrics tersedia (Prometheus format)."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    resp = await client.get("/metrics")
    assert resp.status == 200
    text = await resp.text()
    # Prometheus text format should contain our custom metrics
    assert "ytplayer_commands_total" in text or "ytplayer_events_total" in text or "# HELP" in text


@pytest.mark.asyncio
async def test_e2e_websocket_connect_initial_state(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-05: Verifikasi WS konek dan menerima initial state."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    ws = await client.ws_connect("/ws?room=default")
    
    # First message: initial state broadcast
    msg = await ws.receive()
    assert msg.type.value == 1  # TEXT = 1
    data = json.loads(msg.data)
    assert data["type"] == "state"
    assert "status" in data["data"]
    
    await ws.close()


@pytest.mark.asyncio
async def test_e2e_websocket_auth_with_token(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-05: Verifikasi WS autentikasi token berhasil."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    ws = await client.ws_connect("/ws?room=default")
    
    # Consume initial state
    await ws.receive()
    
    # Send auth with token
    await ws.send_json({
        "type": "cmd",
        "action": "auth",
        "data": {"token": "test-token"}  # mock_db.verify_session returns True
    })
    
    msg = await ws.receive()
    data = json.loads(msg.data)
    assert data["type"] == "auth_status"
    assert data["data"]["success"] is True
    
    await ws.close()


@pytest.mark.asyncio
async def test_e2e_websocket_search(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-05: Verifikasi WS search command mengembalikan hasil."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    ws = await client.ws_connect("/ws?room=default")
    
    # Consume initial state
    await ws.receive()
    
    # Authenticate first
    await ws.send_json({"type": "cmd", "action": "auth", "data": {"token": "test-token"}})
    await ws.receive()  # consume auth_status
    
    # Send search command
    await ws.send_json({
        "type": "cmd",
        "action": "search",
        "data": {"query": "Test Song"}
    })
    
    msg = await ws.receive()
    data = json.loads(msg.data)
    assert data["type"] == "search_results"
    assert len(data["data"]) > 0
    assert data["data"][0]["video_id"] == "test1"
    
    await ws.close()


@pytest.mark.asyncio
async def test_e2e_websocket_unauthenticated_command_rejected(aiohttp_client, mock_room_manager, mock_ytdlp, mock_db):
    """PATCH-3-05: Verifikasi command ditolak bila belum autentikasi."""
    app = create_app(mock_room_manager, mock_ytdlp, mock_db)
    client = await aiohttp_client(app)
    
    ws = await client.ws_connect("/ws?room=default")
    
    # Consume initial state
    await ws.receive()
    
    # Send command WITHOUT auth
    await ws.send_json({
        "type": "cmd",
        "action": "stop",
        "data": {}
    })
    
    msg = await ws.receive()
    data = json.loads(msg.data)
    assert data["type"] == "error"
    assert "ditolak" in data["data"] or "login" in data["data"].lower()
    
    await ws.close()
