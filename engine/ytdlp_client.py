import asyncio
import yt_dlp
import re
from concurrent.futures import ThreadPoolExecutor
from core.state import TrackInfo
from config import CACHE_DIR, YTDLP_RESOLVE_TIMEOUT_SEC

class YtDlpClient:
    """
    yt-dlp is run in a thread executor because it is synchronous.
    Do NOT call yt-dlp directly in the event loop.

    HIGH-04 note: extract_flat=True returns minimal metadata for speed.
    Fields like view_count and thumbnail may be None. This is an
    intentional trade-off — full extraction takes 2-5x longer.
    """

    _YDL_OPTS_INFO = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "format_sort": ["abr", "asr"],
    }

    def __init__(self):
        self.is_cancelled = False
        self._executor = ThreadPoolExecutor(max_workers=4)

    def cancel_download(self):
        self.is_cancelled = True

    def _check_cancel_hook(self, d):
        if self.is_cancelled:
            raise Exception("DownloadCancelled")

    async def search(self, query: str, max_results: int = 10) -> list[TrackInfo]:
        options = {**self._YDL_OPTS_INFO,
                "extract_flat": True}
        url = f"ytsearch{max_results}:{query}"
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(self._executor, self._extract_sync, url, options)

        tracks = []
        for entry in results.get("entries", []):
            if not entry:
                continue

            duration_raw = entry.get("duration")
            try:
                duration = int(duration_raw) if duration_raw else 0
            except (ValueError, TypeError):
                duration = 0

            title_raw = entry.get("title")
            title = str(title_raw).lower() if title_raw else ""

            if duration > 600:
                continue
            if any(kw in title for kw in ["compilation", "full album", "mix", "playlist", "mashup", "medley", "megamix"]):
                continue

            tracks.append(self._to_track(entry))
            if len(tracks) >= max_results:
                break

        return tracks

    async def get_stream_url(self, video_id: str) -> str:
        """Get direct audio URL using yt-dlp to allow true caching.
        Raises RuntimeError jika ekstraksi gagal — caller wajib handle.
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)
        options = {
            **self._YDL_OPTS_INFO,
            "extract_flat": False,
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_running_loop()
        try:
            # PATCH-YTDLP-RESOLVE-TIMEOUT-01: dulu run_in_executor() di sini tidak punya batas
            info = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._extract_sync, url, options),
                timeout=YTDLP_RESOLVE_TIMEOUT_SEC,
            )
            if info:
                stream_url = self._pick_audio_url(info)
                if stream_url:
                    return stream_url
            raise RuntimeError(f"yt-dlp returned no stream URL for {video_id}")
        except asyncio.TimeoutError:
            _log.error(f"get_stream_url timed out after {YTDLP_RESOLVE_TIMEOUT_SEC}s for {video_id}")
            raise RuntimeError(
                f"Timeout ({YTDLP_RESOLVE_TIMEOUT_SEC}s) saat mengambil stream URL untuk {video_id}"
            )
        except RuntimeError:
            raise
        except Exception as e:
            _log.error(f"get_stream_url failed for {video_id}: {type(e).__name__}: {e}")
            raise RuntimeError(f"Gagal mengambil stream URL untuk {video_id}: {e}") from e

    async def download_mp3(self, video_id: str, on_progress=None) -> str:
        """Download to CACHE_DIR/video_id.mp3. Returns the local path."""
        self.is_cancelled = False
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', video_id)
        out_path = CACHE_DIR / f"{safe_id}.%(ext)s"

        hooks = [self._check_cancel_hook]
        if on_progress:
            hooks.append(on_progress)

        options = {
            **self._YDL_OPTS_INFO,
            "format": "bestaudio/best",
            "format_sort": ["abr", "asr"],
            "outtmpl": str(out_path),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }],
            "progress_hooks": hooks,
        }
        loop = asyncio.get_running_loop()  # HIGH-03 fix
        await loop.run_in_executor(self._executor, self._download_sync, video_id, options)
        return str(CACHE_DIR / f"{safe_id}.mp3")

    def _extract_sync(self, url, options):
        with yt_dlp.YoutubeDL(options) as ytdl_instance:
            return ytdl_instance.extract_info(url, download=False)

    def _download_sync(self, video_id, options):
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(options) as ytdl_instance:
            ytdl_instance.download([url])

    def _pick_audio_url(self, info: dict) -> str:
        formats = info.get("formats", [])
        for format_info in reversed(formats):
            if format_info.get("acodec") != "none" and format_info.get("vcodec") == "none":
                return format_info["url"]
        return info["url"]

    def _to_track(self, entry: dict) -> TrackInfo:
        duration_raw = entry.get("duration", 0)
        duration = int(duration_raw) if duration_raw else 0

        video_id = entry.get("id", "") or entry.get("url", "")
        if video_id and not re.match(r'^[a-zA-Z0-9_\-]{1,64}$', video_id):
            video_id = f"vid_{abs(hash(entry.get('title', ''))) % 10**10}"
        elif not video_id:
            video_id = f"vid_{abs(hash(entry.get('title', ''))) % 10**10}"

        return TrackInfo(
            video_id=video_id,
            title=entry.get("title", "Unknown"),
            artist=entry.get("uploader", "Unknown"),
            duration=duration,
            thumbnail=entry.get("thumbnail"),
            view_count=entry.get("view_count"),
        )
