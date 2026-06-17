from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Button
from textual.containers import Vertical
from textual import on
from rich.markup import escape
from core.state import AppState, PlaybackMode
from core.event_bus import bus, CMD_SET_MODE
from tui.theme import TEXT_DIM
from tui.components.nav_bar import TabChanged

class RadioTab(Widget):
    """The Radio Tab for infinite playback."""
    DEFAULT_CSS = """
    RadioTab {
        height: 1fr;
        padding: 2 4;
    }
    #radio_container {
        align: center middle;
        height: 1fr;
    }
    #radio_btn {
        width: 100%;
        height: 3;
        margin-bottom: 2;
    }
    #radio_btn.-on {
        background: $success;
        color: white;
    }
    #radio_info {
        text-align: center;
        margin-bottom: 2;
    }
    #change_seed_btn {
        width: 100%;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="radio_container"):
            self.radio_btn = Button("📻 RADIO: OFF", id="radio_btn")
            self.info = Static(f"[{TEXT_DIM}]Radio memutar lagu otomatis tanpa henti.[/]", id="radio_info")
            yield self.radio_btn
            yield self.info
            yield Button("🔍 Ganti Seed Lagu", id="change_seed_btn")

    def update_state(self, state: AppState) -> None:
        is_radio = state.playback_mode == PlaybackMode.RADIO
        if is_radio:
            self.radio_btn.label = "📻 RADIO: ON"
            self.radio_btn.add_class("-on")
            
            if state.queue:
                next_t = state.queue[0]
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

    @on(Button.Pressed, "#change_seed_btn")
    def on_change_seed(self, event: Button.Pressed) -> None:
        # Pindah ke tab pencarian (SearchTab) menggunakan TabChanged
        self.app.post_message(TabChanged("search"))
