"""
Purpose: Mengelola kontrol volume MPV.
Subscribes to: CMD_VOLUME_UP, CMD_VOLUME_DOWN
Publishes: LOG_MESSAGE
"""

import asyncio
from core.event_bus import EventBus, LOG_MESSAGE
from core.command_bus import command_bus, CMD_VOLUME_UP, CMD_VOLUME_DOWN
from core.ports import AudioPlayerPort
from core.state import AppState, AudioOutput

class VolumeService:
    def __init__(self, bus: EventBus, mpv: AudioPlayerPort, state: AppState):
        self.bus = bus
        self.mpv = mpv
        self.state = state
        self.current_volume = state.volume
        
        command_bus.register(CMD_VOLUME_UP, self._on_volume_up)
        command_bus.register(CMD_VOLUME_DOWN, self._on_volume_down)
        
    async def _on_volume_up(self, _data=None):
        self.current_volume = min(150, self.current_volume + 5)
        await self._apply_volume()
        
    async def _on_volume_down(self, _data=None):
        self.current_volume = max(0, self.current_volume - 5)
        await self._apply_volume()
        
    async def _apply_volume(self):
        if getattr(self.state, "audio_output", AudioOutput.DEVICE) == AudioOutput.BROWSER:
            await self.mpv.set_volume(0)
        else:
            await self.mpv.set_volume(self.current_volume)
        self.state.volume = self.current_volume
        await self.bus.publish(LOG_MESSAGE, f"Volume: {self.current_volume}%")
