"""
Purpose: Mirrors current playback state to an Android notification via
         termux-notification (MediaStyle), and relays button presses back
         into the EventBus through a FIFO. No-op automatically on any
         platform where the termux-notification binary is not present.
Subscribes to: TRACK_STARTED, "track.pause.changed"
Publishes: CMD_PREV, CMD_NEXT, CMD_TOGGLE_PAUSE
"""

import asyncio
import logging
import os
import shutil
import threading
import time

from core.event_bus import EventBus, TRACK_STARTED
from core.command_bus import command_bus, CMD_PREV, CMD_NEXT, CMD_TOGGLE_PAUSE
from core.state import TrackInfo
from config import BASE_DIR

logger = logging.getLogger(__name__)

NOTIFICATION_ID = "ytgui_nowplaying"
_SOCK_DIR = BASE_DIR / "cache" / "sockets"
_FIFO_PATH = _SOCK_DIR / "nowplaying.fifo"
_SHEBANG = "#!/data/data/com.termux/files/usr/bin/bash"
_TOKEN_TO_EVENT = {
    "prev": CMD_PREV,
    "next": CMD_NEXT,
    "toggle": CMD_TOGGLE_PAUSE,
}


class TermuxNowPlaying:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self._track: TrackInfo | None = None
        self._paused = False
        self._available = False
        self._loop = None
        self._stop = threading.Event()
        self._reader_thread = None
        self._fifo_path = _FIFO_PATH
        self._action_paths = {}

        self.bus.subscribe(TRACK_STARTED, self._on_track_started)
        self.bus.subscribe("track.pause.changed", self._on_pause_changed)

    async def start(self):
        if not shutil.which("termux-notification"):
            logger.info("termux-notification not found, now-playing notification disabled.")
            return

        self._available = True
        self._loop = asyncio.get_running_loop()

        try:
            _SOCK_DIR.mkdir(parents=True, exist_ok=True)
            if self._fifo_path.exists():
                self._fifo_path.unlink()
            os.mkfifo(str(self._fifo_path))

            # Write one tiny standalone script per action — the notification
            # action string must be a single bare path, no quotes/redirects,
            # since the action runner is not guaranteed to use real shell parsing.
            for token in ("prev", "toggle", "next"):
                script_path = _SOCK_DIR / f"np_{token}.sh"
                script_path.write_text(
                    f"{_SHEBANG}\necho '{token}' > '{self._fifo_path}' 2>/dev/null\n"
                )
                script_path.chmod(0o755)
                self._action_paths[token] = str(script_path)
        except OSError as e:
            logger.warning(f"Failed to set up now-playing notification: {e}")
            self._available = False
            return

        self._reader_thread = threading.Thread(target=self._blocking_read_loop, daemon=True)
        self._reader_thread.start()

    def _blocking_read_loop(self):
        while not self._stop.is_set():
            try:
                with open(self._fifo_path, "r") as f:
                    for line in f:
                        token = line.strip()
                        if token and self._loop:
                            asyncio.run_coroutine_threadsafe(self._handle_token(token), self._loop)
            except FileNotFoundError:
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Now-playing FIFO reader error: {e}")
                time.sleep(1)

    async def _handle_token(self, token: str):
        event = _TOKEN_TO_EVENT.get(token)
        if event:
            await command_bus.execute(event)

    async def _on_track_started(self, track: TrackInfo):
        self._track = track
        self._paused = False
        await self._render()

    async def _on_pause_changed(self, paused: bool):
        self._paused = bool(paused)
        if self._track:
            await self._render()

    async def _render(self):
        if not self._available or not self._track:
            return

        title = self._track.title or "YTGUI"
        artist = self._track.artist or "Now playing"

        args = [
            "termux-notification",
            "--id", NOTIFICATION_ID,
            "--type", "media",
            "-t", title,
            "-c", artist,
            "--media-previous", self._action_paths["prev"],
            "--media-play", self._action_paths["toggle"],
            "--media-pause", self._action_paths["toggle"],
            "--media-next", self._action_paths["next"],
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
        except Exception as e:
            logger.warning(f"termux-notification render failed: {e}")

    async def cleanup(self):
        self._stop.set()
        if self._available:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "termux-notification-remove", "--id", NOTIFICATION_ID,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
            except Exception:
                pass
        try:
            if self._fifo_path.exists():
                self._fifo_path.unlink()
            for p in self._action_paths.values():
                pathlib_p = __import__("pathlib").Path(p)
                if pathlib_p.exists():
                    pathlib_p.unlink()
        except Exception:
            pass
