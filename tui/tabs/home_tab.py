import asyncio
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Label, Button
from textual.containers import Vertical, Horizontal
from textual import work, on
from rich.markup import escape
from core.state import TrackInfo, PlaybackMode
from core.event_bus import bus, CMD_PLAY_TRACK, CMD_SET_MODE
from tui.theme import TEXT_DIM, ACCENT_GOLD, TEXT_PRIMARY
from services.discover_service import DiscoverService

def make_track_card(track: TrackInfo, icon: str) -> Button:
    dur = f"{track.duration // 60}:{track.duration % 60:02d}"
    label = f"{icon} {escape(track.title)}\n[dim]{escape(track.artist)} · {dur}[/]"
    btn = Button(label, id=f"track_{track.video_id}", classes="track-card")
    btn.track = track
    return btn

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
    .empty-msg {
        color: $text-muted;
        text-align: center;
        margin: 2;
    }
    Button.radio-cta {
        width: 100%;
        height: 3;
        background: $accent;
        color: $background;
        border: round $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }
    .card-row {
        height: auto;
        overflow-x: auto;
    }
    .track-card {
        width: 18;
        height: 3;
        border: round $border;
        background: $panel;
        text-align: left;
        padding: 0 1;
        margin-right: 1;
    }
    .track-card:hover {
        border: round $accent;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discover_service = None

    def compose(self) -> ComposeResult:
        with Vertical(id="home_container"):
            yield Static("🌟 Welcome to YTGUI V2", classes="section-title")
            
            self.radio_cta = Button("▶ Mulai Radio", id="home_radio_cta", classes="radio-cta")
            yield self.radio_cta
            
            yield Static("Continue Listening", classes="section-title")
            self.recent_row = Horizontal(id="recent_row", classes="card-row")
            yield self.recent_row
            self.recent_empty = Static("Belum ada riwayat pemutaran.", classes="empty-msg")
            yield self.recent_empty

            yield Static("Favorites", classes="section-title")
            self.fav_row = Horizontal(id="fav_row", classes="card-row")
            yield self.fav_row
            self.fav_empty = Static("Belum ada lagu favorit.", classes="empty-msg")
            yield self.fav_empty

    def on_mount(self) -> None:
        if hasattr(self.app, 'db') and self.app.db:
            self.discover_service = DiscoverService(self.app.db)
            self.load_data()

    def on_show(self) -> None:
        self.load_data()

    @work(exclusive=True)
    async def load_data(self) -> None:
        if not self.discover_service:
            return
            
        recent = await self.discover_service.get_recent(5)
        favs = await self.discover_service.get_favorites(5)
        
        await self._update_ui(recent, favs)

    async def _update_ui(self, recent: list[TrackInfo], favs: list[TrackInfo]) -> None:
        await self.recent_row.remove_children()
        await self.fav_row.remove_children()

        if not recent:
            self.recent_row.display = False
            self.recent_empty.display = True
            self.recent_empty.update("Cari lagu di tab Search untuk mulai mendengarkan!")
        else:
            self.recent_row.display = True
            self.recent_empty.display = False
            for track in recent:
                await self.recent_row.mount(make_track_card(track, "🕒"))

        if not favs:
            self.fav_row.display = False
            self.fav_empty.display = True
            self.fav_empty.update("Lagu yang sering diputar akan muncul di sini.")
        else:
            self.fav_row.display = True
            self.fav_empty.display = False
            for track in favs:
                await self.fav_row.mount(make_track_card(track, "⭐"))

    @on(Button.Pressed)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("track-card"):
            await bus.publish(CMD_PLAY_TRACK, getattr(event.button, "track"))
        elif event.button.id == "home_radio_cta":
            await bus.publish(CMD_SET_MODE, PlaybackMode.RADIO)
