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
TRACK_STARTED    = "track.started"
TRACK_ENDED      = "track.ended"
TRACK_PROGRESS   = "track.progress"
QUEUE_EMPTY      = "queue.empty"
QUEUE_UPDATED    = "queue.updated"
VOLUME_CHANGED   = "volume.changed"
LYRICS_UPDATED   = "lyrics.updated"
LYRICS_SYNC      = "lyrics.sync"
ERROR_OCCURRED   = "error.occurred"
SEARCH_RESULTS   = "search.results"
LOG_MESSAGE      = "log.message"
DOWNLOAD_PROGRESS = "download.progress"
DOWNLOAD_COMPLETE = "download.complete"
SKIP_SEGMENT     = "skip.segment"
APP_SHUTDOWN     = "app.shutdown"

# Command Events
CMD_TOGGLE_PAUSE = "cmd.toggle.pause"
CMD_NEXT         = "cmd.next"
CMD_PREV         = "cmd.prev"
CMD_STOP         = "cmd.stop"
CMD_VOLUME_UP    = "cmd.volume.up"
CMD_VOLUME_DOWN  = "cmd.volume.down"
CMD_DOWNLOAD     = "cmd.download"
CMD_SEARCH       = "cmd.search"
CMD_TOGGLE_RADIO = "cmd.toggle.radio"
CMD_QUEUE_SELECT = "cmd.queue.select"
CMD_TOGGLE_LYRICS = "cmd.toggle.lyrics"
CMD_QUIT         = "cmd.quit"
CMD_FOCUS_SEARCH = "cmd.focus.search"
CMD_UNFOCUS      = "cmd.unfocus"
CMD_SEEK         = "cmd.seek"
