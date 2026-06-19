from textual.app import App, ComposeResult
from textual.containers import Vertical, Container, Horizontal
from textual.binding import Binding
from textual.widgets import Static
from core.state import AppState, PlaybackMode
from tui.components.player_bar import PlayerBar
from tui.components.nav_bar import NavBar, TabChanged
from tui.theme import (
    TAB_HOME, TAB_SEARCH, TAB_RADIO, TAB_QUEUE,
    BG_VOID, BG_PANEL, BG_ELEVATED, ACCENT_FIRE, TEXT_PRIMARY, TEXT_MUTED,
    STATUS_OK, STATUS_ERR, ACCENT_GOLD, BORDER
)
from tui.tabs.now_playing_tab import NowPlayingTab
from tui.tabs.search_tab import SearchTab
from tui.tabs.radio_tab import RadioTab
from tui.tabs.queue_tab import QueueTab
from tui.screens.help_screen import HelpScreen
from core.event_bus import (
    bus, LOG_MESSAGE, TRACK_STARTED, QUEUE_UPDATED, LYRICS_UPDATED,
    DOWNLOAD_COMPLETE, CMD_PREV, CMD_NEXT, CMD_TOGGLE_PAUSE, CMD_STOP,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_SET_MODE, CMD_QUIT
)

