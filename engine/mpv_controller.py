import asyncio
import json
import logging
import os
from config import MPV_SOCKET
from core.event_bus import bus, TRACK_PROGRESS, TRACK_ENDED
from core.exceptions import MpvConnectionError

logger = logging.getLogger(__name__)

class MpvController:
    """
    Controls mpv via JSON IPC over a socket.
    Start mpv with: mpv --no-video --idle --input-ipc-server={socket}

    CRITICAL-03 fix: On Windows, falls back to TCP socket (localhost:port)
    if Unix sockets are not available.
    CRITICAL-06 fix: _set_property is now properly defined.
    MED-11: Basic reconnection support via is_connected flag.
    """

    def __init__(self):
        self._reader = None
        self._writer = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._observer_task = None
        self.is_connected = False

    async def connect(self):
        for attempt in range(10):
            try:
                if os.name == 'nt':
                    # CRITICAL-03: Windows fallback — try TCP first, then Unix
                    tcp_port = os.environ.get("YT_PLAYER_MPV_PORT", None)
                    if tcp_port:
                        self._reader, self._writer = await asyncio.open_connection(
                            '127.0.0.1', int(tcp_port)
                        )
                    else:
                        try:
                            self._reader, self._writer = await asyncio.open_unix_connection(MPV_SOCKET)
                        except (AttributeError, OSError):
                            raise MpvConnectionError(
                                "Unix sockets not supported on Windows. "
                                "Set YT_PLAYER_MPV_PORT env var for TCP, "
                                "or start mpv with: mpv --input-ipc-server=tcp://127.0.0.1:PORT"
                            )
                else:
                    self._reader, self._writer = await asyncio.open_unix_connection(MPV_SOCKET)
                
                self.is_connected = True
                self._observer_task = asyncio.create_task(self._observe_events())
                logger.info(f"Connected to mpv (attempt {attempt + 1})")
                return
            except (FileNotFoundError, ConnectionRefusedError):
                await asyncio.sleep(0.5)
            except MpvConnectionError:
                raise
            except Exception as e:
                raise MpvConnectionError(f"Failed to connect to mpv: {e}")
        raise MpvConnectionError(f"Cannot connect to mpv socket after 10 attempts: {MPV_SOCKET}")

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
            except Exception:
                pass

    async def _observe_events(self):
        """Event loop listener for mpv events (end-file, time-pos, etc)."""
        try:
            await self._command(["observe_property", 1, "time-pos"])
            await self._command(["observe_property", 2, "playback-time"])

            while self.is_connected:
                try:
                    line = await self._reader.readline()
                    if not line:
                        break
                    msg = json.loads(line.decode())
                    await self._handle_event(msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                except Exception:
                    break
        finally:
            self.is_connected = False
            logger.warning("mpv observer loop ended — connection lost.")

    async def _handle_event(self, msg: dict):
        if "request_id" in msg:
            fut = self._pending.pop(msg["request_id"], None)
            if fut and not fut.done():
                fut.set_result(msg.get("data"))
            return

        event = msg.get("event")
        if event == "property-change" and msg.get("name") == "time-pos":
            data = msg.get("data")
            if isinstance(data, (int, float)):
                await bus.publish(TRACK_PROGRESS, float(data))
        elif event == "end-file":
            reason = msg.get("reason", "")
            if reason in ("eof", "stop"):
                await bus.publish(TRACK_ENDED, {"reason": reason})

    async def _command(self, cmd: list) -> int:
        if not self.is_connected or not self._writer:
            return 0
        self._request_id += 1
        req_id = self._request_id
        payload = json.dumps({"command": cmd, "request_id": req_id}) + "\n"
        try:
            self._writer.write(payload.encode())
            await self._writer.drain()
        except Exception:
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
        except Exception:
            self._pending.pop(req_id, None)
            return None

    # CRITICAL-06 fix: This method was missing entirely
    async def _set_property(self, prop: str, value):
        await self._command(["set_property", prop, value])
