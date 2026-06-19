from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Center
from tui.theme import TEXT_DIM, BG_VOID, BG_PANEL, ACCENT_FIRE

class HelpScreen(ModalScreen):
    """Screen for displaying a shortcut cheatsheet."""
    DEFAULT_CSS = f"""
    HelpScreen {{
        align: center middle;
        background: {BG_VOID} 80%;
    }}
    #help_container {{
        width: 60;
        height: auto;
        padding: 2;
        background: {BG_PANEL};
        border: thick {ACCENT_FIRE};
    }}
    .help_title {{
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: {ACCENT_FIRE};
    }}
    .help_text {{
        margin-bottom: 1;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help_container"):
            yield Label("PANDUAN SHORTCUT", classes="help_title")
            shortcuts = [
                "/   : Cari lagu",
                "p   : Pause/Resume",
                "n   : Lagu selanjutnya",
                "b   : Lagu sebelumnya",
                "s   : Stop",
                "u   : Volume naik",
                "d   : Volume turun",
                "m   : Unduh lagu ini",
                "r   : Toggle mode Radio",
                "l   : Buka lirik lagu",
                "q   : Keluar aplikasi",
                "Esc : Tutup pencarian/fokus",
                "?   : Tampilkan panduan ini"
            ]
            for s in shortcuts:
                yield Label(f"[{TEXT_DIM}]{s}[/]", classes="help_text")
            
            with Center():
                yield Button("Tutup", variant="primary", id="close_help_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_help_btn":
            self.app.pop_screen()
