"""
Purpose: Mengelola pemutaran lagu secara otomatis dan berkelanjutan (Radio Mode).
Subscribes to: (tidak ada)
Publishes: QUEUE_UPDATED, LOG_MESSAGE
"""

import asyncio
from typing import TYPE_CHECKING
from core.event_bus import bus, QUEUE_UPDATED, LOG_MESSAGE

if TYPE_CHECKING:
    from engine.playback_controller import PlaybackController

class RadioMode:
    """
    Purpose: Mengelola pemutaran lagu secara otomatis dan berkelanjutan (Radio Mode).
    Subscribes to: (tidak ada)
    Publishes: QUEUE_UPDATED, LOG_MESSAGE
    """
    def __init__(self, ytdlp, state):
        self.ytdlp = ytdlp
        self.state = state
        self._is_fetching = False

    async def on_activated(self, controller: "PlaybackController") -> None:
        """Dipanggil saat user switch ke Radio Mode."""
        if not self.state.current_track:
            asyncio.create_task(self._fetch_and_play_initial(controller))
        elif len(self.state.queue) == 0:
            asyncio.create_task(self._prefetch_next(controller))

    async def next(self, controller: "PlaybackController") -> None:
        """Dipanggil oleh PlaybackController saat track berakhir di Radio Mode."""
        if self.state.queue:
            track = self.state.queue.pop(0)
            asyncio.create_task(self._prefetch_next(controller))  # prefetch track berikutnya
            await controller.play_track(track)
        else:
            await self._fetch_and_play_initial(controller)

    async def _prefetch_next(self, controller: "PlaybackController") -> None:
        """Ambil track berikutnya di background, taruh ke queue."""
        if self._is_fetching:
            return
        self._is_fetching = True
        try:
            track = self.state.current_track
            if not track:
                return
            query = f"{track.artist} music"
            results = await self.ytdlp.search(query, max_results=5)
            existing = self._build_exclusion_set()
            new_tracks = [t for t in results if t.video_id not in existing][:2]
            if new_tracks:
                self.state.queue.extend(new_tracks)
                await bus.publish(QUEUE_UPDATED)
        except Exception:
            pass  # silent best-effort
        finally:
            self._is_fetching = False

    async def _fetch_and_play_initial(self, controller: "PlaybackController") -> None:
        """Dipakai saat Radio diaktifkan tanpa track berjalan."""
        try:
            results = await self.ytdlp.search("top hits music", max_results=3)
            if results:
                self.state.queue = results[1:]
                await controller.play_track(results[0])
        except Exception:
            await bus.publish(LOG_MESSAGE, "Radio: Tidak bisa memuat lagu awal.")

    def _build_exclusion_set(self) -> set[str]:
        ids = {t.video_id for t in self.state.queue}
        if self.state.current_track:
            ids.add(self.state.current_track.video_id)
        for t in self.state.history[-20:]:
            ids.add(t.video_id)
        return ids
