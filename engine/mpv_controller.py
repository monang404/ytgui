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
        self._observer_task = None
        self.is_connected = False
        self._mpv_process = None
        self.socket_path = socket_path or MPV_SOCKET
        self.tcp_port = tcp_port or os.environ.get("YT_PLAYER_MPV_PORT", "12345")
        # TASK-3.3: Injected per-room bus (fallback ke global jika belum direfactor)
        if event_bus is None:
            from core.event_bus import bus as _global_bus
            event_bus = _global_bus
        self._bus = event_bus

    async def connect(self):
        import shutil
        
        ytdl_path = shutil.which("yt-dlp")
        ytdl_arg = f"--script-opts=ytdl_hook-ytdl_path={ytdl_path}" if ytdl_path else ""
        
        # Auto-spawn mpv in background
        common_args = [
            "--no-video", "--idle",
            "--ytdl-format=bestaudio/best",
            "--audio-pitch-correction=yes"
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
                # Poll sampai socket tersedia, max 5 detik
                # TASK-2.3 fix: gunakan self.socket_path (per-room), bukan MPV_SOCKET global
                for _ in range(50):
                    await asyncio.sleep(0.1)
                    if os.path.exists(self.socket_path):
                        break
            else:
                await asyncio.sleep(1.0)  # Windows pipe tidak bisa di-poll dengan cara sama
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
                        pass  # Bukan fatal jika chmod gagal
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
        paused = await self._get_property("pause")
        if paused is not None:
            await self._set_property("pause", not paused)

    async def set_volume(self, vol: int):
        if not self.is_connected:
            return
        await self._set_property("volume", max(0, min(150, vol)))

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

    async def _handle_event(self, msg: dict):
        if "request_id" in msg:
            fut = self._pending.pop(msg["request_id"], None)
            if fut and not fut.done():
                fut.set_result(msg.get("data"))
            return

        event = msg.get("event")
        if event == "property-change":
            name = msg.get("name")
            data = msg.get("data")
            if name == "time-pos" and isinstance(data, (int, float)):
                await self._bus.publish(TrackProgressEvent(position=float(data)))
            elif name == "pause":
                await self._bus.publish(TrackPauseChangedEvent(is_paused=bool(data)))
        elif event == "end-file":
            reason = msg.get("reason", "")
            if reason in ("eof", "stop", "error"):
                await self._bus.publish(TrackEndedEvent(reason=reason))

    async def _command(self, cmd: list) -> int:
        if not self.is_connected or not self._writer:
            return 0
        self._request_id += 1
        req_id = self._request_id
        payload = json.dumps({"command": cmd, "request_id": req_id}) + "\n"
        try:
            self._writer.write(payload.encode())
            await self._writer.drain()
        except OSError:
            self.is_connected = False
        return req_id

    async def _get_property(self, prop: str):
        if not self.is_connected:
            return None
        self._request_id += 1
        req_id = self._request_id
        loop = asyncio.get_running_loop()  # HIGH-03 fix
        fut = loop.create_future()
        self._pending[req_id] = fut
        payload = json.dumps({"command": ["get_property", prop], "request_id": req_id}) + "\n"
        try:
            self._writer.write(payload.encode())
            await self._writer.drain()
            return await asyncio.wait_for(fut, timeout=2.0)
        except (OSError, asyncio.TimeoutError):
            self._pending.pop(req_id, None)
            return None

    # CRITICAL-06 fix: This method was missing entirely
    async def _set_property(self, prop: str, value):
        await self._command(["set_property", prop, value])
