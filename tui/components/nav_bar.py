from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button
from textual.containers import Horizontal
from textual.message import Message
from tui.theme import HEIGHT_NAV_BAR, NAV_ACTIVE_COLOR, NAV_INACTIVE_COLOR, TAB_HOME, TAB_SEARCH, TAB_RADIO, TAB_QUEUE, BG_ELEVATED, BG_PANEL, BORDER, TEXT_PRIMARY

class TabChanged(Message):
    """Event sent when a nav bar tab is clicked."""
    def __init__(self, tab_id: str):
        self.tab_id = tab_id
        super().__init__()

class NavBar(Widget):
    DEFAULT_CSS = f"""
    NavBar {{
        height: {HEIGHT_NAV_BAR};
        dock: bottom;
        background: {BG_ELEVATED};
        border-top: solid {BORDER};
    }}
    #nav_container {{
        width: 100%;
        height: 100%;
    }}
    Button.nav-btn {{
        width: 1fr;
        min-width: 1;
        padding: 0;
        height: 100%;
        border: none;
        color: {NAV_INACTIVE_COLOR};
        background: transparent;
        text-align: center;
        content-align: center middle;
        text-style: none;
    }}
    Button.nav-btn:hover {{
        background: {BG_PANEL};
        color: {TEXT_PRIMARY};
        border: none;
    }}
    Button.nav-btn.-active {{
        color: {NAV_ACTIVE_COLOR};
        background: transparent;
        border: none;
        border-bottom: solid {NAV_ACTIVE_COLOR};
        text-style: bold;
    }}
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="nav_container"):
            yield Button("💿\nplayer", id=TAB_HOME, classes="nav-btn")
            yield Button("🔍\nsearch", id=TAB_SEARCH, classes="nav-btn")
            yield Button("📻\nradio", id=TAB_RADIO, classes="nav-btn")
            yield Button("☰\nqueue", id=TAB_QUEUE, classes="nav-btn")

    def on_mount(self) -> None:
        self.set_active_tab(TAB_HOME)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        tab_id = event.button.id
        if tab_id:
            self.set_active_tab(tab_id)
            self.post_message(TabChanged(tab_id))

    def set_active_tab(self, tab_id: str) -> None:
        for btn in self.query("Button.nav-btn"):
            if btn.id == tab_id:
                btn.add_class("-active")
            else:
                btn.remove_class("-active")
