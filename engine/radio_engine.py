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
from typing import TYPE_CHECKING, Optional

from core.events import QueueUpdatedEvent, LogMessageEvent

_RADIO_SEARCH_SEM = asyncio.Semaphore(2)

if TYPE_CHECKING:
    from engine.playback_controller import PlaybackController
from core.state import AppState, PlaybackMode, PlayerStatus
from core.ports import MediaExtractorPort
from core.task_utils import safe_create_task

_FALLBACK_ARTISTS = ["Sheila On 7", "Dewa 19", "Tulus", "Nadin Amizah", "Raisa"]

MAX_TRACK_DURATION = 600        # 10 menit — hindari kompilasi / livestream
TRACKS_PER_ARTIST_TARGET = 3   # target track unik per artis dalam satu batch
ARTISTS_PER_BATCH = 4          # artis per batch normal (4×3 = 12 lagu)
ARTISTS_QUICK = 2              # artis untuk fetch cepat pertama (2×3 = 6 lagu)
SEED_LIMIT = 2                 # max judul populer dari DB per artis

_TITLE_NOISE_WORDS = frozenset({
    "official", "music", "video", "audio", "lyric", "lyrics", "mv",
    "cover", "live", "performance", "hd", "hq", "remastered", "remaster",
    "full", "version", "ver", "feat", "ft", "original", "soundtrack",
    "ost", "karaoke", "instrumental", "acoustic", "akustik", "konser",
})


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    words = [w for w in t.split() if w not in _TITLE_NOISE_WORDS]
    return " ".join(words).strip()


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
        # Playlist cadangan — diisi di background, dipakai saat user klik
        self._standby: list = []
        self._standby_lock = asyncio.Lock()

    # ── bootstrap ─────────────────────────────────────────────

    async def _ensure_artists_loaded(self) -> None:
        if self._seed_artists:
            return
        try:
            if self.db and self.db.conn:
                self._seed_artists = await self.db.get_all_artists()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Gagal load artis dari DB: {e}")

        if not self._seed_artists:
            import logging
            logging.getLogger(__name__).warning(
                "Tabel artists kosong. Jalankan import_artists.py"
            )
            self._seed_artists = list(_FALLBACK_ARTISTS)

    # ── lifecycle ─────────────────────────────────────────────

    async def on_activated(self, controller: "PlaybackController") -> None:
        await self._ensure_artists_loaded()
        self.state.radio_queue.clear()
        self._artist_rotation = []
        _track_task(self._bg_tasks, self._start(controller), name="radio_start")

    async def on_deactivated(self) -> None:
        self.state.radio_queue.clear()
        for task in list(self._bg_tasks):
            task.cancel()
        self._bg_tasks.clear()
        # Jangan buang _standby — bisa dipakai kalau radio dinyalakan lagi

    # ── next (dipanggil saat track habis) ─────────────────────

    async def next(self, controller: "PlaybackController") -> None:
        if self.state.radio_queue:
            track = self.state.radio_queue.popleft()
            # Kalau queue mulai tipis, pastikan standby sedang disiapkan
            if len(self.state.radio_queue) <= 5:
                _track_task(self._bg_tasks, self._ensure_standby(controller), name="radio_ensure_standby")
            await controller.play_track(track)
        else:
            # Queue habis — ambil dari standby atau fetch ulang
            _track_task(self._bg_tasks, self._start(controller), name="radio_refill")

    # ── inti: start dengan standby atau fetch cepat ───────────

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
            # Langsung pakai standby
            self.state.radio_queue.clear()
            self.state.radio_queue.extend(tracks[1:])
            await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            await controller.play_track(tracks[0])
            # Siapkan standby berikutnya di background
            _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby")
            return

        # Fetch cepat: ARTISTS_QUICK artis dulu, langsung putar
        try:
            quick_tracks = await asyncio.wait_for(
                self._gather_batch(max_artists=ARTISTS_QUICK),
                timeout=20.0
            )
        except (asyncio.TimeoutError, Exception):
            quick_tracks = []

        if quick_tracks:
            self.state.radio_queue.clear()
            self.state.radio_queue.extend(quick_tracks[1:])
            await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            await controller.play_track(quick_tracks[0])
            # Background: fetch sisa artis dan masukkan ke queue + siapkan standby
            _track_task(self._bg_tasks, self._backfill_and_standby(controller), name="radio_backfill")
        else:
            await controller.bus.publish(LogMessageEvent(
                message="Radio: Tidak ada hasil ditemukan.", room_id=controller.room_id
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
                    await controller.bus.publish(QueueUpdatedEvent(room_id=controller.room_id))
            except Exception:
                pass

        # Setelah backfill selesai, langsung siapkan standby berikutnya
        _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby")

    async def _build_standby(self, controller: "PlaybackController") -> None:
        """Siapkan playlist cadangan 12 lagu di background.
        Tidak akan jalan kalau standby sudah ada atau sedang dibangun."""
        async with self._standby_lock:
            if self._standby:
                return  # sudah ada, tidak perlu rebuild

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
            except Exception:
                pass

    async def _ensure_standby(self, controller: "PlaybackController") -> None:
        """Pastikan standby sedang disiapkan kalau belum ada."""
        async with self._standby_lock:
            if self._standby:
                return
        _track_task(self._bg_tasks, self._build_standby(controller), name="radio_build_standby2")

    # ── dipanggil dari playback_controller saat tombol Acak ───

    async def _fetch_and_play_initial(
        self, controller: "PlaybackController", seed_artist: Optional[str] = None
    ) -> None:
        """Entry point untuk tombol Acak — sama dengan _start tapi
        reset rotasi dulu agar artis benar-benar fresh."""
        self._artist_rotation = []
        async with self._standby_lock:
            self._standby = []  # buang standby lama, minta yang fresh
        await self._start(controller)

    # ── batch & search ────────────────────────────────────────

    async def _gather_batch(
        self, prioritized_artist: Optional[str] = None, max_artists: int = ARTISTS_PER_BATCH
    ) -> list:
        chosen: list[str] = []
        if prioritized_artist and prioritized_artist in self._seed_artists:
            chosen.append(prioritized_artist)
        slots_left = max_artists - len(chosen)
        if slots_left > 0:
            chosen.extend(self._next_artists_from_rotation(slots_left, exclude=set(chosen)))

        results_per_artist = await asyncio.gather(
            *[self._search_artist(artist) for artist in chosen],
            return_exceptions=True,
        )
        per_artist_tracks: list[list] = [
            r if not isinstance(r, Exception) else []
            for r in results_per_artist
        ]
        return self._interleave(per_artist_tracks)

    def _next_artists_from_rotation(self, count: int, exclude: set[str]) -> list[str]:
        picked: list[str] = []
        while len(picked) < count:
            if not self._artist_rotation:
                self._artist_rotation = list(self._seed_artists)
                random.shuffle(self._artist_rotation)
            artist = self._artist_rotation.pop(0)
            if artist in exclude or artist in picked:
                continue
            picked.append(artist)
        return picked

    async def _search_artist(self, artist: str) -> list:
        """Cari track untuk satu artis.
        Prioritas: judul populer dari DB (max SEED_LIMIT query paralel).
        Fallback: query generik "{artist} music".
        """
        seed_titles: list[str] = []
        if self.db and self.db.conn:
            try:
                seed_titles = await self.db.get_artist_seeds(artist, limit=SEED_LIMIT)
            except Exception:
                pass

        existing = self._build_exclusion_set()
        seen_titles: set[str] = set()
        unique_tracks: list = []

        if seed_titles:
            async def _search_one(judul: str):
                async with _RADIO_SEARCH_SEM:
                    return await self.ytdlp.search(f"{judul} {artist}", max_results=5)

            results_nested = await asyncio.gather(
                *[_search_one(j) for j in seed_titles],
                return_exceptions=True,
            )
            candidate_lists = [r for r in results_nested if not isinstance(r, Exception)]
            for i in range(max((len(l) for l in candidate_lists), default=0)):
                for lst in candidate_lists:
                    if i < len(lst):
                        t = lst[i]
                        if t.video_id in existing:
                            continue
                        if not (0 < t.duration < MAX_TRACK_DURATION):
                            continue
                        norm = _normalize_title(t.title)
                        if norm and norm in seen_titles:
                            continue
                        seen_titles.add(norm)
                        unique_tracks.append(t)
                        if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:
                            break
                if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:
                    break

        if len(unique_tracks) < TRACKS_PER_ARTIST_TARGET:
            async with _RADIO_SEARCH_SEM:
                fallback = await self.ytdlp.search(f"{artist} music", max_results=15)
            for t in fallback:
                if t.video_id in existing:
                    continue
                if not (0 < t.duration < MAX_TRACK_DURATION):
                    continue
                norm = _normalize_title(t.title)
                if norm and norm in seen_titles:
                    continue
                seen_titles.add(norm)
                unique_tracks.append(t)
                if len(unique_tracks) >= TRACKS_PER_ARTIST_TARGET:
                    break

        return unique_tracks[:TRACKS_PER_ARTIST_TARGET]

    @staticmethod
    def _interleave(per_artist_tracks: list[list]) -> list:
        result = []
        max_len = max((len(lst) for lst in per_artist_tracks), default=0)
        for i in range(max_len):
            for lst in per_artist_tracks:
                if i < len(lst):
                    result.append(lst[i])
        return result

    def _build_exclusion_set(self) -> set[str]:
        ids = {t.video_id for t in self.state.radio_queue}
        if self.state.current_track:
            ids.add(self.state.current_track.video_id)
        for t in list(self.state.history)[-20:]:
            ids.add(t.video_id)
        return ids
