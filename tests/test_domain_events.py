import pytest
import asyncio
from core.event_bus import EventBus
from core.events import LogMessageEvent

@pytest.mark.asyncio
async def test_typed_domain_events():
    bus = EventBus()
    received_events = []

    async def handler(event: LogMessageEvent):
        received_events.append(event)

    bus.subscribe(LogMessageEvent, handler)

    event = LogMessageEvent(message="test message")
    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].message == "test message"

@pytest.mark.asyncio
async def test_unsubscribe_domain_events():
    bus = EventBus()
    received_events = []

    async def handler(event: LogMessageEvent):
        received_events.append(event)

    bus.subscribe(LogMessageEvent, handler)
    bus.unsubscribe(LogMessageEvent, handler)

    event = LogMessageEvent(message="test message")
    await bus.publish(event)

    assert len(received_events) == 0

@pytest.mark.asyncio
async def test_error_boundary_domain_events():
    bus = EventBus()
    received_events = []

    async def bad_handler(event: LogMessageEvent):
        raise ValueError("Error in handler")

    async def good_handler(event: LogMessageEvent):
        received_events.append(event)

    bus.subscribe(LogMessageEvent, bad_handler)
    bus.subscribe(LogMessageEvent, good_handler)

    event = LogMessageEvent(message="test message")
    await bus.publish(event)

    # good_handler should still be executed
    assert len(received_events) == 1
