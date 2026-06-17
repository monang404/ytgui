"""
Purpose: EventBus untuk komunikasi antar modul secara decoupled dan asinkron.
Subscribes to: (tidak ada)
Publishes: (tidak ada)
"""

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger(__name__)

class EventBus:
    """
    Lightweight pub/sub. Modules do not import each other directly —
    all communication goes through events to prevent circular imports.
    """
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable):
        self._subscribers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable):
        """Remove a handler from an event."""
        try:
            self._subscribers[event].remove(handler)
        except ValueError:
            pass

    async def publish(self, event: str, data: Any = None):
        """Publish event to all subscribers. Exceptions in one handler
        do NOT prevent subsequent handlers from executing (CRITICAL-01 fix)."""
        for handler in self._subscribers[event]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Handler {getattr(handler, '__name__', handler)} error on '{event}': {e}", exc_info=True)

# Singleton
bus = EventBus()

# Event names constants

# === TRACK ===
TRACK_STARTED    = "track.started"    # data: TrackInfo
TRACK_ENDED      = "track.ended"      # data: {"reason": str}
TRACK_PROGRESS   = "track.progress"   # data: float (seconds)

# === QUEUE ===
QUEUE_UPDATED    = "queue.updated"    # data: None

# === LYRICS ===
LYRICS_UPDATED   = "lyrics.updated"   # data: None

# === DOWNLOAD ===
DOWNLOAD_PROGRESS = "download.progress"  # data: float 0.0–1.0
DOWNLOAD_COMPLETE = "download.complete"  # data: TrackInfo

# === SYSTEM ===
LOG_MESSAGE      = "log.message"      # data: str
APP_SHUTDOWN     = "app.shutdown"     # data: None

# === COMMANDS ===
CMD_PLAY_TRACK   = "cmd.play.track"       # data: TrackInfo — BARU
CMD_TOGGLE_PAUSE = "cmd.toggle.pause"
CMD_NEXT         = "cmd.next"
CMD_PREV         = "cmd.prev"
CMD_STOP         = "cmd.stop"
CMD_SEEK         = "cmd.seek"              # data: float
CMD_VOLUME_UP    = "cmd.volume.up"
CMD_VOLUME_DOWN  = "cmd.volume.down"
CMD_DOWNLOAD     = "cmd.download"          # data: TrackInfo | None
CMD_SEARCH       = "cmd.search"            # data: str
CMD_SET_MODE     = "cmd.set.mode"          # data: PlaybackMode — BARU
CMD_QUEUE_SELECT = "cmd.queue.select"      # data: int (index)
CMD_QUEUE_REMOVE = "cmd.queue.remove"      # data: int (index) — BARU
CMD_QUIT         = "cmd.quit"
