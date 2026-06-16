import asyncio
import time
import datetime
import logging
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
from textual.binding import Binding

from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH, CMD_FOCUS_SEARCH, CMD_UNFOCUS,
    CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_VOLUME_UP, CMD_VOLUME_DOWN,
    CMD_DOWNLOAD, CMD_TOGGLE_RADIO, CMD_TOGGLE_LYRICS
)
from core.state import AppState
from tui.panels.now_playing import NowPlayingPanel
from tui.panels.queue_panel import QueuePanel
from tui.panels.lyrics_panel import LyricsPanel
from tui.panels.controls import ControlsPanel

logger = logging.getLogger(__name__)

class Dashboard(App):
    """The main Textual application for YTCLI."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 5;
    }
    #left_col {
        column-span: 1;
        row-span: 1;
    }
    #right_col {
        column-span: 1;
        row-span: 1;
        layout: vertical;
    }
    #lyrics_panel {
        height: 1fr;
    }
    #queue_panel {
        height: 1fr;
    }
    #controls {
        column-span: 2;
        row-span: 1;
        height: auto;
        padding: 1;
        border: solid #FFC107;
    }
    .status-label {
        color: #FFC107;
        text-align: center;
        margin-bottom: 1;
    }
    #controls_row {
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("p", "toggle_pause", "Play/Pause"),
        Binding("n", "next", "Next"),
        Binding("b", "prev", "Prev"),
        Binding("s", "stop", "Stop"),
        Binding("u", "vol_up", "Vol +"),
        Binding("d", "vol_down", "Vol -"),
        Binding("m", "download", "Download"),
        Binding("r", "toggle_radio", "Radio"),
        Binding("l", "toggle_lyrics", "Lyrics"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self._status_msg = ""
        self._status_msg_time = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.now_playing = NowPlayingPanel(id="left_col")
        self.queue_panel = QueuePanel(id="queue_panel")
        self.lyrics_panel = LyricsPanel(id="lyrics_panel")
        self.controls = ControlsPanel(id="controls")
        
        yield self.now_playing
        with Vertical(id="right_col"):
            yield self.queue_panel
            yield self.lyrics_panel
        yield self.controls

    async def on_mount(self) -> None:
        self.title = "YT TERMUX PLAYER PRO"
        bus.subscribe(LOG_MESSAGE, self._on_log_message)
        bus.subscribe(CMD_QUIT, self._on_cmd_quit)
        
        # 3 fps refresh
        self.set_interval(0.3, self.refresh_ui)

    def refresh_ui(self) -> None:
        # Check if status msg expired
        if self._status_msg and (time.time() - self._status_msg_time > 5.0):
            self._status_msg = ""

        # Update controls status
        if self.state.is_online:
            online_str = "[ONLINE]"
        else:
            online_str = "[OFFLINE]"
        
        status_text = f"{online_str} {self._status_msg}"
        self.controls.status_msg = status_text

        # Update panels
        self.now_playing.update_state(self.state)
        self.queue_panel.update_state(self.state)
        
        if self.state.show_lyrics:
            self.lyrics_panel.display = True
            self.lyrics_panel.update_state(self.state)
        else:
            self.lyrics_panel.display = False

    async def _on_log_message(self, msg: str) -> None:
        self._status_msg = str(msg)
        self._status_msg_time = time.time()
        self.refresh_ui()

    async def _on_cmd_quit(self, _) -> None:
        self.exit()

    async def action_toggle_pause(self) -> None:
        await bus.publish(CMD_TOGGLE_PAUSE)

    async def action_next(self) -> None:
        await bus.publish(CMD_NEXT)

    async def action_prev(self) -> None:
        await bus.publish(CMD_PREV)

    async def action_stop(self) -> None:
        await bus.publish(CMD_STOP)

    async def action_vol_up(self) -> None:
        await bus.publish(CMD_VOLUME_UP)

    async def action_vol_down(self) -> None:
        await bus.publish(CMD_VOLUME_DOWN)

    async def action_download(self) -> None:
        await bus.publish(CMD_DOWNLOAD)

    async def action_toggle_radio(self) -> None:
        await bus.publish(CMD_TOGGLE_RADIO)

    async def action_toggle_lyrics(self) -> None:
        await bus.publish(CMD_TOGGLE_LYRICS)

    async def action_quit(self) -> None:
        await bus.publish(CMD_QUIT)
