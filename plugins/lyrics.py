import re
import structlog
import aiohttp
import bisect
import asyncio
import syncedlyrics
from contextlib import asynccontextmanager
from config import LYRICS_API_BASE
from core.event_bus import EventBus
from core.events import LyricsUpdatedEvent, TrackProgressEvent

logger = structlog.get_logger(__name__)

from core.state import TrackInfo

class LyricsFetcher:
    """
    MED-01 fix: Accepts a shared aiohttp session.
    LOW-07 fix: Strips timestamp prefixes from displayed lyrics.
    """
    def __init__(self, state, session: aiohttp.ClientSession = None, event_bus: EventBus = None):
        self.state = state
        self.lyrics_data: list[tuple[float, str]] = []
        self._session = session
        self._owns_session = False  # True jika kita yang buat, kita yang harus tutup
        self._current_generation = 0
        # TASK-3.4: Injected per-room bus (fallback ke global jika belum direfactor)
        if event_bus is None:
            from core.event_bus import bus as _global_bus
            event_bus = _global_bus
        self._bus = event_bus
        self._bus.subscribe(TrackProgressEvent, self._on_progress)

    def _get_session(self) -> aiohttp.ClientSession:
        """Kembalikan session yang ada, atau buat satu fallback session yang persisten."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    def cleanup(self):
        self._bus.unsubscribe(TrackProgressEvent, self._on_progress)
        if self._owns_session and self._session and not self._session.closed:
            import asyncio as _asyncio
            try:
                loop = _asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._session.close())
                else:
                    loop.run_until_complete(self._session.close())
            except Exception:
                pass
            self._session = None
            self._owns_session = False

    async def fetch(self, track: TrackInfo):
        """Fetches synchronized lyrics from lrclib.net and parses them."""
        title = track.title
        artist = track.artist
        duration = track.duration
        self.lyrics_data = []
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        self.state.lyrics_offset = 0.0
        self.state.lyrics_loading = True
        
        self._current_generation += 1
        gen = self._current_generation
        
        await self._bus.publish(LyricsUpdatedEvent())

        try:
            session = self._get_session()
            if True:  # dummy block untuk menjaga indentasi try/except di bawah
                # 1. Coba pencarian spesifik (exact match) dengan durasi
                url_get = f"{LYRICS_API_BASE}/get"
                params_get = {"track_name": title, "artist_name": artist, "duration": duration}
                lrc = None
                
                async with session.get(url_get, params=params_get, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        lrc = data.get("syncedLyrics") or data.get("plainLyrics", "")

                # Bersihkan judul secara umum (karena info dari YouTube sering kotor)
                clean_title = re.sub(r'[\(\[].*?[\)\]]', '', title)
                for kw in ['official', 'music video', 'lyric', 'lyrics', 'audio', 'video', 'mv', 'hq']:
                    clean_title = re.sub(rf'\b{kw}s?\b', '', clean_title, flags=re.IGNORECASE)
                clean_title = re.sub(r'\s+', ' ', clean_title).strip('- ')
                
                # Buat search query yang lebih bersih
                if "-" in title:
                    search_query = clean_title
                else:
                    search_query = f"{clean_title} {artist}" if artist and artist.lower() not in ["unknown", "topic"] else clean_title

                # 2. Jika gagal karena durasi tidak persis sama (sering terjadi di YouTube), gunakan fallback search
                if not lrc:
                    url_search = f"{LYRICS_API_BASE}/search"
                    params_search = {"q": search_query}
                    
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
                logger.info(f"syncedlyrics query: {search_query}")
                loop = asyncio.get_running_loop()
                try:
                    lrc = await asyncio.wait_for(loop.run_in_executor(None, syncedlyrics.search, search_query), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("syncedlyrics timeout (5.0s)")
                    lrc = None
            
            if self._current_generation == gen:
                if lrc:
                    self.lyrics_data = self._parse_lrc(lrc)
                    # LOW-07 fix: Store CLEAN lines (no timestamps) for display
                    self.state.lyrics_lines = [text for _, text in self.lyrics_data]
                    self.state.lyrics_timestamps = [t for t, _ in self.lyrics_data]
                    await self._bus.publish(LyricsUpdatedEvent())
                    logger.info(f"Lyrics: fetched {len(self.lyrics_data)} lines")
                else:
                    logger.info("Lyrics: No lyrics found anywhere")
                
        except Exception as e:
            if self._current_generation == gen:
                logger.debug(f"Lyrics fetch failed: {e}")
        finally:
            if self._current_generation == gen:
                self.state.lyrics_loading = False
                await self._bus.publish(LyricsUpdatedEvent())

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

    async def _on_progress(self, event: TrackProgressEvent):
        """Find the active lyric index based on current playback position."""
        position = event.position
        if not self.lyrics_data or not isinstance(position, (int, float)):
            return

        timestamps = getattr(self.state, "lyrics_timestamps", [])
        if not timestamps:
            timestamps = [t for t, _ in self.lyrics_data]
            self.state.lyrics_timestamps = timestamps
        adjusted_position = position + self.state.lyrics_offset
        active_idx = bisect.bisect_right(timestamps, adjusted_position) - 1
        active_idx = max(0, active_idx)
                
        if self.state.lyrics_index != active_idx:
            self.state.lyrics_index = active_idx
            await self._bus.publish(LyricsUpdatedEvent())
