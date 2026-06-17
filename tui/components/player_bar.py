from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual import events, on
from textual.containers import Horizontal
from core.state import AppState, PlayerStatus, PlaybackMode
from tui.theme import STATUS_ERR
from core.event_bus import bus, CMD_PREV, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD
from tui.components.progress_bar import ClickableProgressBar
from rich.markup import escape

class PlayerBar(Widget):
    DEFAULT_CSS = """
    PlayerBar {
        height: auto;
        dock: bottom;
        background: $boost;
        layout: vertical;
        padding: 1 2;
    }
    #pb_controls {
        height: 1;
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

    Static.player-btn {
        width: auto;
        height: 1;
        padding: 0 2;
        background: transparent;
        color: $text;
        margin: 0;
    }
    Static.player-btn:hover {
        background: $panel;
        color: $accent;
        text-style: bold;
    }
    Static.main-btn {
        height: 1;
        content-align: center middle;
        padding: 0 2;
        background: transparent;
        border: none;
    }
    Static.main-btn:hover {
        color: $accent;
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
            self.btn_prev = Static(" |◁ ", id="btn_prev", classes="player-btn main-btn")
            self.btn_play = Static(" ▷ ", id="btn_play", classes="player-btn main-btn")
            self.btn_next = Static(" ▷| ", id="btn_next", classes="player-btn main-btn")
            yield self.btn_prev
            yield self.btn_play
            yield self.btn_next

        with Horizontal(id="pb_meta_row"):
            with Horizontal(classes="meta-left", id="pb_vol_container"):
                self.btn_voldown = Static("🔉", id="btn_voldown", classes="player-btn")
                self.btn_volup = Static("🔊 80%", id="btn_volup", classes="player-btn")
                yield self.btn_voldown
                yield self.btn_volup
            self.badge_cache = Static("", id="pb_badge_cache", classes="meta-center")
            self.btn_download = Static("⬇ unduh", id="btn_download", classes="meta-right player-btn")
            yield self.badge_cache
            yield self.btn_download

    @on(events.Click, ".player-btn")
    async def on_player_btn_click(self, event: events.Click) -> None:
        btn_id = event.control.id
        if btn_id == "btn_prev":
            await bus.publish(CMD_PREV)
        elif btn_id == "btn_play":
            await bus.publish(CMD_TOGGLE_PAUSE)
        elif btn_id == "btn_next":
            await bus.publish(CMD_NEXT)
        elif btn_id == "btn_download":
            await bus.publish(CMD_DOWNLOAD)
        elif btn_id == "btn_voldown":
            await bus.publish(CMD_VOLUME_DOWN)
        elif btn_id == "btn_volup":
            await bus.publish(CMD_VOLUME_UP)

    def update_state(self, state: AppState) -> None:
        if state.playback_mode == PlaybackMode.RADIO:
            self.badge_mode.update("[bold #FFA500]📻 radio[/]")
        else:
            self.badge_mode.update("[bold #555580]≡ queue[/]")
            
        t = state.current_track
        if t:
            if t.local_path:
                self.badge_cache.update("[bold #4ade80]✓ tersimpan[/]")
            else:
                self.badge_cache.update("[bold #A0A0C0]☁ stream[/]")
        else:
            self.badge_cache.update("")

        # Update Volume
        self.btn_volup.update(f"🔊 {state.volume}%")

        # Update Download
        if state.download_progress is not None:
            pct = int(state.download_progress * 100)
            self.btn_download.update(f"⬇ {pct}%")
        else:
            self.btn_download.update("⬇ unduh")

        if state.status == PlayerStatus.IDLE:
            self.info_line.update("Ketuk Radio untuk mulai ▶")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.btn_play.update(" ▷ ")
        elif state.status == PlayerStatus.LOADING:
            track_name = state.current_track.title if state.current_track else ""
            self.info_line.update(f"⏳ memuat... {escape(track_name)}")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.btn_play.update("[#FFA500] || [/]")
        elif state.status == PlayerStatus.PLAYING:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.update("[#FFA500] || [/]")
        elif state.status == PlayerStatus.PAUSED:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.update(" ▷ ")
        elif state.status == PlayerStatus.ERROR:
            msg = state.error_msg or "Terjadi kesalahan"
            self.info_line.update(f"[{STATUS_ERR}]{escape(msg)}[/]")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
