import asyncio
import json
import structlog
import os
from config import MPV_SOCKET
from core.event_bus import EventBus
from core.events import TrackProgressEvent, TrackEndedEvent, TrackPauseChangedEvent
from core.state import PlayerStatus
from core.task_utils import safe_create_task
from core.exceptions import MpvConnectionError
from core.constants import MAX_VOLUME
logger = structlog.get_logger(__name__)

class MpvController:
    """
    Controls mpv via JSON IPC over a socket.
    Start mpv with: mpv --no-video --idle --input-ipc-server={socket}

    CRITICAL-03 fix: On Windows, falls back to TCP socket (localhost:port)
    if Unix sockets are not available.
    CRITICAL-06 fix: _set_property is now properly defined.
    MED-11: Basic reconnection support via is_connected flag.
    """

    def __init__(self, socket_path: str = None, tcp_port: str = None, event_bus: EventBus = None):
        self._reader = None
        self._writer = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._req_lock = asyncio.Lock()  # RC-02: lindungi increment _request_id
        self._reconnect_lock = asyncio.Lock()
        self._observer_task = None
        self.is_connected = False
        self._mpv_process = None
        self.socket_path = socket_path or MPV_SOCKET
        self.tcp_port = tcp_port or os.environ.get("YT_PLAYER_MPV_PORT", "12345")
        # Injected bus (fallback ke global bus)
        if event_bus is None:
            from core.event_bus import bus as _global_bus
            event_bus = _global_bus
        self._bus = event_bus

    async def connect(self):
        async with self._reconnect_lock:
            if self.is_connected:
                return
            await self._do_connect()

    async def _do_connect(self):
        import shutil

        ytdl_path = shutil.which("yt-dlp")
        ytdl_arg = f"--script-opts=ytdl_hook-ytdl_path={ytdl_path}" if ytdl_path else ""

        common_args = [
            "--no-video", "--idle",
            "--ytdl-format=bestaudio/best",
            "--audio-pitch-correction=yes",
            "--cache=yes",
            "--demuxer-max-bytes=50M",
            "--demuxer-max-back-bytes=20M",
            "--demuxer-readahead-secs=60",
            "--audio-buffer=0",
        ]

        if os.name == 'nt':
            cmd = ["mpv"] + common_args + [f"--input-ipc-server=tcp://127.0.0.1:{self.tcp_port}"]
            if ytdl_arg: cmd.insert(1, ytdl_arg)
        else:
            os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)
            if os.path.exists(self.socket_path):
                try:
                    os.remove(self.socket_path)
                except OSError:
                    pass
            cmd = ["mpv"] + common_args + [f"--input-ipc-server={self.socket_path}"]
            if ytdl_arg: cmd.insert(1, ytdl_arg)

        try:
            self._mpv_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                stdin=asyncio.subprocess.DEVNULL
            )
            if os.name != 'nt':
                # gunakan self.socket_path, bukan MPV_SOCKET global
                for _ in range(50):
                    await asyncio.sleep(0.1)
                    if os.path.exists(self.socket_path):
                        break
            else:
                await asyncio.sleep(1.0)
        except OSError as e:
            logger.error(f"Failed to spawn mpv process: {e}")

        for attempt in range(10):
            try:
                if os.name == 'nt':
                    self._reader, self._writer = await asyncio.open_connection('127.0.0.1', int(self.tcp_port))
                else:
                    self._reader, self._writer = await asyncio.open_unix_connection(self.socket_path)

                self.is_connected = True
                self._observer_task = safe_create_task(self._observe_events(), name="mpv_observer")
                if os.name != 'nt':
                    try:
                        import stat
                        os.chmod(self.socket_path, stat.S_IRUSR | stat.S_IWUSR)
                    except OSError:
                        pass
                logger.info(f"Connected to mpv (attempt {attempt + 1})")
                return
            except MpvConnectionError:
                raise
            except (ConnectionError, OSError, FileNotFoundError):
                await asyncio.sleep(0.5)
        raise MpvConnectionError(f"Cannot connect to mpv socket after 10 attempts (TCP: {os.environ.get('YT_PLAYER_MPV_PORT', 'N/A')}, Unix: {MPV_SOCKET})")

    async def play(self, url_or_path: str):
        if not self.is_connected:
            return
        await self._command(["loadfile", url_or_path, "replace"])

    async def pause(self):
        if not self.is_connected:
            return
        await self._set_property("pause", True)

    async def resume(self):
        if not self.is_connected:
            return
        await self._set_property("pause", False)

    async def toggle_pause(self):
        if not self.is_connected:
            return
        await self._command(["cycle", "pause"])

    async def set_volume(self, volume: int):
        if not self.is_connected:
            return
        await self._set_property("volume", max(0, min(MAX_VOLUME, volume)))

    async def get_position(self) -> float:
        if not self.is_connected:
            return 0.0
        val = await self._get_property("time-pos")
        return val if val else 0.0

    async def get_duration(self) -> float:
        if not self.is_connected:
            return 0.0
        val = await self._get_property("duration")
        return val if val else 0.0

    async def seek(self, seconds: float):
        if not self.is_connected:
            return
        await self._command(["seek", seconds, "absolute"])

    async def close(self):
        """Graceful cleanup."""
        self._shutting_down = True  # A-03b: cegah reconnect-publish saat shutdown normal
        self.is_connected = False
        if self._observer_task:
            self._observer_task.cancel()
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except OSError:
                pass

        if self._mpv_process:
            try:
                self._mpv_process.terminate()
                try:
                    await asyncio.wait_for(self._mpv_process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    self._mpv_process.kill()
            except OSError:
                pass

    async def _observe_events(self):
        """Event loop listener for mpv events (end-file, time-pos, etc)."""
        try:
            await self._command(["observe_property", 1, "time-pos"])
            await self._command(["observe_property", 2, "pause"])
            await self._command(["observe_property", 3, "duration"])

            while self.is_connected:
                try:
                    line = await self._reader.readline()
                    if not line:
                        break
                    msg = json.loads(line.decode())
                    await self._handle_event(msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                except (ConnectionError, OSError, asyncio.IncompleteReadError):
                    break
        finally:
            self.is_connected = False
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()
            self._pending.clear()
            logger.warning("mpv observer loop ended — connection lost.")

            if not getattr(self, "_shutting_down", False):
                reconnected = False
                for attempt in range(3):
                    backoff = 2 ** attempt
                    logger.info(f"Mencoba reconnect ke mpv (attempt {attempt + 1}/3) dalam {backoff}s...")
                    await asyncio.sleep(backoff)
                    if getattr(self, "_shutting_down", False):
                        break
                    try:
                        if os.name == "nt":
                            self._reader, self._writer = await asyncio.open_connection(
                                "127.0.0.1", int(self.tcp_port)
                            )
                        else:
                            self._reader, self._writer = await asyncio.open_unix_connection(
                                self.socket_path
                            )
                        self.is_connected = True
                        self._observer_task = safe_create_task(
                            self._observe_events(), name="mpv_observer"
                        )
                        logger.info(f"Reconnect ke mpv berhasil (attempt {attempt + 1})")
                        reconnected = True
                        break
                    except (ConnectionError, OSError, FileNotFoundError) as e:
                        logger.warning(f"Reconnect attempt {attempt + 1} gagal: {e}")

                if not reconnected:
                    logger.error("Semua percobaan reconnect ke mpv gagal.")
                    from core.events import TrackEndedEvent
                    import asyncio as _aio
                    try:
                        loop = _aio.get_running_loop()
                        loop.create_task(self._bus.publish(TrackEndedEvent(reason="error")))
                    except RuntimeError:
                        pass

    async def _handle_event(self, message: dict):
        if "request_id" in message:
            future = self._pending.pop(message["request_id"], None)
            if future and not future.done():
                future.set_result(message.get("data"))
            return

        event = message.get("event")
        if event == "property-change":
            name = message.get("name")
            data = message.get("data")
            if name == "time-pos" and isinstance(data, (int, float)):
                await self._bus.publish(TrackProgressEvent(position=float(data)))
            elif name == "pause":
                await self._bus.publish(TrackPauseChangedEvent(is_paused=bool(data)))
            elif name == "duration" and isinstance(data, (int, float)):
                from core.events import TrackDurationEvent
                await self._bus.publish(TrackDurationEvent(duration=float(data)))
        elif event == "end-file":
            reason = message.get("reason", "")
            if reason in ("eof", "stop", "error"):
                await self._bus.publish(TrackEndedEvent(reason=reason))

    async def _send_request(self, command_payload: list):
        if not self.is_connected or not self._writer:
            return None
        loop = asyncio.get_running_loop()
        async with self._req_lock:
            self._request_id += 1
            request_id = self._request_id
            future = loop.create_future()
            self._pending[request_id] = future
        payload = json.dumps({"command": command_payload, "request_id": request_id}) + "\n"
        try:
            self._writer.write(payload.encode())
            await self._writer.drain()
            return await asyncio.wait_for(future, timeout=2.0)
        except (OSError, asyncio.TimeoutError):
            self._pending.pop(request_id, None)
            return None

    async def _command(self, command: list):
        return await self._send_request(command)

    async def _get_property(self, prop: str):
        return await self._send_request(["get_property", prop])

    async def _set_property(self, prop: str, value):
        await self._command(["set_property", prop, value])
