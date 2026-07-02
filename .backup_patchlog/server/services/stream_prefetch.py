import time
import structlog
from config import STREAM_URL_TTL_SEC
from core.ports import DatabasePort, MediaExtractorPort

logger = structlog.get_logger(__name__)

class StreamPrefetchService:
    def __init__(self, db: DatabasePort, ytdlp: MediaExtractorPort):
        self.db = db
        self.ytdlp = ytdlp

    async def prefetch_stream_url(self, video_id: str):
        row = await self.db.get_track(video_id)
        if row and row.stream_url and row.stream_url_ts:
            if time.time() - row.stream_url_ts < STREAM_URL_TTL_SEC:
                return
        try:
            url = await self.ytdlp.get_stream_url(video_id)
            await self.db.update_stream_url_only(video_id, url)
        except Exception as e:
            logger.warning(f"Pre-fetch stream URL gagal untuk {video_id}: {e}")
