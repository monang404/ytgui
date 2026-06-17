import re
import logging
import aiohttp
import bisect
import asyncio
import syncedlyrics
from contextlib import asynccontextmanager
<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
from config import LYRICS_API_BASE
from core.event_bus import bus, LYRICS_UPDATED, TRACK_PROGRESS

logger = logging.getLogger(__name__)

from core.state import TrackInfo

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

    async def fetch(self, track: TrackInfo):
        """Fetches synchronized lyrics from lrclib.net and parses them."""
        title = track.title
        artist = track.artist
        duration = track.duration
        self.lyrics_data = []
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        await bus.publish(LYRICS_UPDATED)

        @asynccontextmanager
        async def get_session():
            if self._session:
                yield self._session
            else:
                async with aiohttp.ClientSession() as s:
                    yield s
        
        try:
            async with get_session() as session:
                # 1. Coba pencarian spesifik (exact match) dengan durasi
                url_get = f"{LYRICS_API_BASE}/get"
                params_get = {"track_name": title, "artist_name": artist, "duration": duration}
                lrc = None
                
                async with session.get(url_get, params=params_get, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lrc = data.get("syncedLyrics") or data.get("plainLyrics", "")
<<<<<<< Updated upstream
                    
=======

>>>>>>> Stashed changes
            # 2. Jika gagal karena durasi tidak persis sama (sering terjadi di YouTube), gunakan fallback search
            if not lrc:
                url_search = f"{LYRICS_API_BASE}/search"
                # Format query: Gabungkan title dan artist jika artist bukan 'Unknown'
                query = f"{title} {artist}" if artist and artist.lower() not in ["unknown", "topic"] else title
                params_search = {"q": query}
                
                async with session.get(url_search, params=params_search, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        if isinstance(results, list):
                            for res in results:
                                lrc = res.get("syncedLyrics") or res.get("plainLyrics", "")
                                if lrc:
                                    break
            
            # 3. Ultimate Fallback: gunakan pustaka syncedlyrics untuk mencari di Musixmatch, NetEase, dll.
            if not lrc:
                logger.info("lrclib failed. Falling back to syncedlyrics (Musixmatch/NetEase/etc)...")
                
                # Bersihkan judul dari embel-embel (Official Video), [Lyrics], dll.
                clean_title = re.sub(r'[\(\[].*?[\)\]]', '', title)
                for kw in ['official', 'music video', 'lyric', 'lyrics', 'audio', 'video']:
                    clean_title = re.sub(rf'\b{kw}s?\b', '', clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip('- ')
                
                # Jika judul aslinya sudah memiliki format "Artis - Judul", jangan tambahkan nama channel (seperti NAGASWARA)
                if "-" in title:
                    query = clean_title
                else:
                    query = f"{clean_title} {artist}" if artist and artist.lower() not in ["unknown", "topic"] else clean_title
                
                logger.info(f"syncedlyrics query: {query}")
                loop = asyncio.get_running_loop()
                lrc = await loop.run_in_executor(None, syncedlyrics.search, query)
            
            if lrc:
                self.lyrics_data = self._parse_lrc(lrc)
                # LOW-07 fix: Store CLEAN lines (no timestamps) for display
                self.state.lyrics_lines = [text for _, text in self.lyrics_data]
                await bus.publish(LYRICS_UPDATED)
                logger.info(f"Lyrics: fetched {len(self.lyrics_data)} lines")
            else:
                logger.info("Lyrics: No lyrics found anywhere")
                
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

        timestamps = [t for t, _ in self.lyrics_data]
        active_idx = bisect.bisect_right(timestamps, position) - 1
        active_idx = max(0, active_idx)
                
        if self.state.lyrics_index != active_idx:
            self.state.lyrics_index = active_idx
