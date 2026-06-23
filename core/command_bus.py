"""
Purpose: CommandBus untuk single-writer pattern (1-to-1).
Berbeda dengan EventBus (pub/sub 1-to-many), CommandBus menjamin
hanya ada SATU handler untuk setiap command.
"""

import asyncio
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)

class CommandBus:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register(self, command: str, handler: Callable):
        if command in self._handlers:
            raise RuntimeError(f"Command '{command}' is already registered to {self._handlers[command]}")
        self._handlers[command] = handler

    def unregister(self, command: str):
        if command in self._handlers:
            del self._handlers[command]

    async def execute(self, command: str, data: Any = None) -> Any:
        if command not in self._handlers:
            raise RuntimeError(f"No handler registered for command '{command}'")
        
        handler = self._handlers[command]
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(data)
            else:
                return handler(data)
        except Exception as e:
            logger.error(f"Command execution error for '{command}': {e}", exc_info=True)
            raise

command_bus = CommandBus()

# === COMMANDS ===
CMD_PLAY_TRACK   = "cmd.play.track"       # data: TrackInfo
CMD_TOGGLE_PAUSE = "cmd.toggle.pause"
CMD_NEXT         = "cmd.next"
CMD_PREV         = "cmd.prev"
CMD_STOP         = "cmd.stop"
CMD_SEEK         = "cmd.seek"              # data: float
CMD_VOLUME_UP    = "cmd.volume.up"
CMD_VOLUME_DOWN  = "cmd.volume.down"
CMD_DOWNLOAD     = "cmd.download"          # data: TrackInfo | None
CMD_SET_MODE     = "cmd.set.mode"          # data: PlaybackMode
CMD_SET_OUTPUT   = "cmd.set.output"        # data: AudioOutput
CMD_QUEUE_SELECT = "cmd.queue.select"      # data: int (index)
CMD_QUEUE_ADD    = "cmd.queue.add"         # data: TrackInfo
CMD_QUEUE_REMOVE = "cmd.queue.remove"      # data: int (index)
CMD_RADIO_RANDOMIZE = "cmd.radio.randomize"
CMD_QUIT         = "cmd.quit"
