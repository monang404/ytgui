"""
PATCH-1-03: Concurrent dispatch di EventBus dengan asyncio.gather
Verifikasi bahwa EventBus memanggil handlers secara concurrent (bukan sequential).
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from core.event_bus import EventBus
from core.events import DomainEvent
from dataclasses import dataclass

@dataclass
class TestEvent(DomainEvent):
    data: str = ""

@pytest.fixture
def bus():
    return EventBus()

@pytest.mark.asyncio
class TestEventBusConcurrentDispatch:
    """Checklist PATCH-1-03:
    - [x] Handler TRACK_PROGRESS berjalan paralel
    - [x] Satu handler lambat tidak memblokir handler lain
    - [x] Error di satu handler tidak mempengaruhi handler lain
    - [x] Handler sync tetap dipanggil dengan benar
    """

    async def test_handlers_run_concurrently(self, bus):
        """Dua async handler harus berjalan secara concurrent, bukan sequential.
        Jika sequential, total waktu >= 0.4s. Concurrent harus ~0.2s."""
        call_times = []

        async def slow_handler_1(event: TestEvent):
            start = time.monotonic()
            await asyncio.sleep(0.2)
            call_times.append(("h1", time.monotonic() - start))

        async def slow_handler_2(event: TestEvent):
            start = time.monotonic()
            await asyncio.sleep(0.2)
            call_times.append(("h2", time.monotonic() - start))

        bus.subscribe(TestEvent, slow_handler_1)
        bus.subscribe(TestEvent, slow_handler_2)

        start = time.monotonic()
        await bus.publish(TestEvent(data="data"))
        total = time.monotonic() - start

        assert len(call_times) == 2, "Kedua handler harus dipanggil"
        assert total < 0.35, (
            f"Handlers berjalan sequential ({total:.2f}s). "
            f"Harus concurrent (target < 0.35s)"
        )

    async def test_slow_handler_does_not_block_others(self, bus):
        """Handler lambat tidak boleh menghalangi handler lain."""
        fast_done = asyncio.Event()

        async def slow_handler(event: TestEvent):
            await asyncio.sleep(1.0)

        async def fast_handler(event: TestEvent):
            fast_done.set()

        bus.subscribe(TestEvent, slow_handler)
        bus.subscribe(TestEvent, fast_handler)

        publish_task = asyncio.create_task(bus.publish(TestEvent(data="data")))

        try:
            await asyncio.wait_for(fast_done.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            pytest.fail("Fast handler terblokir oleh slow handler — dispatch harus concurrent")

        publish_task.cancel()
        try:
            await publish_task
        except asyncio.CancelledError:
            pass

    async def test_error_in_one_handler_does_not_affect_others(self, bus):
        """Error di satu async handler TIDAK BOLEH menghentikan handler lain."""
        success_called = asyncio.Event()

        async def failing_handler(event: TestEvent):
            raise RuntimeError("I crashed!")

        async def success_handler(event: TestEvent):
            success_called.set()

        bus.subscribe(TestEvent, failing_handler)
        bus.subscribe(TestEvent, success_handler)

        await bus.publish(TestEvent(data="data"))

        assert success_called.is_set(), (
            "Success handler harus tetap dipanggil meskipun handler lain crash"
        )

    async def test_sync_handler_still_works(self, bus):
        """Handler sync (non-coroutine) harus tetap bisa dipanggil."""
        results = []

        def sync_handler(event: TestEvent):
            results.append(event.data)

        bus.subscribe(TestEvent, sync_handler)
        await bus.publish(TestEvent(data="hello"))

        assert results == ["hello"]

    async def test_mixed_sync_async_handlers(self, bus):
        """Mix sync dan async handlers harus semua terpanggil."""
        results = []

        def sync_handler(event: TestEvent):
            results.append("sync")

        async def async_handler(event: TestEvent):
            results.append("async")

        bus.subscribe(TestEvent, sync_handler)
        bus.subscribe(TestEvent, async_handler)

        await bus.publish(TestEvent(data="data"))

        assert "sync" in results, "Sync handler harus terpanggil"
        assert "async" in results, "Async handler harus terpanggil"
