"""
Purpose: CommandBus untuk single-writer pattern (1-to-1).
Berbeda dengan EventBus (pub/sub 1-to-many), CommandBus menjamin
hanya ada SATU handler untuk setiap command.
"""

import asyncio
import structlog
import time
from typing import Callable, Any, Dict
from core.observability import COMMAND_COUNT, COMMAND_LATENCY, tracer

logger = structlog.get_logger(__name__)

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

    async def execute(self, command: str, room_id: str = "default", data: Any = None) -> Any:
        if command not in self._handlers:
            raise RuntimeError(f"No handler registered for command '{command}'")
        
        handler = self._handlers[command]
        start_time = time.perf_counter()
        status = "success"
        
        with tracer.start_as_current_span(f"CommandBus.execute:{command}") as span:
            span.set_attribute("room_id", room_id)
            span.set_attribute("command", command)
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(room_id, data)
                else:
                    return handler(room_id, data)
            except Exception as e:
                status = "error"
                span.record_exception(e)
                logger.error(f"Command execution error for '{command}': {e}", exc_info=True)
                raise
            finally:
                duration = time.perf_counter() - start_time
                COMMAND_LATENCY.labels(command_name=command, room_id=room_id).observe(duration)
                COMMAND_COUNT.labels(command_name=command, room_id=room_id, status=status).inc()

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
