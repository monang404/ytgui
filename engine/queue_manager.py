import asyncio
from core.state import AppState, PlayerStatus, TrackInfo
from core.event_bus import (
    bus, TRACK_ENDED, TRACK_STARTED, QUEUE_UPDATED, QUEUE_EMPTY,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_TOGGLE_PAUSE, SEARCH_RESULTS,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_LYRICS,
    LOG_MESSAGE, TRACK_PROGRESS, DOWNLOAD_PROGRESS, DOWNLOAD_COMPLETE
)
from engine.mpv_controller import MpvController
from engine.ytdlp_client import YtDlpClient
from cache.db import Database
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher

class QueueManager:
    """
    The orchestrator. Manages queue, playback commands, volume,
    download, and previous track navigation.
    
    HIGH-06 fix: CMD_PREV implemented with history tracking.
    HIGH-07 fix: CMD_VOLUME_UP/DOWN implemented.
    HIGH-08 fix: CMD_DOWNLOAD implemented.
    LOW-05 fix: CMD_TOGGLE_LYRICS implemented.
    """
    def __init__(self, state: AppState, mpv: MpvController, ytdlp: YtDlpClient,
                 db: Database, resolver: CacheResolver, 
                 sponsorblock: SponsorBlockHandler, lyrics_fetcher: LyricsFetcher):
        self.state = state
        self.mpv = mpv
        self.ytdlp = ytdlp
        self.db = db
        self.resolver = resolver
        self.sponsorblock = sponsorblock
        self.lyrics_fetcher = lyrics_fetcher

        # Subscriptions
        bus.subscribe(TRACK_ENDED, self._on_track_ended)
        bus.subscribe(TRACK_PROGRESS, self._on_progress)
        bus.subscribe(CMD_NEXT, self.play_next)
        bus.subscribe(CMD_PREV, self.play_prev)
        bus.subscribe(CMD_STOP, self.stop)
        bus.subscribe(SEARCH_RESULTS, self._on_search_results)
        bus.subscribe(CMD_TOGGLE_PAUSE, self._on_toggle_pause)
        bus.subscribe(CMD_VOLUME_UP, self._on_volume_up)
        bus.subscribe(CMD_VOLUME_DOWN, self._on_volume_down)
        bus.subscribe(CMD_DOWNLOAD, self._on_download)
        bus.subscribe(CMD_TOGGLE_LYRICS, self._on_toggle_lyrics)

    async def play_next(self, _=None):
        """Plays the next track in the queue."""
        # Push current track to history before advancing
        if self.state.current_track:
            self.state.history.append(self.state.current_track)
            # Keep history bounded
            if len(self.state.history) > 50:
                self.state.history.pop(0)

        if not self.state.queue:
            await self.stop()
            await bus.publish(QUEUE_EMPTY)
            return

        next_track = self.state.queue.pop(0)
        await self.play_track(next_track)

    async def play_prev(self, _=None):
        """HIGH-06 fix: Plays the previous track from history."""
        if not self.state.history:
            await bus.publish(LOG_MESSAGE, "No previous track.")
            return
        
        # Push current track back to front of queue
        if self.state.current_track:
            self.state.queue.insert(0, self.state.current_track)
        
        prev_track = self.state.history.pop()
        await self.play_track(prev_track)

    async def play_track(self, track: TrackInfo):
        self.state.current_track = track
        self.state.status = PlayerStatus.LOADING
        self.state.position = 0.0
        self.state.next_uri_ready = None
        await bus.publish(QUEUE_UPDATED)
        await bus.publish(LOG_MESSAGE, f"Resolving: {track.title}...")

        try:
            # 1. Resolve URI (Local or Stream)
            uri = await self.resolver.resolve(track)
            
            # 2. Play on mpv
            await self.mpv.play(uri)
            self.state.status = PlayerStatus.PLAYING
            await bus.publish(TRACK_STARTED, track)
            await bus.publish(LOG_MESSAGE, f"Playing: {track.title}")

            # 3. Record play count (MED-10 fix: only on actual play)
            await self.db.increment_play_count(track.video_id)

            # 4. Fire & Forget Integrations
            asyncio.create_task(self.sponsorblock.fetch_segments(track.video_id))
            asyncio.create_task(self.lyrics_fetcher.fetch(track.title, track.artist, track.duration))

        except Exception as e:
            self.state.status = PlayerStatus.ERROR
            await bus.publish(LOG_MESSAGE, f"Error playing: {e}")
            await asyncio.sleep(2)
            await self.play_next()

    async def stop(self, _=None):
        self.state.current_track = None
        self.state.queue.clear()
        self.state.status = PlayerStatus.IDLE
        self.state.position = 0.0
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        await self.mpv.pause()
        await bus.publish(QUEUE_UPDATED)
        await bus.publish(LOG_MESSAGE, "Stopped.")

    async def _on_track_ended(self, data: dict):
        if data.get("reason") in ("eof", "stop"):
            await self.play_next()

    async def _on_progress(self, position: float):
        self.state.position = position

    async def _on_search_results(self, results: list[TrackInfo]):
        """When user searches, clear queue and play the first result."""
        if results:
            self.state.queue = list(results[1:])
            await self.play_track(results[0])

    async def _on_toggle_pause(self, _=None):
        await self.mpv.toggle_pause()
        if self.state.status == PlayerStatus.PLAYING:
            self.state.status = PlayerStatus.PAUSED
        elif self.state.status == PlayerStatus.PAUSED:
            self.state.status = PlayerStatus.PLAYING

    async def _on_volume_up(self, _=None):
        """HIGH-07 fix: Volume control."""
        self.state.volume = min(150, self.state.volume + 5)
        await self.mpv.set_volume(self.state.volume)
        await bus.publish(LOG_MESSAGE, f"Volume: {self.state.volume}%")

    async def _on_volume_down(self, _=None):
        """HIGH-07 fix: Volume control."""
        self.state.volume = max(0, self.state.volume - 5)
        await self.mpv.set_volume(self.state.volume)
        await bus.publish(LOG_MESSAGE, f"Volume: {self.state.volume}%")

    async def _on_download(self, _=None):
        """HIGH-08 fix: Download current track to local cache."""
        if not self.state.current_track:
            await bus.publish(LOG_MESSAGE, "No track to download.")
            return
        
        track = self.state.current_track
        if track.local_path:
            await bus.publish(LOG_MESSAGE, f"Already cached: {track.title}")
            return

        await bus.publish(LOG_MESSAGE, f"Downloading: {track.title}...")
        try:
            local_path = await self.ytdlp.download_mp3(track.video_id)
            track.local_path = local_path
            await self.db.upsert_track(track, local_path=local_path)
            await bus.publish(LOG_MESSAGE, f"Downloaded: {track.title}")
            await bus.publish(DOWNLOAD_COMPLETE, track)
        except Exception as e:
            await bus.publish(LOG_MESSAGE, f"Download failed: {e}")

    async def _on_toggle_lyrics(self, _=None):
        """LOW-05 fix: Toggle lyrics display."""
        self.state.show_lyrics = not self.state.show_lyrics
        status = "ON" if self.state.show_lyrics else "OFF"
        await bus.publish(LOG_MESSAGE, f"Lyrics: {status}")
