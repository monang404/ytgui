import pytest
import asyncio
from core.command_bus import CommandBus

@pytest.fixture
def command_bus():
    return CommandBus()

@pytest.mark.asyncio
async def test_command_bus_register_and_execute(command_bus):
    called = False
    
    async def my_handler(room_id, payload):
        nonlocal called
        called = True
        assert room_id == "default"
        assert payload == "test_payload"

    command_bus.register("TEST_CMD", my_handler)
    await command_bus.execute("TEST_CMD", data="test_payload")
    
    assert called is True

@pytest.mark.asyncio
async def test_command_bus_single_writer(command_bus):
    async def handler1(payload): pass
    async def handler2(payload): pass
    
    command_bus.register("TEST_CMD", handler1)
    
    with pytest.raises(RuntimeError) as exc_info:
        command_bus.register("TEST_CMD", handler2)
        
    assert "already registered" in str(exc_info.value)

@pytest.mark.asyncio
async def test_command_bus_execute_unregistered(command_bus):
    with pytest.raises(RuntimeError) as exc_info:
        await command_bus.execute("UNREGISTERED_CMD")
        
    assert "No handler registered for command" in str(exc_info.value)
