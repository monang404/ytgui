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

# Fallback minimal — dipakai HANYA jika tabel artists di DB masih kosong
# (misalnya belum pernah menjalankan import_artists.py).
# Sumber artis utama dibaca dari DB saat RadioMode pertama kali diaktifkan.
_FALLBACK_ARTISTS = ["Sheila On 7", "Dewa 19", "Tulus", "Nadin Amizah", "Raisa"]

MAX_TRACK_DURATION = 600  # 10 menit — hindari kompilasi panjang / livestream
TRACKS_PER_ARTIST_TARGET = 3  # target track unik per artis dalam satu batch
ARTISTS_PER_BATCH = 4  # jumlah artis berbeda yang diambil sekaligus per batch (4x3 = 12 lagu/sesi)

# Kata-kata noise yang sering muncul di judul upload YouTube dan tidak
# relevan untuk membedakan "lagu yang sama" vs "lagu yang berbeda".
_TITLE_NOISE_WORDS = frozenset({
    "official", "music", "video", "audio", "lyric", "lyrics", "mv",
    "cover", "live", "performance", "hd", "hq", "remastered", "remaster",
    "full", "version", "ver", "feat", "ft", "original", "soundtrack",
    "ost", "karaoke", "instrumental", "acoustic", "akustik", "konser",
})


def _normalize_title(title: str) -> str:
    """Normalisasi judul track agar varian upload (official video, lyric
    video, audio only, cover, live, dll) dari lagu yang sama bisa
    dikenali sebagai duplikat walau video_id-nya berbeda.
    """
    if not title:
        return ""
    t = title.lower()
    # Buang isi dalam kurung/bracket, biasanya berisi noise: "(Official Video)", "[Lyrics]"
    t = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", t)
    # Buang karakter non alfanumerik (selain spasi)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    # Buang kata-kata noise umum
    words = [w for w in t.split() if w not in _TITLE_NOISE_WORDS]
    return " ".join(words).strip()


