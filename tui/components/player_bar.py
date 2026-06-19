from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual import events, on
from textual.containers import Horizontal
from core.state import AppState, PlayerStatus, PlaybackMode
from tui.theme import STATUS_ERR, BG_ELEVATED, BG_PANEL, ACCENT_FIRE, TEXT_PRIMARY, TEXT_MUTED, STATUS_OK, BG_VOID
from tui.theme import STATUS_ERR, BG_ELEVATED, BG_PANEL, ACCENT_FIRE, TEXT_PRIMARY, TEXT_MUTED, STATUS_OK, BG_VOID, BORDER
from core.event_bus import bus, CMD_PREV, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD
from tui.components.progress_bar import ClickableProgressBar
from rich.markup import escape

class PlayerBar(Widget):
    DEFAULT_CSS = f"""
    PlayerBar {{
        height: 14;
        dock: bottom;
        background: transparent;
        border-top: solid {BORDER};
        layout: vertical;
        padding: 1 2;
    }}
    #pb_title_row {{ height: 1; }}
    #pb_title_row #pb_info {{ width: 1fr; }}
    #pb_title_row #pb_seek_hint {{ width: auto; margin-right: 2; }}
    #pb_title_row #pb_badge_mode {{ width: auto; color: {ACCENT_FIRE}; }}

    #pb_controls {{
        height: 3;
        align: center middle;
    }}

    #pb_meta_row {{ height: 1; margin-top: 1; }}
    .meta-left   {{ width: 1fr; text-align: left; color: {TEXT_MUTED}; }}
    .meta-center {{ width: 1fr; text-align: center; color: {TEXT_MUTED}; }}
    .meta-right  {{ width: 1fr; text-align: right; }}

    #pb_vol_container {{
        width: 1fr;
        height: 1;
        layout: horizontal;
    }}

    Static.player-btn {{
        width: auto;
        padding: 0 2;
        background: transparent;
        color: {TEXT_PRIMARY};
        margin: 0;
        overflow: hidden;
    }}
    Static.player-btn:hover {{
        background: {BG_PANEL};
        color: {ACCENT_FIRE};
        text-style: bold;
    }}
    #pb_controls .main-btn {{
        height: 3;
        width: 15;
        content-align: center middle;
        background: transparent;
        border: round {ACCENT_FIRE};
        margin: 0 1;
        padding: 0;
        overflow: hidden;
    }}
    #pb_controls .main-btn:hover {{
        background: {ACCENT_FIRE};
        color: {BG_VOID};
        border: round {TEXT_PRIMARY};
    }}
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="pb_title_row"):
            self.info_line = Static("Ketuk Radio untuk mulai ▶", id="pb_info")
            self.seek_hint = Static("[dim] →[/dim]", id="pb_seek_hint")
            self.badge_mode = Static("[dim]\u2261 queue[/dim]", id="pb_badge_mode")
            yield self.info_line
            yield self.seek_hint
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
            self.badge_sb = Static("", id="pb_badge_sb", classes="meta-center")
            self.badge_cache = Static("", id="pb_badge_cache", classes="meta-center")
            self.btn_download = Static("⬇ unduh", id="btn_download", classes="meta-right player-btn")
            yield self.badge_sb
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
            self.badge_mode.update("[bold yellow]\U0001f4fb radio[/bold yellow]")
        else:
            self.badge_mode.update("[dim]\u2261 queue[/dim]")
            
        t = state.current_track
        if t:
            if t.local_path:
                self.badge_cache.update(r"[green]\[✓] tersimpan[/green]")
            else:
                self.badge_cache.update(r"[dim]\[☁] stream[/dim]")
        else:
            self.badge_cache.update("")

        if getattr(state, "sponsorblock_active", False):
            self.badge_sb.update("[bold yellow]SB: ON[/bold yellow]")
        else:
            self.badge_sb.update("")

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
            self.btn_play.update("[yellow] || [/yellow]")
        elif state.status == PlayerStatus.PLAYING:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/bold] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.update("[yellow] || [/yellow]")
        elif state.status == PlayerStatus.PAUSED:
            t = state.current_track
            if t:
                self.info_line.update(f"[bold]{escape(t.title)}[/bold] - {escape(t.artist)}")
                self.progress_bar.position = state.position
                self.progress_bar.duration = t.duration
            self.btn_play.update(" ▷ ")
        elif state.status == PlayerStatus.ERROR:
            msg = state.error_msg or "Terjadi kesalahan"
            self.info_line.update(f"[red]{escape(msg)}[/red]")
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
