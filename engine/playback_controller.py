"""
Purpose: Central controller for playback orchestration.
Subscribes to: TRACK_ENDED, TRACK_PROGRESS, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE, "track.pause.changed"
Publishes: TRACK_STARTED, LOG_MESSAGE, QUEUE_UPDATED
"""

import asyncio
import logging
from core.event_bus import (
    EventBus, TRACK_ENDED, TRACK_PROGRESS, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_SET_MODE, CMD_QUEUE_SELECT,
    CMD_QUEUE_REMOVE, TRACK_STARTED, LOG_MESSAGE, QUEUE_UPDATED
)
from core.state import AppState, PlayerStatus, PlaybackMode, TrackInfo
from engine.mpv_controller import MpvController
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.queue_mode import QueueMode
from engine.radio_mode import RadioMode

logger = logging.getLogger(__name__)

class PlaybackController:
    def __init__(
        self,
        bus: EventBus,
        state: AppState,
        mpv: MpvController,
        resolver: CacheResolver,
        sponsorblock: SponsorBlockHandler,
        lyrics_fetcher: LyricsFetcher,
        queue_mode: QueueMode,
        radio_mode: RadioMode
    ):
        self.bus = bus
        self.state = state
        self.mpv = mpv
        self.resolver = resolver
        self.sponsorblock = sponsorblock
        self.lyrics_fetcher = lyrics_fetcher
        self.queue_mode = queue_mode
        self.radio_mode = radio_mode

        # Subscribe
        self.bus.subscribe(TRACK_ENDED, self._on_track_ended)
        self.bus.subscribe(TRACK_PROGRESS, self._on_track_progress)
        self.bus.subscribe(CMD_PLAY_TRACK, self._on_cmd_play_track)
        self.bus.subscribe(CMD_TOGGLE_PAUSE, self._on_cmd_toggle_pause)
        self.bus.subscribe(CMD_NEXT, self._on_next)
        self.bus.subscribe(CMD_PREV, self._on_prev)
        self.bus.subscribe(CMD_STOP, self._on_stop)
        self.bus.subscribe(CMD_SEEK, self._on_seek)
        self.bus.subscribe(CMD_SET_MODE, self._on_set_mode)
        self.bus.subscribe(CMD_QUEUE_SELECT, self._on_queue_select)
        self.bus.subscribe(CMD_QUEUE_REMOVE, self._on_queue_remove)
        self.bus.subscribe("track.pause.changed", self._on_pause_changed)

    async def play_track(self, track: TrackInfo):
        # Push current to history if it exists
        if self.state.current_track:
            self.state.history.append(self.state.current_track)
            if len(self.state.history) > 50:
                self.state.history.pop(0)

        self.state.current_track = track
        self.state.status = PlayerStatus.LOADING
        self.state.position = 0.0
        self.state.duration = float(track.duration)
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0

        try:
            # Resolve URI
            uri = await self.resolver.resolve(track)
            
            # Play
            await self.mpv.play(uri)
            
            self.state.status = PlayerStatus.PLAYING
            await self.bus.publish(TRACK_STARTED, track)
            
            # Fetch sponsorblock and lyrics
            asyncio.create_task(self.sponsorblock.fetch_segments(track.video_id))
            asyncio.create_task(self.lyrics_fetcher.fetch(track))
            
        except Exception as e:
            logger.error(f"Failed to play track {track.title}: {e}", exc_info=True)
            self.state.status = PlayerStatus.ERROR
            self.state.error_msg = f"Error: {e}"
            await self.bus.publish(LOG_MESSAGE, f"Gagal memutar lagu: {track.title} | {type(e).__name__}: {str(e)}")
            await asyncio.sleep(2)
            await self._on_next()

    async def _on_cmd_play_track(self, track: TrackInfo):
        await self.play_track(track)

    async def _on_track_ended(self, data: dict):
        reason = data.get("reason")
        if reason == "eof":
            await self._on_next()
        elif reason == "error":
            self.state.status = PlayerStatus.ERROR
            await self.bus.publish(LOG_MESSAGE, "Terjadi kesalahan pemutaran")
            await asyncio.sleep(2)
            await self._on_next()

    async def _on_track_progress(self, position: float):
        self.state.position = position

    async def _on_cmd_toggle_pause(self, _data=None):
        if self.state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED):
            await self.mpv.toggle_pause()

    async def _on_next(self, _data=None):
        if self.state.playback_mode == PlaybackMode.QUEUE:
            await self.queue_mode.next(self)
        else:
            await self.radio_mode.next(self)

    async def _on_prev(self, _data=None):
        if self.state.history:
            track = self.state.history.pop()
            # To avoid adding it back to history again when play_track is called,
            # we temporarily clear current_track, or just let play_track handle it
            # and clean up history later. But the simplest is to pop current, 
            # set current to None, then play.
            self.state.current_track = None 
            await self.play_track(track)
            # Remove the last appended item which was the None or the previous current_track
            # Actually, play_track pushes `current_track` to history. 
            # By setting it to None before calling, we avoid pushing None.
        else:
            await self.bus.publish(LOG_MESSAGE, "Tidak ada lagu sebelumnya")

    async def _on_stop(self, _data=None):
        await self.mpv.pause()
        self.state.status = PlayerStatus.IDLE
        self.state.current_track = None
        self.state.queue.clear()
        self.state.position = 0.0
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        await self.bus.publish(LOG_MESSAGE, "Pemutaran dihentikan")
        await self.bus.publish(QUEUE_UPDATED)

    async def _on_seek(self, position: float):
        if self.state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED):
            await self.mpv.seek(position)
            self.state.position = position

    async def _on_set_mode(self, mode: PlaybackMode):
        if self.state.playback_mode != mode:
            self.state.playback_mode = mode
            if mode == PlaybackMode.RADIO:
                await self.radio_mode.on_activated(self)
            await self.bus.publish(LOG_MESSAGE, f"Mode diubah ke {mode.name}")
            await self.bus.publish(QUEUE_UPDATED)

    async def _on_queue_select(self, index: int):
        if 0 <= index < len(self.state.queue):
            track = self.state.queue[index]
            self.state.queue = self.state.queue[index+1:]
            await self.play_track(track)

    async def _on_queue_remove(self, index: int):
        if 0 <= index < len(self.state.queue):
            removed = self.state.queue.pop(index)
            await self.bus.publish(QUEUE_UPDATED)
            await self.bus.publish(LOG_MESSAGE, f"Dihapus dari antrean: {removed.title}")

    async def _on_pause_changed(self, paused: bool):
        if paused:
            if self.state.status == PlayerStatus.PLAYING:
                self.state.status = PlayerStatus.PAUSED
        else:
            if self.state.status == PlayerStatus.PAUSED:
                self.state.status = PlayerStatus.PLAYING
