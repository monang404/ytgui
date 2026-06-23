"""
Purpose: Central controller for playback orchestration.
Subscribes to: TRACK_ENDED, TRACK_PROGRESS, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE, "track.pause.changed"
Publishes: TRACK_STARTED, LOG_MESSAGE, QUEUE_UPDATED
"""

import asyncio
import structlog
from core.event_bus import (
    EventBus, TRACK_ENDED, TRACK_PROGRESS, TRACK_STARTED, LOG_MESSAGE, QUEUE_UPDATED
)
from core.command_bus import (
    command_bus, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE,
    CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_SET_MODE, CMD_QUEUE_SELECT,
    CMD_QUEUE_REMOVE, CMD_QUEUE_ADD, CMD_RADIO_RANDOMIZE, CMD_SET_OUTPUT
)
from core.state import AppState, PlayerStatus, PlaybackMode, AudioOutput, TrackInfo
from core.ports import AudioPlayerPort
from cache.resolver import CacheResolver
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.queue_mode import QueueMode
from engine.radio_mode import RadioMode
from core.task_utils import safe_create_task

logger = structlog.get_logger(__name__)

class PlaybackController:
    def __init__(
        self,
        bus: EventBus,
        state: AppState,
        mpv: AudioPlayerPort,
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

        self._lock = asyncio.Lock()
        self._retry_count = 0

        # Subscribe
        # Subscribe events
        self.bus.subscribe(TRACK_ENDED, self._on_track_ended)
        self.bus.subscribe(TRACK_PROGRESS, self._on_track_progress)

        # Register commands
        command_bus.register(CMD_PLAY_TRACK, self._on_cmd_play_track)
        command_bus.register(CMD_TOGGLE_PAUSE, self._on_cmd_toggle_pause)
        command_bus.register(CMD_NEXT, self._on_next)
        command_bus.register(CMD_PREV, self._on_prev)
        command_bus.register(CMD_STOP, self._on_stop)
        command_bus.register(CMD_SEEK, self._on_seek)
        command_bus.register(CMD_SET_MODE, self._on_set_mode)
        command_bus.register(CMD_QUEUE_SELECT, self._on_queue_select)
        command_bus.register(CMD_QUEUE_REMOVE, self._on_queue_remove)
        command_bus.register(CMD_QUEUE_ADD, self._on_queue_add)
        command_bus.register(CMD_RADIO_RANDOMIZE, self._on_radio_randomize)
        command_bus.register(CMD_SET_OUTPUT, self._on_set_output)
        self.bus.subscribe("track.pause.changed", self._on_pause_changed)

    async def play_track(self, track: TrackInfo):
        # Push current to history if it exists
        if self.state.current_track:
            self.state.history.append(self.state.current_track)

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
            
            if getattr(self.state, "audio_output", AudioOutput.DEVICE) == AudioOutput.BROWSER:
                await self.bus.publish(LOG_MESSAGE, "Audio output is browser, skipping mpv local playback.")
            else:
                await self.mpv.set_volume(self.state.volume)
                
            await self.mpv.resume()
            
            self.state.status = PlayerStatus.PLAYING
            self._retry_count = 0  # Reset retry count on success
            await self.bus.publish(TRACK_STARTED, track)
            
            # C-02: Increment play count for favorites
            await self.resolver.db.increment_play_count(track.video_id)
            
            # Fetch sponsorblock and lyrics
            safe_create_task(self.sponsorblock.fetch_segments(track.video_id), name="fetch_sponsorblock")
            safe_create_task(self.lyrics_fetcher.fetch(track), name="fetch_lyrics")
            
        except Exception as e:
            logger.error(f"Failed to play track {track.title}: {e}", exc_info=True)
            self.state.status = PlayerStatus.ERROR
            self.state.error_msg = f"Error: {e}"
            await self.bus.publish(LOG_MESSAGE, f"Gagal memutar lagu: {track.title} | {type(e).__name__}: {str(e)}")
            
            self._retry_count += 1
            if self._retry_count >= 3:
                await self.bus.publish(LOG_MESSAGE, "Terlalu banyak kegagalan beruntun. Pemutaran dihentikan.")
                self._retry_count = 0
            else:
                backoff = 2 ** self._retry_count
                await asyncio.sleep(backoff)
                # Ensure we don't call _on_next if we are no longer trying to play this track
                if self.state.current_track == track:
                    await self._advance_to_next()

    async def _on_cmd_play_track(self, track: TrackInfo):
        async with self._lock:
            await self.play_track(track)

    async def _on_track_ended(self, data: dict):
        reason = data.get("reason")
        
        # Build payload for next to prevent double-skip if track changes concurrently
        next_data = {}
        if self.state.current_track:
            next_data["video_id"] = self.state.current_track.video_id

        if reason == "eof":
            await self._on_next(next_data)
        elif reason == "error":
            self.state.status = PlayerStatus.ERROR
            await self.bus.publish(LOG_MESSAGE, "Terjadi kesalahan pemutaran")
            await asyncio.sleep(2)
            await self._on_next(next_data)

    async def _on_track_progress(self, position: float):
        self.state.position = position

    async def _on_cmd_toggle_pause(self, _data=None):
        if self.state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED):
            await self.mpv.toggle_pause()

    async def _on_next(self, data=None):
        async with self._lock:
            if data and isinstance(data, dict) and "video_id" in data:
                if not self.state.current_track or self.state.current_track.video_id != data["video_id"]:
                    logger.info(f"Ignoring skip: requested {data['video_id']} != current {getattr(self.state.current_track, 'video_id', None)}")
                    return
            await self._advance_to_next()

    async def _advance_to_next(self):
        if self.state.playback_mode == PlaybackMode.QUEUE:
            await self.queue_mode.next(self)
        else:
            await self.radio_mode.next(self)

    async def _on_prev(self, _data=None):
        async with self._lock:
            if self.state.history:
                track = self.state.history.pop()
                self.state.current_track = None 
                await self.play_track(track)
            else:
                await self.bus.publish(LOG_MESSAGE, "Tidak ada lagu sebelumnya")

    async def _on_stop(self, _data=None):
        await self.mpv.pause()
        self.state.status = PlayerStatus.IDLE
        self.state.current_track = None
        self.state.queue.clear()
        self.state.radio_queue.clear()
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
            previous_mode = self.state.playback_mode
            self.state.playback_mode = mode
            if previous_mode == PlaybackMode.RADIO:
                await self.radio_mode.on_deactivated()
            if mode == PlaybackMode.RADIO:
                await self.radio_mode.on_activated(self)
            await self.bus.publish(LOG_MESSAGE, f"Mode diubah ke {mode.name}")
            await self.bus.publish(QUEUE_UPDATED)

    async def _on_queue_select(self, index: int):
        async with self._lock:
            if 0 <= index < len(self.state.queue):
                track = self.state.queue[index]
                for _ in range(index + 1):
                    self.state.queue.popleft()
                await self.play_track(track)

    async def _on_queue_remove(self, index: int):
        async with self._lock:
            if 0 <= index < len(self.state.queue):
                removed = self.state.queue[index]
                del self.state.queue[index]
                await self.bus.publish(QUEUE_UPDATED)
                await self.bus.publish(LOG_MESSAGE, f"Dihapus dari antrean: {removed.title}")

    async def _on_queue_add(self, track: TrackInfo):
        self.state.queue.append(track)
        await self.bus.publish(QUEUE_UPDATED)
        await self.bus.publish(LOG_MESSAGE, f"Ditambahkan ke antrean: {track.title}")

    async def _on_radio_randomize(self, _data=None):
        async with self._lock:
            if self.state.playback_mode == PlaybackMode.RADIO:
                self.state.radio_queue.clear()
                
                # Stop playing current track immediately to give instant "reset" feel
                await self.mpv.pause()
                self.state.current_track = None
                self.state.status = PlayerStatus.LOADING
                self.state.position = 0.0
                await self.bus.publish(QUEUE_UPDATED)
                
                await self.bus.publish(LOG_MESSAGE, "Mengacak ulang stasiun radio...")
                # Panggil fetch dengan seed=None agar memaksa penggunaan seed acak dari list
                await self.radio_mode._fetch_and_play_initial(self, seed_artist=None)
            else:
                await self.bus.publish(LOG_MESSAGE, "Radio tidak aktif")

    async def _on_pause_changed(self, paused: bool):
        if paused:
            if self.state.status == PlayerStatus.PLAYING:
                self.state.status = PlayerStatus.PAUSED
        else:
            if self.state.status == PlayerStatus.PAUSED:
                self.state.status = PlayerStatus.PLAYING

    async def _on_set_output(self, output: AudioOutput):
        """Ubah mode output (device / browser)"""
        self.state.audio_output = output
        if output == AudioOutput.BROWSER:
            await self.mpv.set_volume(0)
        else:
            await self.mpv.set_volume(self.state.volume)
        await self.bus.publish(LOG_MESSAGE, f"Output suara diubah ke: {'Browser' if output == AudioOutput.BROWSER else 'HP'}")
        await self.bus.publish(QUEUE_UPDATED)
