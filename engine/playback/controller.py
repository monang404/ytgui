# PATCHLOG_APPLIED
"""
Purpose: Central controller for playback orchestration.
Subscribes to: TRACK_ENDED, TRACK_PROGRESS, CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK, CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE, "track.pause.changed"
Publishes: TRACK_STARTED, LOG_MESSAGE, QUEUE_UPDATED
"""

import asyncio
import structlog
from core.event_bus import EventBus
from core.events import (
    TrackEndedEvent, TrackProgressEvent, TrackStartedEvent,
    LogMessageEvent, QueueUpdatedEvent, TrackPauseChangedEvent,
    TrackDurationEvent
)
from core.state import AppState, PlayerStatus, PlaybackMode, AudioOutput, TrackInfo
from core.ports import AudioPlayerPort, LyricsProvider, SponsorBlockProvider
from cache.resolver import CacheResolver
from engine.queue_manager import QueueMode
from engine.radio_engine import RadioMode
from core.task_utils import safe_create_task
from engine.playback.track_loader import TrackLoader

logger = structlog.get_logger(__name__)
from core.log_config import STATS as _LOG_STATS


class PlaybackController:
    def __init__(
        self,
        bus: EventBus,
        state: AppState,
        mpv: AudioPlayerPort,
        resolver: CacheResolver,
        sponsorblock: SponsorBlockProvider,
        lyrics_fetcher: LyricsProvider,
        queue_mode: QueueMode,
        radio_mode: RadioMode
    ):
        self.bus = bus
        self.state = state
        self.mpv = mpv
        self.resolver = resolver
        self.queue_mode = queue_mode
        self.radio_mode = radio_mode
        self.track_loader = TrackLoader(resolver, sponsorblock, lyrics_fetcher)

        self._lock = asyncio.Lock()
        self._play_lock = asyncio.Lock()  # A-05: proteksi race condition di play_track
        self._retry_count = 0

        self.bus.subscribe(TrackEndedEvent, self._on_track_ended)
        self.bus.subscribe(TrackProgressEvent, self._on_track_progress)
        self.bus.subscribe(TrackPauseChangedEvent, self._on_pause_changed)
        self.bus.subscribe(TrackDurationEvent, self._on_track_duration)

    async def _on_track_duration(self, event: TrackDurationEvent):
        if event.duration and self.state.duration == 0:
            self.state.duration = event.duration
            if self.state.current_track:
                self.state.current_track.duration = int(event.duration)
                safe_create_task(self.resolver.db.upsert_track(self.state.current_track), name="upsert_track_duration")
            await self.bus.publish(QueueUpdatedEvent())

    async def play_track(self, track: TrackInfo):
        async with self._play_lock:  # A-05: cegah concurrent play_track race
            if self.state.current_track:
                self.state.history.append(self.state.current_track)

            self.state.current_track = track
            self.state.status = PlayerStatus.LOADING
            self.state.position = 0.0
            self.state.duration = float(track.duration)
            self.state.lyrics_lines = []
            self.state.lyrics_index = 0

            try:
                uri = await self.track_loader.load_track(track)

                await self.mpv.play(uri)

                if getattr(self.state, "audio_output", AudioOutput.DEVICE) == AudioOutput.BROWSER:
                    await self.mpv.set_volume(0)
                    await self.bus.publish(LogMessageEvent(message="Audio output is browser, mpv silent (volume=0)."))
                else:
                    await self.mpv.set_volume(self.state.volume)

                await self.mpv.resume()

                self.state.status = PlayerStatus.PLAYING
                self._retry_count = 0
                _LOG_STATS.is_playing = True
                _LOG_STATS.current_track = track.title[:50] if track and track.title else '—'
                _LOG_STATS.inc('songs_played')
                await self.bus.publish(TrackStartedEvent(track=track))

                if self.state.duration == 0:
                    safe_create_task(self._poll_duration(track), name="poll_duration")

            except Exception as e:
                logger.error(f"Failed to play track {track.title}: {e}", exc_info=True)
                self.state.status = PlayerStatus.ERROR
                self.state.error_msg = f"Error: {e}"
                await self.bus.publish(LogMessageEvent(message=f"Gagal memutar lagu: {track.title} | {type(e).__name__}: {str(e)}"))

                self._retry_count += 1
                if self._retry_count >= 3:
                    await self.bus.publish(LogMessageEvent(message="Terlalu banyak kegagalan beruntun. Pemutaran dihentikan."))
                    self._retry_count = 0
                else:
                    backoff = 2 ** self._retry_count
                    await asyncio.sleep(backoff)
                    if self.state.current_track == track:
                        await self._advance_to_next()

    async def _poll_duration(self, track: TrackInfo):
        await asyncio.sleep(2)
        if self.state.current_track != track:
            return
        dur = await self.mpv.get_duration()
        if dur > 0:
            self.state.duration = dur
            track.duration = int(dur)
            safe_create_task(self.resolver.db.upsert_track(track), name="upsert_track_duration_poll")
            await self.bus.publish(QueueUpdatedEvent())
        else:
            await asyncio.sleep(5)
            if self.state.current_track == track:
                dur = await self.mpv.get_duration()
                if dur > 0:
                    self.state.duration = dur
                    track.duration = int(dur)
                    safe_create_task(self.resolver.db.upsert_track(track), name="upsert_track_duration_poll")
                    await self.bus.publish(QueueUpdatedEvent())

    async def _on_cmd_play_track(self, track: TrackInfo):
        async with self._lock:
            if self.state.playback_mode == PlaybackMode.RADIO:
                await self.radio_mode.on_deactivated()
                self.state.playback_mode = PlaybackMode.QUEUE
                await self.bus.publish(QueueUpdatedEvent())
            await self.play_track(track)

    async def _on_track_ended(self, event: TrackEndedEvent):
        reason = event.reason
        logger.info(f"[AUTOPLAY] Track ended with reason: {reason}")

        next_data = {}
        if self.state.current_track:
            next_data["video_id"] = self.state.current_track.video_id

        if reason == "eof":
            await asyncio.sleep(0.35)
            await self._on_next(next_data)
        elif reason == "stop":
            # Abaikan event "stop" dari MPV karena ini otomatis terpanggil saat `loadfile` (ganti lagu).
            # State IDLE diset secara eksplisit di `_on_stop()` jika user/sistem benar-benar berhenti.
            pass
        elif reason == "error":
            self.state.status = PlayerStatus.ERROR
            await self.bus.publish(LogMessageEvent(message="Terjadi kesalahan pemutaran"))
            await asyncio.sleep(2)
            if self.state.status == PlayerStatus.IDLE:
                return
            current_vid = getattr(self.state.current_track, "video_id", None)
            if next_data.get("video_id") and current_vid != next_data["video_id"]:
                return
            await self._on_next(next_data)

    async def _on_track_progress(self, event: TrackProgressEvent):
        self.state.position = event.position
        if self.state.playback_mode == PlaybackMode.RADIO:
            self.radio_mode.check_prefetch(self, self.state.position, self.state.duration)

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
                await self.bus.publish(LogMessageEvent(message="Tidak ada lagu sebelumnya"))

    async def _on_stop(self, _data=None):
        self._retry_count = 0  # TASK-0.2: reset retry state agar tidak bocor ke lagu berikutnya
        await self.mpv.pause()
        self.state.status = PlayerStatus.IDLE
        _LOG_STATS.is_playing = False
        self.state.current_track = None
        self.state.queue.clear()
        self.state.radio_queue.clear()
        self.state.position = 0.0
        self.state.lyrics_lines = []
        self.state.lyrics_index = 0
        await self.bus.publish(LogMessageEvent(message="Pemutaran dihentikan"))
        await self.bus.publish(QueueUpdatedEvent())

    async def _on_seek(self, position: float):
        if self.state.status in (PlayerStatus.PLAYING, PlayerStatus.PAUSED):
            await self.mpv.seek(position)
            self.state.position = position

    async def _on_set_mode(self, mode: PlaybackMode):
        should_activate_radio = False
        async with self._lock:
            if self.state.playback_mode != mode:
                previous_mode = self.state.playback_mode
                self.state.playback_mode = mode

                if previous_mode == PlaybackMode.RADIO:
                    await self.radio_mode.on_deactivated()
                    await self.mpv.pause()
                    self.state.current_track = None
                    self.state.status = PlayerStatus.IDLE
                    _LOG_STATS.is_playing = False

                if mode == PlaybackMode.RADIO:
                    self.state.status = PlayerStatus.LOADING
                    should_activate_radio = True

                await self.bus.publish(LogMessageEvent(message=f"Mode diubah ke {mode.name}"))
                await self.bus.publish(QueueUpdatedEvent())

        if should_activate_radio:
            await self.radio_mode.on_activated(self)

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
                await self.bus.publish(QueueUpdatedEvent())
                await self.bus.publish(LogMessageEvent(message=f"Dihapus dari antrean: {removed.title}"))

    async def _on_queue_add(self, track: TrackInfo):
        async with self._lock:
            self.state.queue.append(track)
            await self.bus.publish(QueueUpdatedEvent())
            await self.bus.publish(LogMessageEvent(message=f"Ditambahkan ke antrean: {track.title}"))

    async def _on_queue_replace(self, tracks: list[TrackInfo]):
        async with self._lock:
            self.state.queue.clear()
            self.state.queue.extend(tracks)
            await self.bus.publish(QueueUpdatedEvent())

    async def _on_queue_reorder(self, data: dict):
        async with self._lock:
            from_index = data.get("from_index")
            to_index = data.get("to_index")
            q = self.state.queue
            if from_index is not None and to_index is not None:
                if 0 <= from_index < len(q) and 0 <= to_index < len(q):
                    item = q[from_index]
                    del q[from_index]
                    q.insert(to_index, item)
                    await self.bus.publish(QueueUpdatedEvent())

    async def _on_radio_randomize(self, data=None):
        seed = None
        should_fetch = False
        async with self._lock:
            if self.state.playback_mode == PlaybackMode.RADIO:
                seed = data.get("seed_artist") if data else None
                self.state.radio_queue.clear()
                await self.mpv.pause()
                self.state.current_track = None
                self.state.status = PlayerStatus.LOADING
                self.state.position = 0.0
                self.radio_mode._artist_rotation = []
                await self.bus.publish(QueueUpdatedEvent())
                await self.bus.publish(LogMessageEvent(message="Mengacak ulang stasiun radio..."))
                should_fetch = True
            else:
                await self.bus.publish(LogMessageEvent(message="Radio tidak aktif"))

        if should_fetch:
            from core.task_utils import safe_create_task
            safe_create_task(
                self.radio_mode._fetch_and_play_initial(self, seed_artist=seed),
                name="radio_randomize_fetch"
            )

    async def _on_pause_changed(self, event: TrackPauseChangedEvent):
        if event.is_paused:
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
        await self.bus.publish(LogMessageEvent(message=f"Output suara diubah ke: {'Browser' if output == AudioOutput.BROWSER else 'HP'}"))
        await self.bus.publish(QueueUpdatedEvent())

    async def _on_set_sponsorblock(self, enabled: bool):
        self.state.sponsorblock_active = enabled
        await self.bus.publish(LogMessageEvent(message=f"SponsorBlock: {'ON' if enabled else 'OFF'}"))
        await self.bus.publish(QueueUpdatedEvent())

    async def _on_lyrics_offset(self, data: dict):
        offset = data.get("offset", 0.0)
        self.state.lyrics_offset = float(offset)
        from core.events import LyricsUpdatedEvent
        await self.bus.publish(LyricsUpdatedEvent())
