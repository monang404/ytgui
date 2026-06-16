import re
import logging
import aiohttp
from config import LYRICS_API_BASE
from core.event_bus import bus, LYRICS_UPDATED, TRACK_PROGRESS

logger = logging.getLogger(__name__)

class LyricsFetcher:
    """
    MED-01 fix: Accepts a shared aiohttp session.
    LOW-07 fix: Strips timestamp prefixes from displayed lyrics.
    """
    def __init__(self, state, session: aiohttp.ClientSession = None):
        self.state = state
        self.lyrics_data: list[tuple[float, str]] = []
        self._session = session
        bus.subscribe(TRACK_PROGRESS, self._on_progress)

    async def fetch(self, title: str, artist: str, duration: int):
        """Fetches synchronized lyrics from lrclib.net and parses them."""
        self.lyrics_data = []
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        await bus.publish(LYRICS_UPDATED)

        url = f"{LYRICS_API_BASE}/get"
        params = {"track_name": title, "artist_name": artist, "duration": duration}
        try:
            session = self._session or aiohttp.ClientSession()
            close_after = self._session is None
            try:
                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lrc = data.get("syncedLyrics") or data.get("plainLyrics", "")
                        self.lyrics_data = self._parse_lrc(lrc)
                        # LOW-07 fix: Store CLEAN lines (no timestamps) for display
                        self.state.lyrics_lines = [text for _, text in self.lyrics_data]
                        await bus.publish(LYRICS_UPDATED)
                        logger.info(f"Lyrics: fetched {len(self.lyrics_data)} lines")
            finally:
                if close_after:
                    await session.close()
        except Exception as e:
            logger.debug(f"Lyrics fetch failed: {e}")

    def _parse_lrc(self, lrc_text: str) -> list[tuple[float, str]]:
        """Parse LRC format. Strips timestamp tags from text content."""
        pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)")
        result = []
        for line in lrc_text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = pattern.match(line)
            if m:
                minutes, seconds, text = m.groups()
                timestamp = int(minutes) * 60 + float(seconds)
                # LOW-07: Only store the clean text, not the [MM:SS.ss] prefix
                result.append((timestamp, text.strip()))
            else:
                # Plain text line (no timestamp)
                if line:
                    result.append((0.0, line))
        
        return sorted(result, key=lambda x: x[0])

    async def _on_progress(self, position: float):
        """Find the active lyric index based on current playback position."""
        if not self.lyrics_data or not isinstance(position, (int, float)):
            return

        active_idx = 0
        for i, (timestamp, _) in enumerate(self.lyrics_data):
            if timestamp <= position:
                active_idx = i
            else:
                break
                
        if self.state.lyrics_index != active_idx:
            self.state.lyrics_index = active_idx
