"""
Purpose: EventBus untuk komunikasi antar modul secara decoupled dan asinkron.
Subscribes to: (tidak ada)
Publishes: (tidak ada)
"""

from typing import Callable, Type, TypeVar, Any
from collections import defaultdict
import asyncio
import structlog
import inspect
import weakref

from core.task_utils import safe_create_task
from core.events import DomainEvent
from core.observability import EVENT_COUNT

logger = structlog.get_logger(__name__)

E = TypeVar("E", bound=DomainEvent)

class EventBus:
    """
    Lightweight pub/sub using typed DomainEvents.
    Modules do not import each other directly —
    all communication goes through events to prevent circular imports.
    """
    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: Type[E], handler: Callable[[E], Any]):
        if inspect.ismethod(handler):
            ref = weakref.WeakMethod(handler)
        else:
            ref = handler
        self._subscribers[event_type].append(ref)

    def _resolve(self, ref):
        """Resolve ref ke handler asli. Return None jika dead weakref."""
        if isinstance(ref, weakref.ref):
            return ref()
        return ref

    def purge_dead_refs(self):
        """Hapus semua dead weakref dari seluruh subscriber list.
        Dipanggil otomatis dari unsubscribe(). Bisa juga dipanggil
        manual saat room dihancurkan untuk pembersihan menyeluruh.
        """
        for event_type in list(self._subscribers):
            self._subscribers[event_type] = [
                r for r in self._subscribers[event_type]
                if self._resolve(r) is not None
            ]
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

    def unsubscribe(self, event_type: Type[E], handler: Callable[[E], Any]):
        """Remove a handler from an event, sekaligus bersihkan dead refs."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                r for r in self._subscribers[event_type]
                if self._resolve(r) is not None and self._resolve(r) != handler
            ]
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
        self.purge_dead_refs()

    async def publish(self, event: DomainEvent):
        """Publish event to all subscribers. Exceptions in one handler
        do NOT prevent subsequent handlers from executing (CRITICAL-01 fix)."""
        event_type = type(event)

        EVENT_COUNT.labels(event_type=event_type.__name__).inc()

        active_handlers = []
        for ref in list(self._subscribers.get(event_type, [])):
            if isinstance(ref, weakref.ref):
                handler = ref()
                if handler is None:
                    self._subscribers[event_type].remove(ref)
                    continue
            else:
                handler = ref
            active_handlers.append(handler)

        # Concurrent dispatch with error boundary
        tasks = []
        for handler in active_handlers:
            if asyncio.iscoroutinefunction(handler):
                async def _wrap_handler(h=handler):
                    try:
                        await h(event)
                    except Exception as e:
                        logger.error(f"Async Handler {getattr(h, '__name__', h)} error on '{event_type.__name__}': {e}", exc_info=True)
                tasks.append(safe_create_task(_wrap_handler(), name=f"event_{event_type.__name__}"))
            else:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Handler {getattr(handler, '__name__', handler)} error on '{event_type.__name__}': {e}", exc_info=True)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

bus = EventBus()
