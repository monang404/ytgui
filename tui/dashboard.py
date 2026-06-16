import asyncio
import time
import datetime
import logging
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input
from textual.binding import Binding
from textual import on

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
        grid-rows: auto 1fr auto;
        background: #11111b;
    }
    #search_input {
        column-span: 2;
        row-span: 1;
        margin: 1 2;
        border: tall #89b4fa;
        background: #1e1e2e;
    }
    #search_input:focus {
        border: double #cba6f7;
    }
    #left_col {
        column-span: 1;
        row-span: 1;
        height: 100%;
        min-height: 10;
        padding: 0 1;
    }
    #right_col {
        column-span: 1;
        row-span: 1;
        layout: vertical;
        height: 100%;
        min-height: 10;
        padding: 0 1;
    }
    #lyrics_panel, #queue_panel {
        height: 1fr;
        border: tall #313244;
        background: #1e1e2e;
        margin-bottom: 1;
    }
    #controls {
        column-span: 2;
        row-span: 1;
        height: auto;
        padding: 1;
        border-top: heavy #45475a;
        background: #181825;
    }
    .status-label {
        color: #a6e3a1;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #controls_row {
        layout: grid;
        grid-size: 4;
        grid-gutter: 1 2;
        grid-rows: auto;
        height: auto;
        align: center middle;
    }
    Button {
        width: 100%;
        min-width: 5;
        border: none;
        background: #313244;
        color: #cdd6f4;
    }
    Button:hover {
        background: #45475a;
        text-style: bold;
    }
    Button.-active {
        background: #89b4fa;
        color: #11111b;
    }
    #btn_quit {
        background: #f38ba8;
        color: #11111b;
    }
    #btn_quit:hover {
        background: #eba0ac;
    }
    OptionList {
        background: #1e1e2e;
        border: none;
    }
    OptionList:focus {
        border: blank;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search"),
        Binding("escape", "unfocus", "Unfocus"),
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
        yield Input(placeholder="Search song... ('/' to focus, 'ESC' to unfocus)", id="search_input")
        self.now_playing = NowPlayingPanel(id="left_col")
        self.queue_panel = QueuePanel(id="queue_panel")
        self.lyrics_panel = LyricsPanel(id="lyrics_panel")
        self.controls = ControlsPanel(id="controls")
        
        yield self.now_playing
        with Vertical(id="right_col"):
            yield self.queue_panel
            yield self.lyrics_panel
        yield self.controls
        yield Footer()

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

    @on(Input.Submitted, "#search_input")
    async def on_search_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            await bus.publish(CMD_SEARCH, query)
            event.input.value = ""
            self.set_focus(None)

    def _is_input_focused(self) -> bool:
        return isinstance(self.focused, Input)

    async def action_focus_search(self) -> None:
        input_widget = self.query_one("#search_input", Input)
        input_widget.focus()

    async def action_unfocus(self) -> None:
        if self._is_input_focused():
            self.set_focus(None)

    async def action_toggle_pause(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_TOGGLE_PAUSE)

    async def action_next(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_NEXT)

    async def action_prev(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_PREV)

    async def action_stop(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_STOP)

    async def action_vol_up(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_VOLUME_UP)

    async def action_vol_down(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_VOLUME_DOWN)

    async def action_download(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_DOWNLOAD)

    async def action_toggle_radio(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_TOGGLE_RADIO)

    async def action_toggle_lyrics(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_TOGGLE_LYRICS)

    async def action_quit(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_QUIT)
