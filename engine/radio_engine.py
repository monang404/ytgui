"""
Purpose: Mengelola pemutaran lagu secara otomatis dan berkelanjutan (Radio Mode).
Radio Mode adalah fitur independen: ia memiliki list lagu sendiri
(state.radio_queue) dan TIDAK PERNAH membaca atau menulis state.queue
(milik Queue Mode). Lihat Constitution: "Radio must work independently
from queue" dan "Radio must NEVER depend on Queue Empty events."
Subscribes to: (tidak ada)
Publishes: QUEUE_UPDATED, LOG_MESSAGE
"""

import asyncio
import random
import re
import logging
from typing import TYPE_CHECKING, Optional

from core.events import QueueUpdatedEvent, LogMessageEvent


if TYPE_CHECKING:
    from engine.playback import PlaybackController
from core.state import AppState, PlaybackMode, PlayerStatus
from core.ports import MediaExtractorPort
from core.task_utils import safe_create_task

_log = logging.getLogger(__name__)

MAX_TRACK_DURATION = 600
TRACKS_PER_ARTIST_TARGET = 3
ARTISTS_PER_BATCH = 4
ARTISTS_QUICK = 2
SEED_LIMIT = 2

_TITLE_NOISE_WORDS = frozenset({
    "official", "music", "video", "audio", "lyric", "lyrics", "mv",
    "cover", "live", "performance", "hd", "hq", "remastered", "remaster",
    "full", "version", "ver", "feat", "ft", "original", "soundtrack",
    "ost", "karaoke", "instrumental", "acoustic", "akustik", "konser",
})





def _track_task(task_set: set, coro, name: str):
    task = safe_create_task(coro, name=name)
    task.add_done_callback(task_set.discard)
    task_set.add(task)
    if task.done():
        task_set.discard(task)
    return task


