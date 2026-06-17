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
from typing import TYPE_CHECKING, Optional
from core.event_bus import bus, QUEUE_UPDATED, LOG_MESSAGE

if TYPE_CHECKING:
    from engine.playback_controller import PlaybackController

RANDOM_SEED_QUERIES = [
    "popular hit single track official audio",
    "trending pop hit single",
    "viral tiktok hit song",
    "best acoustic cover single",
    "chill lofi single track",
    "classic rock hit song",
    "popular jazz song official",
    "indie folk hit single",
    "r&b hit single official",
    "top edm drop single",
    "kpop trending hit track",
    "billboard hot 100 hit single"
]
MAX_TRACK_DURATION = 600  # 10 menit — hindari kompilasi panjang / livestream

class RadioMode:
    """
    Purpose: Mengelola pemutaran lagu secara otomatis dan berkelanjutan (Radio Mode).
    Radio menyimpan seluruh lagunya di state.radio_queue, terpisah total
    dari state.queue milik Queue Mode.
    Subscribes to: (tidak ada)
    Publishes: QUEUE_UPDATED, LOG_MESSAGE
    """
    def __init__(self, ytdlp, state):
        self.ytdlp = ytdlp
        self.state = state
        self._is_fetching = False
        self._bg_tasks = set()

    async def on_activated(self, controller: "PlaybackController") -> None:
        """Dipanggil saat user menyalakan Radio Mode.

        Sesuai konstitusi, Radio harus "Start immediately" dan bekerja
        independen dari Queue. Karena itu setiap kali Radio dinyalakan,
        Radio SELALU langsung melakukan pencarian baru dan memutar lagu —
        tidak peduli apa yang sebelumnya terjadi di Queue Mode.
        """
        self.state.radio_queue = []
        seed_artist = self.state.current_track.artist if self.state.current_track else None
        task = asyncio.create_task(self._fetch_and_play_initial(controller, seed_artist))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def on_deactivated(self) -> None:
        """Dipanggil saat user mematikan Radio Mode. Bersihkan sisa state
        Radio agar sesi berikutnya selalu mulai dari kondisi yang bersih,
        dan tidak membocorkan lagu radio ke dalam Queue Mode."""
        self.state.radio_queue = []

    async def next(self, controller: "PlaybackController") -> None:
        """Dipanggil oleh PlaybackController saat track berakhir di Radio Mode."""
        if self.state.radio_queue:
            track = self.state.radio_queue.pop(0)
            task = asyncio.create_task(self._prefetch_next(controller))
            self._bg_tasks.add(task)
            task.add_done_callback(self._bg_tasks.discard)
            await controller.play_track(track)
        else:
            seed_artist = self.state.current_track.artist if self.state.current_track else None
            await self._fetch_and_play_initial(controller, seed_artist)

    async def _prefetch_next(self, controller: "PlaybackController") -> None:
        """Ambil track berikutnya di background, taruh ke radio_queue (bukan queue)."""
        if self._is_fetching:
            return
        self._is_fetching = True
        try:
            track = self.state.current_track
            if not track:
                return
            query = f"{track.artist} music"
            results = await self.ytdlp.search(query, max_results=10)
            existing = self._build_exclusion_set()
            # Filter kompilasi: durasi harus < 10 menit (600 detik) dan bukan livestream (0)
            new_tracks = [t for t in results if t.video_id not in existing and 0 < t.duration < MAX_TRACK_DURATION]
            random.shuffle(new_tracks)
            if new_tracks:
                self.state.radio_queue.extend(new_tracks[:2])
                await bus.publish(QUEUE_UPDATED)
        except Exception as e:
            await bus.publish(LOG_MESSAGE, f"Prefetch Error: {str(e)}")
        finally:
            self._is_fetching = False

    async def _fetch_and_play_initial(self, controller: "PlaybackController", seed_artist: Optional[str] = None) -> None:
        """Cari & putar lagu radio baru — dipakai saat Radio baru diaktifkan
        atau saat radio_queue habis. Selalu langsung memutar (tidak menunggu)."""
        try:
            query = f"{seed_artist} music" if seed_artist else random.choice(RANDOM_SEED_QUERIES)
            results = await self.ytdlp.search(query, max_results=15)
            existing = self._build_exclusion_set()
            filtered = [t for t in results if t.video_id not in existing and 0 < t.duration < MAX_TRACK_DURATION]

            if not filtered and seed_artist:
                # Seed artis tidak membuahkan hasil baru (semua duplikat) -> fallback umum
                query = random.choice(RANDOM_SEED_QUERIES)
                results = await self.ytdlp.search(query, max_results=15)
                existing = self._build_exclusion_set()
                filtered = [t for t in results if t.video_id not in existing and 0 < t.duration < MAX_TRACK_DURATION]

            if filtered:
                random.shuffle(filtered)
                self.state.radio_queue = filtered[1:]
                await controller.play_track(filtered[0])
                await bus.publish(QUEUE_UPDATED)
            else:
                await bus.publish(LOG_MESSAGE, "Radio: Tidak ada hasil lagu ditemukan.")
        except Exception as e:
            await bus.publish(LOG_MESSAGE, f"Radio Error: {str(e)}")

    def _build_exclusion_set(self) -> set[str]:
        ids = {t.video_id for t in self.state.radio_queue}
        if self.state.current_track:
            ids.add(self.state.current_track.video_id)
        for t in self.state.history[-20:]:
            ids.add(t.video_id)
        return ids
