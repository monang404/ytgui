import re
import time
import structlog
from pathlib import Path
from aiohttp import web
from config import CACHE_DIR, STREAM_URL_TTL_SEC
from core.observability import get_metrics_content

logger = structlog.get_logger(__name__)
STATIC_DIR = Path(__file__).parent.parent.parent / "web" / "static"

async def serve_index(request):
    resp = web.FileResponse(STATIC_DIR / "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp

async def health_check(request):
    db = request.app["db"]
    db_status = "connected" if db.conn else "disconnected"

    pc = request.app.get("playback_controller")
    mpv_ok = getattr(getattr(pc, "mpv", None), "is_connected", False)
    mpv_status = "connected" if mpv_ok else "not_started"

    return web.json_response({
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "mpv": mpv_status
    })

async def serve_stream(request):
    video_id = request.match_info.get("video_id")
    if not video_id or not re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
        return web.HTTPBadRequest(text="Invalid video_id")

    cache_file = CACHE_DIR / f"{video_id}.mp3"
    try:
        if not cache_file.resolve().is_relative_to(CACHE_DIR.resolve()):
            return web.HTTPForbidden(text="Akses ditolak")
    except Exception:
        return web.HTTPBadRequest(text="Path tidak valid")

    if cache_file.exists():
        return web.FileResponse(
            cache_file,
            headers={"Access-Control-Allow-Origin": "*"}
        )

    db = request.app["db"]
    ytdlp = request.app["ytdlp"]
    stream_url = None

    row = await db.get_track(video_id)
    if row and row.stream_url and row.stream_url_ts:
        if time.time() - row.stream_url_ts < STREAM_URL_TTL_SEC:
            stream_url = row.stream_url

    http_session = request.app.get("http_session")
    if not http_session:
        if not stream_url:
            try:
                stream_url = await ytdlp.get_stream_url(video_id)
                await db.update_stream_url_only(video_id, stream_url)
            except Exception as e:
                logger.error(f"Gagal fetch stream URL untuk redirect: {e}")
                return web.HTTPServiceUnavailable(text="Stream tidak tersedia saat ini")
        from urllib.parse import urlparse as _urlparse
        _p = _urlparse(stream_url)
        _domain = _p.netloc.lower()
        if _p.scheme != "https" or not (
            _domain.endswith(".googlevideo.com") or _domain.endswith(".youtube.com")
        ):
            logger.error(f"URL stream tidak valid untuk redirect: {stream_url}")
            return web.HTTPForbidden(text="URL stream tidak valid")
        return web.HTTPFound(stream_url)

    for attempt in range(2):
        if not stream_url:
            try:
                stream_url = await ytdlp.get_stream_url(video_id)
                await db.update_stream_url_only(video_id, stream_url)
            except Exception as e:
                if attempt == 1:
                    return web.HTTPInternalServerError(text=f"Gagal mencari stream: {e}")
                continue

        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(stream_url)
            if parsed_url.scheme != "https":
                raise ValueError("Skema URL harus HTTPS")
            domain = parsed_url.netloc.lower()
            if not (domain.endswith(".googlevideo.com") or domain.endswith(".youtube.com")):
                raise ValueError(f"Domain tidak sah: {domain}")
        except Exception as e:
            logger.error(f"SSRF terdeteksi atau URL stream tidak valid: {stream_url} - {e}")
            return web.HTTPForbidden(text="URL stream tidak valid")

        try:
            headers = {}
            if "Range" in request.headers:
                headers["Range"] = request.headers["Range"]

            async with http_session.get(stream_url, headers=headers) as upstream:
                if upstream.status in (403, 410) and attempt == 0:
                    logger.warning(f"YouTube stream URL expired ({upstream.status}), refetching...")
                    stream_url = None
                    continue

                response = web.StreamResponse(
                    status=upstream.status,
                    headers={
                        "Content-Type": upstream.headers.get("Content-Type", "audio/mpeg"),
                        "Accept-Ranges": "bytes",
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "private, max-age=3600",
                    }
                )

                if "Content-Range" in upstream.headers:
                    response.headers["Content-Range"] = upstream.headers["Content-Range"]
                if "Content-Length" in upstream.headers:
                    try:
                        response.content_length = int(upstream.headers["Content-Length"])
                    except ValueError:
                        pass

                await response.prepare(request)

                async for chunk in upstream.content.iter_chunked(16384):
                    await response.write(chunk)

                await response.write_eof()
                return response

        except Exception as e:
            logger.warning(f"Proxy stream error untuk {video_id}: {e}")
            if attempt == 0:
                stream_url = None
                continue
            return web.HTTPInternalServerError(text="Proxy stream error")

async def serve_metrics(request):
    import os as _os
    client_ip = request.remote
    _localhost_ips = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
    metrics_token = _os.environ.get("YTGUI_METRICS_TOKEN")
    is_local = client_ip in _localhost_ips
    has_valid_token = (
        metrics_token
        and request.headers.get("X-Metrics-Token") == metrics_token
    )
    if not is_local and not has_valid_token:
        return web.HTTPForbidden(text="Akses ditolak: metrics hanya untuk localhost atau gunakan X-Metrics-Token")

    content, content_type = get_metrics_content()
    ct = content_type.split(";")[0].strip()
    return web.Response(body=content, content_type=ct)
