"""
Purpose: Mengelola kontrol volume MPV.
Subscribes to: CMD_VOLUME_UP, CMD_VOLUME_DOWN
Publishes: LOG_MESSAGE
"""

import asyncio
from core.event_bus import EventBus
from core.events import LogMessageEvent
from core.command_bus import CommandBus
from core.ports import AudioPlayerPort
from core.state import AppState, AudioOutput

class VolumeService:
    def __init__(self, bus: EventBus, mpv: AudioPlayerPort, state: AppState):
        self.bus = bus
        self.mpv = mpv
        self.state = state
        self.current_volume = state.volume

    async def _on_volume_up(self, _data=None):
        self.current_volume = min(100, self.current_volume + 5)
        await self._apply_volume()

    async def _on_volume_down(self, _data=None):
        self.current_volume = max(0, self.current_volume - 5)
        await self._apply_volume()

    async def _on_volume_set(self, data):
        vol = data.get("volume", 80)
        self.current_volume = max(0, min(100, int(vol)))
        await self._apply_volume()

    async def _apply_volume(self):
        if getattr(self.state, "audio_output", AudioOutput.DEVICE) == AudioOutput.BROWSER:
            await self.mpv.set_volume(0)
        else:
            await self.mpv.set_volume(self.current_volume)
        self.state.volume = self.current_volume
        await self.bus.publish(LogMessageEvent(message=f"Volume: {self.current_volume}%"))
