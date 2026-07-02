import json
import aiohttp
import structlog
from typing import Optional
from config import SPONSORBLOCK_CATS
from core.event_bus import EventBus
from core.events import TrackProgressEvent, LogMessageEvent
from core.state import AppState
from core.ports import AudioPlayerPort
from core.task_utils import safe_create_task

logger = structlog.get_logger(__name__)
SPONSORBLOCK_API = "https://sponsor.ajay.app/api/skipSegments"

class SponsorBlockHandler:
    """
    HIGH-02 fix: Uses json.dumps for category serialization.
    MED-01 fix: Accepts a shared aiohttp session.
    """
    def __init__(self, mpv: AudioPlayerPort, state: AppState, session: Optional[aiohttp.ClientSession] = None, event_bus: EventBus = None):
        self.mpv = mpv
        self.state = state
        self.segments: list[tuple[float, float]] = []
        self._session = session
        # Injected bus (fallback ke global bus)
        if event_bus is None:
            from core.event_bus import bus as _global_bus
            event_bus = _global_bus
        self._bus = event_bus
        self._bus.subscribe(TrackProgressEvent, self._on_progress)

    def cleanup(self):
        self._bus.unsubscribe(TrackProgressEvent, self._on_progress)

    async def fetch_segments(self, video_id: str):
        """Fetches skip segments and stores them in memory for the current track."""
        self.segments = []
        params = {
            "videoID": video_id,
            "categories": json.dumps(SPONSORBLOCK_CATS),
        }

        try:
            session = self._session or aiohttp.ClientSession()
            close_after = self._session is None
            try:
                async with session.get(
                    SPONSORBLOCK_API, params=params,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.segments = [
                            (seg["segment"][0], seg["segment"][1]) for seg in data
                        ]
                        logger.info(f"SponsorBlock: {len(self.segments)} segments for {video_id}")
                    elif resp.status == 404:
                        pass
            finally:
                if close_after:
                    await session.close()
        except Exception as e:
            logger.debug(f"SponsorBlock fetch failed: {e}")

    async def _on_progress(self, event: TrackProgressEvent):
        """Called every ~0.5s by MpvController. Seeks past sponsored segments."""
        current_pos = event.position
        if getattr(self.state, "sponsorblock_active", True) == False:
            return
        if not self.segments or not isinstance(current_pos, (int, float)):
            return

        for start, end in self.segments:
            if start <= current_pos < end:
                await self.mpv.seek(end)
                await self._bus.publish(LogMessageEvent(message=f"Melewati sponsor ({int(start)}s - {int(end)}s)"))
                break
