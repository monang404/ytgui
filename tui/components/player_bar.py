from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal
from core.state import AppState, PlayerStatus, PlaybackMode
from tui.theme import HEIGHT_PLAYER_BAR, STATUS_ERR
from core.event_bus import bus, CMD_PREV, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD
from tui.components.progress_bar import ClickableProgressBar
from rich.markup import escape

class PlayerBar(Widget):
    DEFAULT_CSS = """
    PlayerBar {
        height: auto;
        dock: bottom;
        background: $boost;
        padding: 1 1;
    }
    #pb_controls {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    #pb_title_row { height: 1; }
    #pb_title_row #pb_info { width: 1fr; }
    #pb_title_row #pb_badge_mode { width: auto; color: $accent; }

    #pb_meta_row { height: 1; margin-top: 1; }
    .meta-left   { width: 1fr; text-align: left; color: $text-muted; }
    .meta-center { width: 1fr; text-align: center; color: $success; }
    .meta-right  { width: 1fr; text-align: right; }
    
    #pb_vol_container {
        width: 1fr;
        height: 1;
        layout: horizontal;
    }

    Button.player-btn {
        min-width: 5;
        min-height: 1;
        height: 1;
        border: none;
        padding: 0 1;
        background: transparent;
    }
    Button.player-btn:hover {
        background: $accent;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="pb_title_row"):
            self.info_line = Static("Ketuk Radio untuk mulai ▶", id="pb_info")
            self.badge_mode = Static("[bold #555580][○] QUEUE[/]", id="pb_badge_mode")
            yield self.info_line
            yield self.badge_mode

        self.progress_bar = ClickableProgressBar(id="pb_progress")
        yield self.progress_bar

        with Horizontal(id="pb_controls"):
            self.btn_prev = Button("⏮", id="btn_prev", classes="player-btn")
            self.btn_play = Button("⏯", id="btn_play", classes="player-btn")
            self.btn_next = Button("⏭", id="btn_next", classes="player-btn")
            yield self.btn_prev
            yield self.btn_play
            yield self.btn_next

        with Horizontal(id="pb_meta_row"):
            with Horizontal(classes="meta-left", id="pb_vol_container"):
                self.btn_voldown = Button("⏬", id="btn_voldown", classes="player-btn")
                self.btn_volup = Button("⏫", id="btn_volup", classes="player-btn")
                yield self.btn_voldown
                yield self.btn_volup
            self.badge_cache = Static("", id="pb_badge_cache", classes="meta-center")
            self.btn_download = Button("⬇", id="btn_download", classes="meta-right player-btn")
            yield self.badge_cache
            yield self.btn_download

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_prev":
            await bus.publish(CMD_PREV)
        elif event.button.id == "btn_play":
            await bus.publish(CMD_TOGGLE_PAUSE)
        elif event.button.id == "btn_next":
            await bus.publish(CMD_NEXT)
        elif event.button.id == "btn_download":
            await bus.publish(CMD_DOWNLOAD)
        elif event.button.id == "btn_voldown":
            await bus.publish(CMD_VOLUME_DOWN)
        elif event.button.id == "btn_volup":
            await bus.publish(CMD_VOLUME_UP)

    def update_state(self, state: AppState) -> None:
        if state.playback_mode == PlaybackMode.RADIO:
            self.badge_mode.update("[bold #FF6B35][●] RADIO[/]")
        else:
            self.badge_mode.update("[bold #555580][○] QUEUE[/]")
            
        t = state.current_track
        if t:
            if t.local_path:
                self.badge_cache.update("[bold #4ade80]✓ Cached[/]")
            else:
                self.badge_cache.update("[bold #A0A0C0]☁ Stream[/]")
        else:
            self.badge_cache.update("")

        if state.status == PlayerStatus.IDLE:
            self.info_line.update("Ketuk Radio untuk mulai ▶")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.btn_play.label = "▶"
        elif state.status == PlayerStatus.LOADING:
            track_name = state.current_track.title if state.current_track else ""
            self.info_line.update(f"⏳ Memuat... {escape(track_name)}")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.btn_play.label = "⏸"
        elif state.status == PlayerStatus.PLAYING:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.label = "⏸"
        elif state.status == PlayerStatus.PAUSED:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.label = "▶ RESUME"
        elif state.status == PlayerStatus.ERROR:
            msg = state.error_msg or "Terjadi kesalahan"
            self.info_line.update(f"[{STATUS_ERR}]{escape(msg)}[/]")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
