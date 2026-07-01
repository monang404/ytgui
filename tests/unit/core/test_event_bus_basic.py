import pytest
import asyncio
from unittest.mock import Mock
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
async def test_event_bus_strong_reference(bus):
    mock_handler = Mock()
    bus.subscribe(TestEvent, mock_handler)
    event = TestEvent(data="data")
    await bus.publish(event)
    mock_handler.assert_called_once_with(event)

@pytest.mark.asyncio
async def test_event_bus_weak_reference(bus):
    class Subscriber:
        def __init__(self):
            self.called = False

        def handle(self, event: TestEvent):
            self.called = True

    sub = Subscriber()
    bus.subscribe(TestEvent, sub.handle)

    await bus.publish(TestEvent(data="data1"))
    assert sub.called

    del sub
    import gc
    gc.collect()

    await bus.publish(TestEvent(data="data2"))

@pytest.mark.asyncio
async def test_event_bus_unsubscribe(bus):
    mock_handler = Mock()
    bus.subscribe(TestEvent, mock_handler)
    bus.unsubscribe(TestEvent, mock_handler)

    await bus.publish(TestEvent(data="data"))
    mock_handler.assert_not_called()

@pytest.mark.asyncio
async def test_event_bus_error_isolation(bus):
    def failing_handler(event: TestEvent):
        raise Exception("Oops")

    success_handler = Mock()

    bus.subscribe(TestEvent, failing_handler)
    bus.subscribe(TestEvent, success_handler)

    event = TestEvent(data="data")
    await bus.publish(event)
    success_handler.assert_called_once_with(event)