class RadioMode:
    """
    Purpose: Mengelola pemutaran lagu secara otomatis dan berkelanjutan (Radio Mode).
    Radio menyimpan seluruh lagunya di state.radio_queue, terpisah total
    dari state.queue milik Queue Mode.
    Subscribes to: (tidak ada)
    Publishes: QUEUE_UPDATED, LOG_MESSAGE
    """
    def __init__(self, ytdlp: MediaExtractorPort, state: AppState, db=None):
        self.ytdlp = ytdlp
        self.state = state
        self.db = db
        self._is_fetching = False
        self._bg_tasks = set()
        # Pool artis — diisi dari DB saat pertama kali diaktifkan (lazy load).
        # Setelah terisi, tidak query DB lagi kecuali di-reload manual.
        self._seed_artists: list[str] = []
        # Rotasi artis tanpa pengulangan: urutan acak dari _seed_artists yang
        # "dikonsumsi" dari depan tiap kali batch baru diambil. Begitu deck
        # ini habis, semua artis sudah pasti kebagian giliran sekali, lalu
        # deck dikocok ulang dari awal untuk putaran berikutnya.
        self._artist_rotation: list[str] = []

    async def _ensure_artists_loaded(self) -> None:
        """Load pool artis dari DB (lazy — hanya sekali selama instance hidup).
        Kalau DB tidak tersedia atau tabel kosong, jatuh ke _FALLBACK_ARTISTS.
        """
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
                "Tabel artists kosong atau DB tidak tersedia. "
                "Jalankan: python data/import_artists.py --db cache/library.db --json data/artists.json"
            )
            self._seed_artists = list(_FALLBACK_ARTISTS)

    async def on_activated(self, controller: "PlaybackController") -> None:
        """Dipanggil saat user menyalakan Radio Mode.

        Sesuai konstitusi, Radio harus "Start immediately" dan bekerja
        independen dari Queue. Karena itu setiap kali Radio dinyalakan,
        Radio SELALU langsung melakukan pencarian baru dan memutar lagu —
        tidak peduli apa yang sebelumnya terjadi di Queue Mode.
        """
        await self._ensure_artists_loaded()
        self.state.radio_queue.clear()
        seed_artist = random.choice(self._seed_artists)
        task = safe_create_task(self._fetch_and_play_initial(controller, seed_artist), name="radio_initial")
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def on_deactivated(self) -> None:
        """Dipanggil saat user mematikan Radio Mode. Bersihkan sisa state
        Radio agar sesi berikutnya selalu mulai dari kondisi yang bersih,
        dan tidak membocorkan lagu radio ke dalam Queue Mode."""
        self.state.radio_queue.clear()
        for task in list(self._bg_tasks):
            task.cancel()
        self._bg_tasks.clear()

    async def next(self, controller: "PlaybackController") -> None:
        """Dipanggil oleh PlaybackController saat track berakhir di Radio Mode."""
        if self.state.radio_queue:
            track = self.state.radio_queue.popleft()
            if len(self.state.radio_queue) <= 5:
                task = safe_create_task(self._prefetch_next(controller), name="radio_prefetch")
                self._bg_tasks.add(task)
                task.add_done_callback(self._bg_tasks.discard)
            await controller.play_track(track)
        else:
            await self._ensure_artists_loaded()
            seed_artist = random.choice(self._seed_artists)
            await self._fetch_and_play_initial(controller, seed_artist)

    async def _prefetch_next(self, controller: "PlaybackController") -> None:
        """Ambil batch track berikutnya di background, taruh ke radio_queue
        (bukan queue). Sama seperti _fetch_and_play_initial, batch ini
        diambil dari beberapa artis sekaligus lalu di-interleave supaya
        tidak monoton satu artis berturut-turut."""
        if self._is_fetching:
            return
        self._is_fetching = True
        try:
            new_tracks = await asyncio.wait_for(self._gather_batch(), timeout=30.0)
            if new_tracks:
                self.state.radio_queue.extend(new_tracks)
                while len(self.state.radio_queue) > 30:
                    self.state.radio_queue.pop()
                await controller.bus.publish(QueueUpdatedEvent())
        except Exception as e:
            await controller.bus.publish(LogMessageEvent(message=f"Prefetch Error: {str(e)}"))
        finally:
            self._is_fetching = False

    async def _fetch_and_play_initial(self, controller: "PlaybackController", seed_artist: Optional[str] = None) -> None:
        """Cari & putar lagu radio baru — dipakai saat Radio baru diaktifkan
        atau saat radio_queue habis. Selalu langsung memutar (tidak menunggu).

        seed_artist dipertahankan demi kompatibilitas signature (dipanggil
        dari playback_controller.py dengan seed_artist=None saat tombol
        randomize ditekan), tapi nilainya tidak lagi dipakai langsung
        sebagai satu-satunya sumber — pengambilan tetap dilakukan sebagai
        batch dari beberapa artis sekaligus supaya hasil pertama yang
        diputar pun sudah konsisten dengan strategi anti-bosen yang baru.
        """
        try:
            try:
                tracks = await asyncio.wait_for(self._gather_batch(prioritized_artist=seed_artist), timeout=30.0)
            except asyncio.TimeoutError:
                await controller.bus.publish(LogMessageEvent(message="Pencarian radio timeout (30s), mencoba artis lain..."))
                tracks = []

            if not tracks:
                # Coba sekali lagi dengan batch artis yang benar-benar baru
                try:
                    tracks = await asyncio.wait_for(self._gather_batch(), timeout=30.0)
                except asyncio.TimeoutError:
                    await controller.bus.publish(LogMessageEvent(message="Pencarian radio kembali timeout, coba lagi nanti."))
                    tracks = []

            if tracks:
                self.state.radio_queue.clear()
                self.state.radio_queue.extend(tracks[1:])
                await controller.bus.publish(QueueUpdatedEvent())
                await controller.play_track(tracks[0])
            else:
                await controller.bus.publish(LogMessageEvent(message="Radio: Tidak ada hasil lagu ditemukan."))
        except Exception as e:
            await controller.bus.publish(LogMessageEvent(message=f"Radio Error: {str(e)}"))

    async def _gather_batch(self, prioritized_artist: Optional[str] = None) -> list:
        """Ambil track dari beberapa artis berbeda (ARTISTS_PER_BATCH) sekaligus,
        dedup judul per artis, lalu interleave round-robin hasilnya supaya
        urutan akhir bervariasi (tidak ada 2 lagu artis sama menumpuk
        berurutan, kecuali memang sudah kehabisan variasi).

        Pemilihan artis memakai mekanisme rotasi tanpa pengulangan
        (lihat _next_artists_from_rotation): dengan pool besar (99 artis),
        ini menjamin semua artis kebagian giliran tampil dulu sebelum ada
        yang diulang, bukan cuma "kemungkinan besar rata" seperti random
        sample independen.

        Kalau prioritized_artist diberikan, artis itu dipastikan masuk
        dalam batch (mengisi salah satu slot), sisanya diambil dari deck
        rotasi.
        """
        chosen: list[str] = []

        if prioritized_artist and prioritized_artist in self._seed_artists:
            chosen.append(prioritized_artist)

        slots_left = ARTISTS_PER_BATCH - len(chosen)
        if slots_left > 0:
            chosen.extend(self._next_artists_from_rotation(slots_left, exclude=set(chosen)))

        # Kumpulkan track per artis secara paralel
        results_per_artist = await asyncio.gather(
            *[self._search_artist(artist) for artist in chosen],
            return_exceptions=True,
        )

        per_artist_tracks: list[list] = []
        for res in results_per_artist:
            if isinstance(res, Exception):
                per_artist_tracks.append([])
            else:
                per_artist_tracks.append(res)

        return self._interleave(per_artist_tracks)

    def _next_artists_from_rotation(self, count: int, exclude: set[str]) -> list[str]:
        """Ambil `count` nama artis dari depan deck rotasi (tanpa pengulangan).
        Begitu deck kehabisan stok di tengah pengambilan, deck dikocok ulang
        otomatis dari seluruh _seed_artists (minus exclude) dan dilanjutkan,
        supaya satu batch tidak pernah kekurangan slot."""
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
        """Cari track untuk satu artis, filter durasi + exclusion, lalu
        dedup berdasarkan judul yang dinormalisasi (biar 'Rasa Ini' versi
        official video/lyric/audio tidak terhitung sebagai 3 lagu beda).
        Mengembalikan sekitar TRACKS_PER_ARTIST_TARGET track unik
        (bisa kurang kalau memang stoknya tipis)."""
        async with _RADIO_SEARCH_SEM:
            query = f"{artist} music"
            results = await self.ytdlp.search(query, max_results=15)
            existing = self._build_exclusion_set()

        seen_titles: set[str] = set()
        unique_tracks = []
        for t in results:
            if t.video_id in existing:
                continue
            if not (0 < t.duration < MAX_TRACK_DURATION):
                continue
            norm = _normalize_title(t.title)
            if norm and norm in seen_titles:
                continue
            seen_titles.add(norm)
            unique_tracks.append(t)

        random.shuffle(unique_tracks)
        return unique_tracks[:TRACKS_PER_ARTIST_TARGET]

    @staticmethod
    def _interleave(per_artist_tracks: list[list]) -> list:
        """Gabungkan beberapa list track per-artis dengan round-robin:
        ambil satu-satu giliran dari tiap artis (Artis1, Artis2, Artis3,
        Artis1, ...). Kalau satu artis sudah habis stoknya, sisanya lanjut
        gilir dari artis-artis yang masih ada."""
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
