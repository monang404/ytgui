import asyncio
import time
import datetime
import logging
from textual.app import App, ComposeResult
from textual.containers import Grid, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Input, Button
from textual.binding import Binding
from textual import on
from textual.events import Resize
from tui.theme import *

from core.event_bus import (
    bus, LOG_MESSAGE, CMD_QUIT, CMD_SEARCH, CMD_FOCUS_SEARCH, CMD_UNFOCUS,
    CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_VOLUME_UP, CMD_VOLUME_DOWN,
    CMD_DOWNLOAD, CMD_TOGGLE_RADIO, CMD_TOGGLE_LYRICS,
    QUEUE_UPDATED, TRACK_STARTED, LYRICS_UPDATED, DOWNLOAD_COMPLETE
)
from core.state import AppState, PlayerStatus
from tui.panels.now_playing import NowPlayingPanel
from tui.panels.queue_panel import QueuePanel
from tui.panels.lyrics_panel import LyricsPanel
from tui.panels.controls import ControlsPanel

logger = logging.getLogger(__name__)

class Dashboard(App):
    """The main Textual application for YTCLI."""

    CSS = f"""
    Screen {{
        layout: vertical;
        background: {BG_VOID};
        color: {TEXT_PRIMARY};
        height: 100%;
    }}
    
    #top_bar {{
        height: 3;
        margin-bottom: 1;
    }}
    #search_input {{
        width: 1fr;
        border: tall {BORDER};
        background: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
    }}
    #search_input:focus {{ border: tall {BORDER_FOCUS}; }}
    
    #online_indicator {{
        width: 3;
        content-align: center middle;
        margin-left: 1;
    }}

    #main_grid {{
        height: 1fr;
        width: 100%;
    }}
    .-portrait #main_grid {{ layout: vertical; }}
    .-landscape #main_grid {{ layout: horizontal; }}

    #now_playing {{ 
        height: 13; 
        width: 100%; 
        border: tall {BORDER}; 
        background: {BG_PANEL}; 
        padding: 1 2;
    }}
    Screen.-compact #now_playing {{
        height: 8;
    }}
    .-landscape #now_playing {{ 
        width: 38%; 
        height: 1fr; 
        margin-right: 1; 
    }}

    #side_panel {{ 
        height: 1fr; 
        width: 100%; 
    }}
    .-landscape #side_panel {{ 
        width: 62%; 
    }}

    #controls_primary {{
        height: 3;
        align: center middle;
    }}
    #btn_pause {{
        width: 1fr;
        background: {ACCENT_FIRE};
        color: #FFFFFF;
        text-style: bold;
    }}
    #btn_pause:hover {{ background: #ff7d4a; }}
    #btn_prev, #btn_next {{
        width: 20%;
    }}

    #controls_secondary {{
        layout: grid;
        grid-size: 6;
        grid-gutter: 1;
        height: 3;
        margin-top: 1;
    }}

    #controls_danger {{
        align: right middle;
        height: 3;
        margin-top: 1;
    }}
    #btn_quit {{
        width: 16;
        border: tall #3a1a1a;
        background: {BG_ELEVATED};
        color: {STATUS_ERR};
    }}
    #btn_quit:hover {{
        background: {STATUS_ERR};
        color: #FFFFFF;
    }}
    
    Button {{
        width: 100%;
        background: {BG_ELEVATED};
        color: {TEXT_MUTED};
    }}
    Button:hover {{
        background: {BORDER};
        color: {TEXT_PRIMARY};
    }}
    Button.-active {{
        background: {ACCENT_GOLD};
        color: {BG_ELEVATED};
    }}

    OptionList {{
        background: {BG_PANEL};
        border: none;
    }}
    OptionList:focus {{
        border: tall {BORDER_FOCUS};
    }}

    /* MANUAL TABS */
    #tab_bar {{
        height: 3;
        width: 100%;
        margin-bottom: 1;
    }}
    .tab-btn {{
        width: 1fr;
        min-width: 10;
        height: 3;
        border: none;
        background: {BG_ELEVATED};
        color: {TEXT_MUTED};
    }}
    .tab-btn.-active {{
        background: {BG_PANEL};
        color: {ACCENT_GOLD};
        border: tall {ACCENT_GOLD};
    }}

    #lyrics_panel, #queue_panel {{
        height: 1fr;
        border: tall {BORDER};
        background: {BG_PANEL};
    }}
    
    #controls {{
        height: 11;
        background: {BG_VOID};
    }}
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
        
        with Horizontal(id="top_bar"):
            yield Input(placeholder="Search... ('/' focus, 'ESC' unfocus)", id="search_input")
            self.online_dot = Static("●", id="online_indicator")
            yield self.online_dot

        with Vertical(id="main_grid"):
            self.now_playing = NowPlayingPanel(id="now_playing")
            yield self.now_playing
            
            with Vertical(id="side_panel"):
                with Horizontal(id="tab_bar"):
                    yield Button("Antrean", id="tab_btn_queue", classes="tab-btn -active")
                    yield Button("Lirik", id="tab_btn_lyrics", classes="tab-btn")
                
                self.queue_panel = QueuePanel(id="queue_panel")
                self.lyrics_panel = LyricsPanel(id="lyrics_panel")
                yield self.queue_panel
                yield self.lyrics_panel
                
        self.controls = ControlsPanel(id="controls")
        yield self.controls
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "YT TERMUX PLAYER PRO"
        bus.subscribe(LOG_MESSAGE, self._on_log_message)
        bus.subscribe(CMD_QUIT, self._on_cmd_quit)
        bus.subscribe("cmd.switch.lyrics.tab", self._on_switch_lyrics_tab)
        bus.subscribe(QUEUE_UPDATED, self._on_queue_updated)
        bus.subscribe(TRACK_STARTED, self._on_track_started)
        bus.subscribe(LYRICS_UPDATED, self._on_lyrics_updated)
        bus.subscribe(DOWNLOAD_COMPLETE, self._on_download_complete)
        
        # Initial layout mode sync
        is_landscape = self.size.width >= BREAKPOINT_LANDSCAPE
        is_short = self.size.height < 35
        self.screen.set_class(is_landscape, "-landscape")
        self.screen.set_class(not is_landscape, "-portrait")
        self.screen.set_class(is_short, "-compact")
        
        # Initial tab sync
        self._active_tab = "queue"
        self._sync_tab_visibility()

        # 3 fps refresh
        self.set_interval(0.3, self.refresh_ui)

    def on_resize(self, event: Resize) -> None:
        is_landscape = event.size.width >= BREAKPOINT_LANDSCAPE
        is_short = event.size.height < 35
        self.screen.set_class(is_landscape, "-landscape")
        self.screen.set_class(not is_landscape, "-portrait")
        self.screen.set_class(is_short, "-compact")

    @on(Button.Pressed, "#tab_btn_queue")
    def _show_queue_tab(self, event=None) -> None:
        self._active_tab = "queue"
        self._sync_tab_visibility()

    @on(Button.Pressed, "#tab_btn_lyrics")
    def _show_lyrics_tab(self, event=None) -> None:
        self._active_tab = "lyrics"
        self._sync_tab_visibility()

    def _sync_tab_visibility(self) -> None:
        self.queue_panel.display = (self._active_tab == "queue")
        self.lyrics_panel.display = (self._active_tab == "lyrics")
        self.query_one("#tab_btn_queue").set_class(self._active_tab == "queue", "-active")
        self.query_one("#tab_btn_lyrics").set_class(self._active_tab == "lyrics", "-active")

    def refresh_ui(self) -> None:
        # Check if status msg expired
        if self._status_msg and (time.time() - self._status_msg_time > 5.0):
            self._status_msg = ""
            self.now_playing.status_line.update("")

        # Update online indicator
        color = STATUS_OK if self.state.is_online else STATUS_ERR
        self.online_dot.update(f"[{color}]●[/]")

        # Update panels (always update both so background data is fresh)
        self.now_playing.update_state(self.state)
        self.queue_panel.update_state(self.state)
        self.lyrics_panel.update_state(self.state)

        # Sync tombol pause/resume berdasarkan state
        try:
            btn = self.query_one("#btn_pause", Button)
            if self.state.status == PlayerStatus.PAUSED:
                btn.label = "▶  RESUME"
            elif self.state.status == PlayerStatus.LOADING:
                btn.label = "⏳  LOADING..."
            elif self.state.status == PlayerStatus.PLAYING:
                btn.label = "⏸  PAUSE"
            else:
                btn.label = "⏯  PLAY / PAUSE"
            
            # Sync tombol Radio active state
            btn_radio = self.query_one("#btn_radio", Button)
            btn_radio.set_class(self.state.is_radio_mode, "-active")
        except Exception:
            pass  # Widget belum mount saat pertama kali

    async def _on_log_message(self, msg: str) -> None:
        self._status_msg = str(msg)
        self._status_msg_time = time.time()
        if hasattr(self.now_playing, 'status_line'):
            self.now_playing.status_line.update(f"[{ACCENT_GOLD}]{msg}[/]")
        self.refresh_ui()

    async def _on_cmd_quit(self, _) -> None:
        self.exit()

    async def _on_switch_lyrics_tab(self, _=None):
        if self._active_tab == "queue":
            self._show_lyrics_tab()
        else:
            self._show_queue_tab()

    async def _on_queue_updated(self, _=None):
        self.queue_panel.update_state(self.state)

    async def _on_track_started(self, track=None):
        self.now_playing.update_state(self.state)
        self.queue_panel.update_state(self.state)

    async def _on_lyrics_updated(self, _=None):
        self.lyrics_panel.update_state(self.state)

    async def _on_download_complete(self, track=None):
        self.now_playing.update_state(self.state)

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
        if self._active_tab == "queue":
            self._show_lyrics_tab()
        else:
            self._show_queue_tab()

    async def action_quit(self) -> None:
        if self._is_input_focused(): return
        await bus.publish(CMD_QUIT)
