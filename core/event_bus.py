"""
Purpose: EventBus untuk komunikasi antar modul secara decoupled dan asinkron.
Subscribes to: (tidak ada)
Publishes: (tidak ada)
"""

import weakref
from typing import Callable, Any
from collections import defaultdict
import asyncio
import logging
import inspect

from core.task_utils import safe_create_task

logger = logging.getLogger(__name__)

class EventBus:
    """
    Lightweight pub/sub. Modules do not import each other directly —
    all communication goes through events to prevent circular imports.
    """
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event: str, handler: Callable):
        # Gunakan weakref untuk method agar tidak memory leak
        if inspect.ismethod(handler):
            ref = weakref.WeakMethod(handler)
        else:
            ref = handler # Fallback strong reference untuk fungsi biasa/lambda
        self._subscribers[event].append(ref)

    def unsubscribe(self, event: str, handler: Callable):
        """Remove a handler from an event."""
        if event in self._subscribers:
            self._subscribers[event] = [
                r for r in self._subscribers[event]
                if (r() if isinstance(r, weakref.ref) else r) != handler
            ]

    async def publish(self, event: str, data: Any = None):
        """Publish event to all subscribers. Exceptions in one handler
        do NOT prevent subsequent handlers from executing (CRITICAL-01 fix)."""
        active_handlers = []
        for ref in list(self._subscribers[event]):
            if isinstance(ref, weakref.ref):
                handler = ref()
                if handler is None:
                    self._subscribers[event].remove(ref) # Cleanup dead reference
                    continue
            else:
                handler = ref
            active_handlers.append(handler)

        # PATCH-1-03: Concurrent dispatch instead of sequential blocking
        tasks = []
        for handler in active_handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(safe_create_task(handler(data), name=f"event_{event}"))
            else:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Handler {getattr(handler, '__name__', handler)} error on '{event}': {e}", exc_info=True)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

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
DOWNLOAD_COMPLETE = "download.complete"  # data: TrackInfo

# === SYSTEM ===
LOG_MESSAGE      = "log.message"      # data: str

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
CMD_SET_MODE     = "cmd.set.mode"          # data: PlaybackMode — BARU
CMD_SET_OUTPUT   = "cmd.set.output"        # data: str ("device" or "browser")
CMD_QUEUE_SELECT = "cmd.queue.select"      # data: int (index)
CMD_QUEUE_ADD    = "cmd.queue.add"         # data: TrackInfo
CMD_QUEUE_REMOVE = "cmd.queue.remove"      # data: int (index) — BARU
CMD_RADIO_RANDOMIZE = "cmd.radio.randomize"
CMD_QUIT         = "cmd.quit"
