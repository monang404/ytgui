import asyncio
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal
from textual import work, on
from rich.markup import escape
from core.state import TrackInfo
from core.event_bus import bus, CMD_PLAY_TRACK
from tui.theme import TEXT_DIM, ACCENT_GOLD, TEXT_PRIMARY
from services.discover_service import DiscoverService

class TrackCard(ListItem):
    def __init__(self, track: TrackInfo, is_recent: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track
        self.is_recent = is_recent

    def compose(self) -> ComposeResult:
        with Horizontal():
            icon = "🕒" if self.is_recent else "⭐"
            dur = f"{self.track.duration // 60}:{self.track.duration % 60:02d}"
            views = f"{self.track.view_count or 0}x diputar" if not self.is_recent else ""
            info = f"[{TEXT_DIM}]{dur} {views}[/]"
            yield Label(f"{icon} [bold {TEXT_PRIMARY}]{escape(self.track.title)}[/] - {escape(self.track.artist)} {info}")

class HomeTab(Widget):
    """The Home Tab showing recent tracks and favorites."""
    DEFAULT_CSS = """
    HomeTab {
        height: 1fr;
        padding: 1;
    }
    #home_container {
        height: 1fr;
        overflow-y: auto;
    }
    .section-title {
        text-style: bold;
        color: $accent;
        margin-top: 1;
        margin-bottom: 1;
    }
    .empty-msg {
        color: $text-muted;
        text-align: center;
        margin: 2;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discover_service = None

    def compose(self) -> ComposeResult:
        with Vertical(id="home_container"):
            yield Static("🌟 Welcome to YTGUI V2", classes="section-title")
            
            yield Static("Continue Listening", classes="section-title")
            self.recent_list = ListView(id="recent_list")
            yield self.recent_list
            self.recent_empty = Static("Belum ada riwayat pemutaran.", classes="empty-msg")
            yield self.recent_empty

            yield Static("Favorites", classes="section-title")
            self.fav_list = ListView(id="fav_list")
            yield self.fav_list
            self.fav_empty = Static("Belum ada lagu favorit.", classes="empty-msg")
            yield self.fav_empty

    def on_mount(self) -> None:
        if hasattr(self.app, 'db') and self.app.db:
            self.discover_service = DiscoverService(self.app.db)
            self.load_data()

    def on_show(self) -> None:
        self.load_data()

    @work(exclusive=True, thread=True)
    def load_data(self) -> None:
        if not self.discover_service:
            return
            
        recent = asyncio.run_coroutine_threadsafe(self.discover_service.get_recent(5), self.app.loop).result()
        favs = asyncio.run_coroutine_threadsafe(self.discover_service.get_favorites(5), self.app.loop).result()
        
        self.app.call_from_thread(self._update_ui, recent, favs)

    def _update_ui(self, recent: list[TrackInfo], favs: list[TrackInfo]) -> None:
        self.recent_list.clear()
        self.fav_list.clear()

        if not recent:
            self.recent_list.display = False
            self.recent_empty.display = True
            self.recent_empty.update("Cari lagu di tab Search untuk mulai mendengarkan!")
        else:
            self.recent_list.display = True
            self.recent_empty.display = False
            for track in recent:
                self.recent_list.append(TrackCard(track, is_recent=True))

        if not favs:
            self.fav_list.display = False
            self.fav_empty.display = True
            self.fav_empty.update("Lagu yang sering diputar akan muncul di sini.")
        else:
            self.fav_list.display = True
            self.fav_empty.display = False
            for track in favs:
                self.fav_list.append(TrackCard(track, is_recent=False))

    @on(ListView.Selected)
    async def on_list_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, TrackCard):
            await bus.publish(CMD_PLAY_TRACK, event.item.track)
