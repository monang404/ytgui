import asyncio
import time
import datetime
import logging
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input, TabbedContent, TabPane
from textual.binding import Binding
from textual import on
from textual.events import Resize

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
        background: #0D0D0D;
        color: #E8E8FF;
    }
    
    /* PORTRAIT MODE (Default Stacked) */
    Screen.-portrait {
        layout: vertical;
    }
    Screen.-portrait #search_input { width: 100%; height: 3; margin-bottom: 1; }
    Screen.-portrait #now_playing { width: 100%; height: auto; }
    Screen.-portrait #tabs_container { width: 100%; height: 1fr; }
    Screen.-portrait #controls { width: 100%; height: auto; }

    /* LANDSCAPE MODE (Grid) */
    Screen.-landscape {
        layout: grid;
        grid-size: 3 3;
        grid-columns: 1fr 1fr 1fr;
        grid-rows: auto 1fr auto;
    }
    Screen.-landscape #search_input { column-span: 3; row-span: 1; height: 3; }
    Screen.-landscape #now_playing { column-span: 1; row-span: 1; height: 100%; margin-right: 1; }
    Screen.-landscape #tabs_container { column-span: 2; row-span: 1; height: 100%; }
    Screen.-landscape #controls { column-span: 3; row-span: 1; height: auto; }

    /* SHARED COMPONENT STYLES */
    #search_input {
        border: tall #2a2a45;
        background: #1E1E30;
        color: #E8E8FF;
    }
    #search_input:focus { border: tall #FFC107; }
    
    #now_playing {
        border: tall #1E1E30;
        background: #141420;
    }
    
    TabbedContent {
        height: 100%;
    }
    TabPane {
        padding: 0;
        border: tall #1E1E30;
        background: #141420;
    }
    
    #controls {
        padding: 1;
        border-top: solid #1E1E30;
        background: #0D0D0D;
    }
    .status-label {
        color: #4ade80;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .controls-row {
        height: 3;
        margin-bottom: 1;
    }
    .primary-actions Button { width: 1fr; }
    .primary-actions .double-width { width: 2fr; }
    .secondary-actions Button { width: 1fr; min-width: 3; }
    .destructive-actions { height: 3; }
    .destructive-actions .spacer { width: 1fr; }
    .destructive-actions Button { width: 20; }
    Button {
        width: 100%;
        min-width: 5;
        border: none;
        background: #1E1E30;
        color: #A0A0C0;
    }
    Button:hover {
        background: #2a2a45;
        color: #E8E8FF;
    }
    Button.-active {
        background: #FFC107;
        color: #1E1E30;
    }
    #btn_pause {
        background: #FF6B35;
        color: #FFFFFF;
        text-style: bold;
    }
    #btn_pause:hover {
        background: #ff7d4a;
    }
    #btn_quit {
        background: #1E1E30;
        color: #ef4444;
    }
    #btn_quit:hover {
        background: #ef4444;
        color: #FFFFFF;
    }
    OptionList {
        background: #141420;
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
        yield Input(placeholder="Search... ('/' to focus, 'ESC' unfocus)", id="search_input")
        
        self.now_playing = NowPlayingPanel(id="now_playing")
        yield self.now_playing
        
        with TabbedContent(initial="queue-tab", id="tabs_container"):
            with TabPane("Antrean", id="queue-tab"):
                self.queue_panel = QueuePanel(id="queue_panel")
                yield self.queue_panel
            with TabPane("Lirik", id="lyrics-tab"):
                self.lyrics_panel = LyricsPanel(id="lyrics_panel")
                yield self.lyrics_panel
                
        self.controls = ControlsPanel(id="controls")
        yield self.controls
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "YT TERMUX PLAYER PRO"
        bus.subscribe(LOG_MESSAGE, self._on_log_message)
        bus.subscribe(CMD_QUIT, self._on_cmd_quit)
        
        self.screen.add_class("-portrait")
        
        # 3 fps refresh
        self.set_interval(0.3, self.refresh_ui)

    def on_resize(self, event: Resize) -> None:
        if event.size.width >= 80:
            self.screen.add_class("-landscape")
            self.screen.remove_class("-portrait")
        else:
            self.screen.add_class("-portrait")
            self.screen.remove_class("-landscape")

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
        self.now_playing.status_msg = status_text

        # Update panels
        self.now_playing.update_state(self.state)
        self.queue_panel.update_state(self.state)
        self.lyrics_panel.update_state(self.state)

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
        tabs = self.query_one(TabbedContent)
        if tabs.active == "lyrics-tab":
            tabs.active = "queue-tab"
        else:
            tabs.active = "lyrics-tab"

    async def action_quit(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_QUIT)
