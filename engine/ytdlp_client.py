import asyncio
import yt_dlp
import re
from core.state import TrackInfo
from config import CACHE_DIR

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
        "format": "bestaudio/best",
    }

    def __init__(self):
        self.is_cancelled = False

    def cancel_download(self):
        self.is_cancelled = True

    def _check_cancel_hook(self, d):
        if self.is_cancelled:
            raise Exception("DownloadCancelled")

    async def search(self, query: str, max_results: int = 10) -> list[TrackInfo]:
        opts = {**self._YDL_OPTS_INFO,
                "extract_flat": True,
                "playlist_items": f"1:{max_results}"}
        url = f"ytsearch{max_results}:{query}"
        loop = asyncio.get_running_loop()  # HIGH-03 fix
        results = await loop.run_in_executor(None, self._extract_sync, url, opts)
        return [self._to_track(e) for e in results.get("entries", []) if e]

    async def get_stream_url(self, video_id: str) -> str:
        """Get direct audio URL. We now delegate this to mpv internally to avoid HTTP 403 Forbidden."""
        return f"https://www.youtube.com/watch?v={video_id}"

    async def download_mp3(self, video_id: str, on_progress=None) -> str:
        """Download to CACHE_DIR/video_id.mp3. Returns the local path."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', video_id)
        out_path = CACHE_DIR / f"{safe_id}.%(ext)s"
        
        hooks = [self._check_cancel_hook]
        if on_progress:
            hooks.append(on_progress)
            
        opts = {
            **self._YDL_OPTS_INFO,
            "format": "bestaudio/best",
            "outtmpl": str(out_path),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "progress_hooks": hooks,
        }
        loop = asyncio.get_running_loop()  # HIGH-03 fix
        await loop.run_in_executor(None, self._download_sync, video_id, opts)
        return str(CACHE_DIR / f"{safe_id}.mp3")

    def _extract_sync(self, url, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _download_sync(self, video_id, opts):
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    def _pick_audio_url(self, info: dict) -> str:
        formats = info.get("formats", [])
        for fmt in reversed(formats):
            if fmt.get("acodec") != "none" and fmt.get("vcodec") == "none":
                return fmt["url"]
        return info["url"]

    def _to_track(self, entry: dict) -> TrackInfo:
        # Some yt-dlp versions return duration as float or None
        duration_raw = entry.get("duration", 0)
        duration = int(duration_raw) if duration_raw else 0
        
        # MED-07 fix: Guard against missing/empty video ID
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
