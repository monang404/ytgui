"""
Purpose: Mengelola download lagu dari YouTube.
Subscribes to: CMD_DOWNLOAD
Publishes: LOG_MESSAGE, DOWNLOAD_COMPLETE
"""

import asyncio
import structlog
from core.event_bus import EventBus
from core.events import LogMessageEvent, DownloadCompleteEvent
from core.command_bus import command_bus, CMD_DOWNLOAD
from core.state import AppState, TrackInfo
from core.ports import MediaExtractorPort
from core.task_utils import safe_create_task

logger = structlog.get_logger(__name__)

class DownloadManager:
    def __init__(self, bus: EventBus, state: AppState, ytdlp: MediaExtractorPort):
        self.bus = bus
        self.state = state
        self.ytdlp = ytdlp
        self._download_lock = asyncio.Lock()

        command_bus.register(CMD_DOWNLOAD, self._on_download)

    async def _on_download(self, track: TrackInfo | None = None):
        target = track or self.state.current_track
        if not target:
            await self.bus.publish(LogMessageEvent(message="Tidak ada lagu yang dipilih untuk di-download"))
            return

        if target.local_path:
            await self.bus.publish(LogMessageEvent(message="Lagu sudah tersimpan lokal"))
            return

        if self._download_lock.locked():
            await self.bus.publish(LogMessageEvent(message="Download sedang berjalan, tunggu selesai."))
            return

        safe_create_task(self._do_download(target), name=f"download_{target.video_id}")

    async def _do_download(self, track: TrackInfo):
        async with self._download_lock:
            try:
                self.state.download_progress = 0.0
                await self.bus.publish(LogMessageEvent(message=f"Memulai download: {track.title}"))

                loop = asyncio.get_running_loop()

                def sync_progress_hook(d):
                    if d.get('status') == 'downloading':
                        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded_bytes = d.get('downloaded_bytes', 0)
                        if total_bytes and total_bytes > 0:
                            percent = downloaded_bytes / total_bytes
                            loop.call_soon_threadsafe(self._update_progress, percent)

                local_path = await self.ytdlp.download_mp3(track.video_id, on_progress=sync_progress_hook)
                track.local_path = local_path
                self.state.download_progress = None

                import shutil
                from core.utils import user_download_path
                
                user_path = user_download_path(track.artist, track.title)
                user_path.parent.mkdir(exist_ok=True)
                if not user_path.exists():
                    shutil.copy2(local_path, user_path)

                await self.bus.publish(LogMessageEvent(message=f"Download sukses: {track.title} (Tersimpan di folder 'downloads')"))
                await self.bus.publish(DownloadCompleteEvent(track=track))

            except Exception as e:
                self.state.download_progress = None
                logger.error(f"Download error: {e}", exc_info=True)
                await self.bus.publish(LogMessageEvent(message=f"Download gagal: {str(e)}"))

    def _update_progress(self, percent: float):
        self.state.download_progress = percent
        from core.events import DownloadProgressEvent
        safe_create_task(self.bus.publish(DownloadProgressEvent(progress=percent)), name="pub_dl_prog")
