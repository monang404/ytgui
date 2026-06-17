from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Horizontal
from core.state import AppState, PlayerStatus
from tui.theme import HEIGHT_PLAYER_BAR, STATUS_ERR
from core.event_bus import bus, CMD_PREV, CMD_TOGGLE_PAUSE, CMD_NEXT
from tui.components.progress_bar import ClickableProgressBar
from rich.markup import escape

class PlayerBar(Widget):
    DEFAULT_CSS = f"""
    PlayerBar {{
        height: auto;
        dock: bottom;
        background: $boost;
        padding: 1 1;
    }}
    #pb_controls {{
        height: auto;
        align: center middle;
        margin-top: 1;
    }}
    Button.player-btn {{
        min-width: 5;
        min-height: 1;
        height: 1;
        border: none;
        padding: 0 1;
        background: transparent;
    }}
    Button.player-btn:hover {{
        background: $accent;
    }}
    """

    def compose(self) -> ComposeResult:
        self.info_line = Static("Ketuk Radio untuk mulai ▶", id="pb_info")
        self.progress_bar = ClickableProgressBar(id="pb_progress")
        self.btn_prev = Button("⏮", id="btn_prev", classes="player-btn")
        self.btn_play = Button("⏯", id="btn_play", classes="player-btn")
        self.btn_next = Button("⏭", id="btn_next", classes="player-btn")

        yield self.info_line
        yield self.progress_bar
        with Horizontal(id="pb_controls"):
            yield self.btn_prev
            yield self.btn_play
            yield self.btn_next

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_prev":
            await bus.publish(CMD_PREV)
        elif event.button.id == "btn_play":
            await bus.publish(CMD_TOGGLE_PAUSE)
        elif event.button.id == "btn_next":
            await bus.publish(CMD_NEXT)

    def update_state(self, state: AppState) -> None:
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
