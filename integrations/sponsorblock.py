import json
import aiohttp
import logging
from typing import Optional
from config import SPONSORBLOCK_CATS
from core.event_bus import bus, TRACK_PROGRESS, LOG_MESSAGE
from core.state import AppState
from core.ports import AudioPlayerPort
from core.task_utils import safe_create_task

logger = logging.getLogger(__name__)
SPONSORBLOCK_API = "https://sponsor.ajay.app/api/skipSegments"

class SponsorBlockHandler:
    """
    HIGH-02 fix: Uses json.dumps for category serialization.
    MED-01 fix: Accepts a shared aiohttp session.
    """
    def __init__(self, mpv: AudioPlayerPort, state: AppState, session: Optional[aiohttp.ClientSession] = None):
        self.mpv = mpv
        self.state = state
        self.segments: list[tuple[float, float]] = []
        self._session = session
        bus.subscribe(TRACK_PROGRESS, self._on_progress)

    def cleanup(self):
        bus.unsubscribe(TRACK_PROGRESS, self._on_progress)

    async def fetch_segments(self, video_id: str):
        """Fetches skip segments and stores them in memory for the current track."""
        self.segments = []
        if self.state:
            self.state.sponsorblock_active = False
        
        # HIGH-02 fix: Use json.dumps instead of str().replace()
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
                        if self.state:
                            self.state.sponsorblock_active = len(self.segments) > 0
                        logger.info(f"SponsorBlock: {len(self.segments)} segments for {video_id}")
                    elif resp.status == 404:
                        pass  # No segments for this video, that's normal
            finally:
                if close_after:
                    await session.close()
        except Exception as e:
            logger.debug(f"SponsorBlock fetch failed: {e}")

    async def _on_progress(self, current_pos: float):
        """Called every ~0.5s by MpvController. Seeks past sponsored segments."""
        if not self.segments or not isinstance(current_pos, (int, float)):
            return

        for start, end in self.segments:
            if start <= current_pos <= start + 0.6:
                await self.mpv.seek(end)
                await bus.publish(LOG_MESSAGE, f"Melewati sponsor ({int(start)}s - {int(end)}s)")
                break