class YTGuiApp(App):
    CSS = f"""
    Screen {{
        layout: vertical;
        background: {BG_VOID};
        min-width: 40;
        min-height: 25;
    }}
    #content_area {{
        height: 1fr;
        width: 100%;
        background: transparent;
    }}
    #app_header {{
        height: 1;
        width: 100%;
        background: {ACCENT_FIRE};
        color: {TEXT_PRIMARY};
        text-style: bold;
    }}
    #header_left {{ width: 1fr; text-align: left; padding-left: 1; }}
    #header_right {{ width: 1fr; text-align: right; padding-right: 1; color: {STATUS_OK}; }}
    .section-title {{
        text-style: bold;
        color: {ACCENT_FIRE};
        margin-top: 1;
        margin-bottom: 1;
    }}
    .badge-baru {{
        background: {TEXT_PRIMARY};
        color: {BG_VOID};
        text-style: bold;
        padding: 0 1;
    }}

    /* ── Global Button Overrides ── */
    Button {{
        background: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: round {BORDER};
        text-style: bold;
        overflow: hidden;
    }}
    Button:hover {{
        background: {ACCENT_FIRE};
        color: {BG_VOID};
        border: round {ACCENT_FIRE};
    }}
    Button:focus {{
        border: round {ACCENT_FIRE};
    }}
    Button.-primary {{
        background: {ACCENT_FIRE};
        color: {BG_VOID};
        border: round {ACCENT_FIRE};
    }}
    Button.-primary:hover {{
        background: {TEXT_PRIMARY};
        color: {BG_VOID};
        border: round {TEXT_PRIMARY};
    }}
    Button.-error {{
        background: {STATUS_ERR};
        color: {TEXT_PRIMARY};
        border: round {STATUS_ERR};
    }}
    Button.-error:hover {{
        background: {TEXT_PRIMARY};
        color: {STATUS_ERR};
        border: round {TEXT_PRIMARY};
    }}
    Button.-success {{
        background: {STATUS_OK};
        color: {TEXT_PRIMARY};
        border: round {STATUS_OK};
    }}
    Button.-success:hover {{
        background: {TEXT_PRIMARY};
        color: {STATUS_OK};
        border: round {TEXT_PRIMARY};
    }}

    /* ── Global Input Overrides ── */
    Input {{
        background: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: round {BORDER};
    }}
    Input:focus {{
        border: round {ACCENT_FIRE};
    }}

    /* ── Global ListView Overrides ── */
    ListItem.--highlight {{
        background: {ACCENT_FIRE} 30%;
    }}
    ListView:focus > ListItem.--highlight {{
        background: {ACCENT_FIRE};
        color: {BG_VOID};
    }}
    """

    BINDINGS = [
        Binding("/", "search", "Search"),
        Binding("escape", "unfocus", "Unfocus", show=False),
        Binding("p", "pause", "Pause/Resume"),
        Binding("n", "next", "Next"),
        Binding("b", "prev", "Prev"),
        Binding("s", "stop", "Stop"),
        Binding("u", "vol_up", "Vol+"),
        Binding("d", "vol_down", "Vol-"),
        Binding("m", "download", "Download"),
        Binding("M", "download", "Download", show=False),
        Binding("r", "switch_radio", "Radio"),
        Binding("l", "toggle_lyrics", "Lyrics"),
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
    ]

    def __init__(self, state: AppState, ytdlp=None, db=None):
        super().__init__()
        self.state = state
        self.ytdlp = ytdlp
        self.db = db
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="app_header"):
            self.header_left = Static("yt termux player pro", id="header_left")
            self.header_right = Static("● online", id="header_right")
            yield self.header_left
            yield self.header_right
        
        with Vertical(id="content_area"):
            self.tab_home = NowPlayingTab(id=f"content_{TAB_HOME}")
            self.tab_search = SearchTab(id=f"content_{TAB_SEARCH}")
            self.tab_radio = RadioTab(id=f"content_{TAB_RADIO}")
            self.tab_queue = QueueTab(id=f"content_{TAB_QUEUE}")
            
            yield self.tab_home
            yield self.tab_search
            yield self.tab_radio
            yield self.tab_queue

        
        self.player_bar = PlayerBar(id="player_bar")
        yield self.player_bar
        
        self.nav_bar = NavBar(id="nav_bar")
        yield self.nav_bar

    async def on_mount(self) -> None:
        # Subscribe to domain events that require immediate UI updates
        bus.subscribe(LOG_MESSAGE, self._on_log_message)
        bus.subscribe(TRACK_STARTED, self._on_immediate_refresh)
        bus.subscribe(QUEUE_UPDATED, self._on_immediate_refresh)
        bus.subscribe(LYRICS_UPDATED, self._on_immediate_refresh)
        bus.subscribe(DOWNLOAD_COMPLETE, self._on_immediate_refresh)

        # Periodic refresh for progress bar
        self._refresh_timer = self.set_interval(0.3, self.refresh_ui)

        # Sync initial tab
        self._sync_tab_visibility()

    async def on_unmount(self) -> None:
        if self._refresh_timer:
            self._refresh_timer.stop()
        bus.unsubscribe(LOG_MESSAGE, self._on_log_message)
        bus.unsubscribe(TRACK_STARTED, self._on_immediate_refresh)
        bus.unsubscribe(QUEUE_UPDATED, self._on_immediate_refresh)
        bus.unsubscribe(LYRICS_UPDATED, self._on_immediate_refresh)
        bus.unsubscribe(DOWNLOAD_COMPLETE, self._on_immediate_refresh)

    def refresh_ui(self) -> None:
        # Update header
        if hasattr(self.state, 'is_online'):
            indicator = "● online" if self.state.is_online else "● offline"
            color = STATUS_OK if self.state.is_online else STATUS_ERR
            self.header_right.update(f"[{color}]{indicator}[/{color}]")
            
        self.player_bar.update_state(self.state)
        # Update current active tab
        if self.state.active_tab == TAB_HOME:
            self.tab_home.update_state(self.state)
        elif self.state.active_tab == TAB_RADIO:
            self.tab_radio.update_state(self.state)
        elif self.state.active_tab == TAB_QUEUE:
            self.tab_queue.update_state(self.state)

    async def _on_log_message(self, msg: str) -> None:
        # LOG_MESSAGE displayed in player_bar
        self.state.error_msg = msg
        self.call_from_thread(self.player_bar.info_line.update, f"ⓘ {msg}")

    async def _on_immediate_refresh(self, _data=None) -> None:
        self.call_from_thread(self.refresh_ui)

    def _sync_tab_visibility(self) -> None:
        self.tab_home.display = (self.state.active_tab == TAB_HOME)
        self.tab_search.display = (self.state.active_tab == TAB_SEARCH)
        self.tab_radio.display = (self.state.active_tab == TAB_RADIO)
        self.tab_queue.display = (self.state.active_tab == TAB_QUEUE)
        
        # Trigger on_show manually if needed for SearchTab auto-focus
        if self.state.active_tab == TAB_SEARCH:
            self.tab_search.on_show()

    async def on_tab_changed(self, event: TabChanged) -> None:
        self.state.active_tab = event.tab_id
        self._sync_tab_visibility()
        self.refresh_ui()

    async def action_search(self) -> None:
        # Pindah ke Search Tab via event lokal
        self.nav_bar.set_active_tab(TAB_SEARCH)
        self.post_message(TabChanged(TAB_SEARCH))

    async def action_unfocus(self) -> None:
        self.set_focus(None)

    async def action_pause(self) -> None:
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

    async def action_toggle_lyrics(self) -> None:
        if self.state.active_tab != TAB_QUEUE:
            self.nav_bar.set_active_tab(TAB_QUEUE)
            await self.on_tab_changed(TabChanged(TAB_QUEUE))
        if not self.tab_queue.lyrics_container.display:
            await self.tab_queue.action_toggle_lyrics()
        else:
            # If already on queue and displayed, just let it toggle
            if self.state.active_tab == TAB_QUEUE:
                await self.tab_queue.action_toggle_lyrics()

    async def action_switch_radio(self) -> None:
        new_mode = PlaybackMode.RADIO if self.state.playback_mode == PlaybackMode.QUEUE else PlaybackMode.QUEUE
        await bus.publish(CMD_SET_MODE, new_mode)

    async def action_quit(self) -> None:
        await bus.publish(CMD_QUIT)
        self.exit()

    async def action_help(self) -> None:
        self.push_screen(HelpScreen())