class RadioMode:
    """
    Strategi pre-fetch agresif:
    - _standby: playlist cadangan 12 lagu yang disiapkan di background
    - Radio ON / klik Acak:
        1. Kalau _standby sudah ada → pakai langsung (0 detik)
        2. Kalau belum → fetch cepat 2 artis dulu (~5 detik), langsung putar,
           lalu background fetch 2 artis lagi untuk genapi 12
    - Begitu _standby dipakai, langsung siapkan cadangan baru di background
    - Saat queue tinggal ≤ 5 lagu → prefetch otomatis ke _standby
    """

    def __init__(self, ytdlp: MediaExtractorPort, state: AppState, db=None):
        self.ytdlp = ytdlp
        self.state = state
        self.db = db
        self._fetch_lock = asyncio.Lock()
        self._bg_tasks: set = set()
        self._seed_artists: list[str] = []
        self._artist_rotation: list[str] = []
        self._standby: list = []
        self._standby_lock = asyncio.Lock()
        self._prefetch_started = False


    async def _ensure_artists_loaded(self) -> None:
        if self._seed_artists:
            return
        try:
            if self.db and self.db.conn:
                self._seed_artists = await self.db.get_all_artists()
        except Exception as e:
            _log.warning(f"Gagal load artis dari DB: {e}")

        if not self._seed_artists:
            raise RuntimeError(
                "Tabel artists kosong. Jalankan: python data/import_artists.py "
                "--db data/ytgui.db --json data/artists.json"
            )


    async def on_activated(self, controller: "PlaybackController") -> None:
        try:
            await self._ensure_artists_loaded()
        except RuntimeError as e:
            await controller.bus.publish(LogMessageEvent(
                message=f"Radio: {e}"
            ))
            return
        self.state.radio_queue.clear()
        self._artist_rotation = []
        _track_task(self._bg_tasks, self._start(controller), name="radio_start")

    async def on_deactivated(self) -> None:
        self.state.radio_queue.clear()
        for task in list(self._bg_tasks):
            task.cancel()
        self._bg_tasks.clear()


    async def next(self, controller: "PlaybackController") -> None:
        if self.state.radio_queue:
            track = self.state.radio_queue.popleft()
            if len(self.state.radio_queue) <= 5:
                _track_task(self._bg_tasks, self._ensure_standby(controller), name="radio_ensure_standby")
            await controller.play_track(track)
        else:
            # PATCH-RADIO-EMPTY-QUEUE-01: Queue habis — _start() jalan di background (bisa
            self.state.status = PlayerStatus.LOADING
            await controller.bus.publish(QueueUpdatedEvent())
            _track_task(self._bg_tasks, self._start(controller), name="radio_refill")


    async def _start(self, controller: "PlaybackController") -> None:
        """
        Urutan prioritas:
        1. Standby sudah ada → pakai langsung (instan)
        2. Belum ada → fetch cepat ARTISTS_QUICK artis, putar segera,
           lalu background fetch sisa untuk genapi dan isi standby berikutnya
        """
        async with self._standby_lock:
            if self._standby:
                tracks = self._standby
                self._standby = []
            else:
                tracks = None

        if tracks:
            self.state.radio_queue.clear()
            self.state.radio_queue.extend(tracks[1:])
            await controller.bus.publish(QueueUpdatedEvent())
            await controller.play_track(tracks[0])
            _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby")
            return

        try:
            quick_tracks = await asyncio.wait_for(
                self._gather_batch(max_artists=ARTISTS_QUICK),
                timeout=20.0
            )
        except RuntimeError as e:
            await controller.bus.publish(QueueUpdatedEvent())
            await controller.bus.publish(LogMessageEvent(
                message=f"Radio: {e}"
            ))
            return
        except (asyncio.TimeoutError, Exception):
            quick_tracks = []

        if quick_tracks:
            self.state.radio_queue.clear()
            self.state.radio_queue.extend(quick_tracks[1:])
            await controller.bus.publish(QueueUpdatedEvent())
            await controller.play_track(quick_tracks[0])
            _track_task(self._bg_tasks, self._backfill_and_standby(controller), name="radio_backfill")
        else:
            await controller.bus.publish(QueueUpdatedEvent())
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Tidak ada hasil ditemukan."
            ))

    async def _backfill_and_standby(self, controller: "PlaybackController") -> None:
        """Fetch sisa artis (ARTISTS_PER_BATCH - ARTISTS_QUICK) lalu
        tambahkan ke queue yang sedang berjalan. Setelah itu siapkan standby."""
        if self._fetch_lock.locked():
            return
        async with self._fetch_lock:
            try:
                extra = await asyncio.wait_for(
                    self._gather_batch(max_artists=ARTISTS_PER_BATCH - ARTISTS_QUICK),
                    timeout=30.0
                )
                if extra:
                    self.state.radio_queue.extend(extra)
                    while len(self.state.radio_queue) > 30:
                        self.state.radio_queue.pop()
                    await controller.bus.publish(QueueUpdatedEvent())
            except Exception as e:
                _log.warning(f"Radio backfill gagal: {e}")

        _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby")

    async def _build_standby(self, controller: "PlaybackController") -> None:
        """Siapkan playlist cadangan 12 lagu di background.
        Tidak akan jalan kalau standby sudah ada atau sedang dibangun."""
        async with self._standby_lock:
            if self._standby:
                return

        if self._fetch_lock.locked():
            return
        async with self._fetch_lock:
            try:
                tracks = await asyncio.wait_for(
                    self._gather_batch(max_artists=ARTISTS_PER_BATCH),
                    timeout=30.0
                )
                if tracks:
                    async with self._standby_lock:
                        self._standby = tracks
            except Exception as e:
                _log.warning(f"Radio build_standby gagal: {e}")

    async def _ensure_standby(self, controller: "PlaybackController") -> None:
        """Pastikan standby sedang disiapkan kalau belum ada."""
        async with self._standby_lock:
            if self._standby:
                return
        _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby2")


    async def _fetch_and_play_initial(
        self, controller: "PlaybackController", seed_artist: Optional[str] = None
    ) -> None:
        """Entry point untuk tombol Acak.
        Fetch FULL batch 4 artis sekaligus (bukan quick 2 dulu),
        agar dari awal langsung dapat 4 artis berbeda × 3 lagu = 12 lagu.
        _start() tetap pakai quick batch untuk auto-refill saat queue habis.
        """
        self._artist_rotation = []
        async with self._standby_lock:
            self._standby = []

        await controller.bus.publish(LogMessageEvent(
            message="Mengacak playlist radio..."
        ))

        try:
            tracks = await asyncio.wait_for(
                self._gather_batch(
                    prioritized_artist=seed_artist,
                    max_artists=ARTISTS_PER_BATCH
                ),
                timeout=40.0
            )
        except RuntimeError as e:
            await controller.bus.publish(LogMessageEvent(
                message=f"Radio: {e}"
            ))
            return
        except asyncio.TimeoutError:
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Timeout saat mengambil lagu. Coba lagi."
            ))
            return
        except Exception as e:
            _log.warning(f"Radio randomize gagal: {e}")
            return

        if not tracks:
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Tidak ada hasil ditemukan."
            ))
            return

        self.state.radio_queue.clear()
        self.state.radio_queue.extend(tracks[1:])
        await controller.bus.publish(QueueUpdatedEvent())
        await controller.play_track(tracks[0])

        _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby")


    async def _gather_batch(
        self, prioritized_artist: Optional[str] = None, max_artists: int = ARTISTS_PER_BATCH
    ) -> list:
        limit = max_artists * TRACKS_PER_ARTIST_TARGET
        existing = self._build_exclusion_set()

        if not prioritized_artist and self._seed_artists:
            prioritized_artist = random.choice(self._seed_artists)

        if self.db and self.db.conn:
            try:
                tracks = await self.db.get_random_songs(limit=limit, exclude_ids=existing, artist=prioritized_artist)
                return tracks
            except Exception as e:
                _log.warning(f"Gagal mengambil lagu acak dari DB: {e}")
        return []

    def _build_exclusion_set(self) -> set[str]:
        ids = {t.video_id for t in self.state.radio_queue}
        if self.state.current_track:
            ids.add(self.state.current_track.video_id)
        for t in list(self.state.history)[-20:]:
            ids.add(t.video_id)
        return ids

    def check_prefetch(self, controller: "PlaybackController", position: float, duration: float) -> None:
        """Trigger prefetch stream_url untuk lagu berikutnya jika waktu tersisa <= 30 detik."""
        if duration > 0 and (duration - position) <= 30.0:
            current_vid = self.state.current_track.video_id if self.state.current_track else None
            if current_vid and getattr(self, '_last_prefetch_vid', None) != current_vid:
                self._last_prefetch_vid = current_vid
                _track_task(self._bg_tasks, self._prefetch_next(controller), name="radio_prefetch")

    async def _prefetch_next(self, controller: "PlaybackController") -> None:
        """Resolve stream_url untuk lagu pertama di radio_queue secara background."""
        try:
            await asyncio.wait_for(self._do_prefetch(controller), timeout=25.0)
        except Exception as e:
            _log.warning(f"Prefetch next track gagal: {e}")

    async def _do_prefetch(self, controller: "PlaybackController") -> None:
        if not self.state.radio_queue:
            return
        next_track = self.state.radio_queue[0]
        if next_track.stream_url:
            return
        try:
            await controller.track_loader.resolver.resolve(next_track)
            _log.info(f"Berhasil prefetch stream_url untuk: {next_track.title}")
        except Exception as e:
            _log.warning(f"Error saat resolve stream_url prefetch: {e}")