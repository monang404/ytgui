import time
from server.serializers import state_to_dict
from server.handlers.websocket import ConnectionManager
from core.state import AppState

class BroadcastService:
    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def broadcast_state(self, state: AppState):
        await self.manager.broadcast({
            "type": "state",
            "data": state_to_dict(state),
        })

    async def broadcast_progress(self, position: float, status_name: str):
        await self.manager.broadcast({
            "type": "progress",
            "data": {
                "position": position,
                "status": status_name,
                "server_ts": time.time(),
            },
        })

    async def broadcast_lyrics(self, state: AppState):
        await self.manager.broadcast({
            "type": "lyrics",
            "data": {
                "lyrics_lines": list(state.lyrics_lines),
                "lyrics_timestamps": list(state.lyrics_timestamps),
                "lyrics_index": state.lyrics_index,
                "lyrics_offset": state.lyrics_offset,
                "lyrics_loading": getattr(state, "lyrics_loading", False),
            },
        })

    async def broadcast_log(self, message: str):
        await self.manager.broadcast({
            "type": "log",
            "data": message,
        })
