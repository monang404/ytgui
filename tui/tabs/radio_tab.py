from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Vertical, Horizontal
from textual import on
from rich.markup import escape
from core.state import AppState, PlaybackMode
from core.event_bus import bus, CMD_SET_MODE, CMD_NEXT, CMD_RADIO_RANDOMIZE
from tui.theme import TEXT_DIM, STATUS_OK, TEXT_PRIMARY, ACCENT_FIRE, BG_ELEVATED, BG_VOID, BORDER
from tui.components.nav_bar import TabChanged

class RadioTab(Widget):
    """The Radio Tab for infinite playback."""
    DEFAULT_CSS = f"""
    RadioTab {{
        height: 1fr;
        padding: 2 4;
    }}
    #radio_container {{
        align: center middle;
        height: 1fr;
    }}
    #radio_btn {{
        width: 100%;
        height: 3;
        margin-bottom: 2;
        background: {BG_ELEVATED};
        color: {TEXT_PRIMARY};
        border: tall {BORDER};
    }}
    #radio_btn.-on {{
        background: {ACCENT_FIRE};
        color: {BG_VOID};
        border: tall {ACCENT_FIRE};
        text-style: bold;
    }}
    #radio_info {{
        text-align: center;
        margin-bottom: 2;
    }}
    #random_radio_btn {{
        width: 1fr;
        height: 3;
    }}
    #radio_skip_btn {{
        width: 1fr;
        height: 3;
        margin-left: 1;
    }}
    #radio_actions {{
        height: 3;
        layout: horizontal;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="radio_container"):
            self.radio_btn = Button("📻 radio: off", id="radio_btn")
            self.info = Static(f"[{TEXT_DIM}]radio memutar lagu otomatis tanpa henti.[/]", id="radio_info")
            yield self.radio_btn
            yield self.info
            
            with Horizontal(id="radio_actions"):
                yield Button("🎲 acak ulang radio", id="random_radio_btn")
                yield Button("⏭ skip lagu ini", id="radio_skip_btn")

    def update_state(self, state: AppState) -> None:
        is_radio = state.playback_mode == PlaybackMode.RADIO
        if is_radio:
            self.radio_btn.label = "📻 RADIO: ON"
            self.radio_btn.add_class("-on")
            
            if state.radio_queue:
                next_t = state.radio_queue[0]
                self.info.update(f"Radio aktif.\nSelanjutnya: [bold]{escape(next_t.title)}[/]")
            else:
                self.info.update("Radio aktif.\nSedang menyiapkan lagu berikutnya...")
        else:
            self.radio_btn.label = "📻 RADIO: OFF"
            self.radio_btn.remove_class("-on")
            self.info.update(f"[{TEXT_DIM}]Radio memutar lagu otomatis tanpa henti.\nKetuk untuk mengaktifkan.[/]")

    @on(Button.Pressed, "#radio_btn")
    async def toggle_radio(self, event: Button.Pressed) -> None:
        mode = PlaybackMode.QUEUE if self.app.state.playback_mode == PlaybackMode.RADIO else PlaybackMode.RADIO
        await bus.publish(CMD_SET_MODE, mode)

    @on(Button.Pressed, "#random_radio_btn")
    async def on_randomize_radio(self, event: Button.Pressed) -> None:
        await bus.publish(CMD_RADIO_RANDOMIZE)

    @on(Button.Pressed, "#radio_skip_btn")
    async def on_skip(self, event: Button.Pressed) -> None:
        await bus.publish(CMD_NEXT)
