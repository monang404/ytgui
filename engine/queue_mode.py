"""
Purpose: Mengelola playback dari user queue.
Subscribes to: (tidak ada — dipanggil oleh PlaybackController)
Publishes: QUEUE_UPDATED
"""

from core.event_bus import bus, QUEUE_UPDATED
from core.state import PlayerStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.playback_controller import PlaybackController

class QueueMode:
    """
    Purpose: Mengelola playback dari user queue.
    Subscribes to: (tidak ada — dipanggil oleh PlaybackController)
    Publishes: QUEUE_UPDATED
    """
    async def next(self, controller: "PlaybackController") -> None:
        """Dipanggil PlaybackController saat track berakhir di QUEUE mode."""
        if not controller.state.queue:
            controller.state.status = PlayerStatus.IDLE
            controller.state.current_track = None
            await bus.publish(QUEUE_UPDATED)
            return

        track = controller.state.queue.popleft()
        await controller.play_track(track)
