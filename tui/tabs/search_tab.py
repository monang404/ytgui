import time
import asyncio
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, ListView, ListItem, Label, Static
from textual.containers import Vertical
from textual import work, on
from rich.markup import escape
from core.state import TrackInfo
from core.event_bus import bus, CMD_PLAY_TRACK, CMD_SEARCH, LOG_MESSAGE
from tui.theme import TEXT_DIM, ACCENT_GOLD, STATUS_OK, STATUS_ERR

class SearchResultItem(ListItem):
    def __init__(self, track: TrackInfo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track

    def compose(self) -> ComposeResult:
        via = "[✓] Cache" if self.track.local_path else "[☁] Stream"
        dur = f"{self.track.duration // 60}:{self.track.duration % 60:02d}"
        yield Label(f"[bold]{escape(self.track.title)}[/] - {escape(self.track.artist)} [{TEXT_DIM}]{dur} | {via}[/]")

class SearchTab(Widget):
    """The Search Tab for finding tracks."""
    DEFAULT_CSS = """
    SearchTab {
        height: 1fr;
        padding: 1;
    }
    #search_input {
        width: 1fr;
        margin-bottom: 1;
    }
    #search_results {
        height: 1fr;
    }
    #search_msg {
        text-align: center;
        margin-top: 1;
    }
    SearchResultItem {
        border: round $border;
        margin-bottom: 1;
        padding: 0 1;
        height: auto;
    }
    SearchResultItem:hover {
        border: round $accent;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._search_timer = None
        self._last_query = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="search_container"):
            yield Input(placeholder="ketik pencarian... (tekan enter)", id="search_input")
            self.msg_label = Static(f"[{TEXT_DIM}]ketik nama lagu atau artis[/]", id="search_msg")
            yield self.msg_label
            self.list_view = ListView(id="search_results")
            self.list_view.display = False
            yield self.list_view

    def on_show(self) -> None:
        self.query_one("#search_input").focus()

    @on(Input.Changed, "#search_input")
    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()

        if not query:
            self.msg_label.update(f"[{TEXT_DIM}]Ketik nama lagu atau artis[/]")
            self.msg_label.display = True
            self.list_view.display = False
            self.list_view.clear()

    @work(exclusive=True)
    async def perform_live_search(self, query: str) -> None:
        self._show_loading()
        try:
            # We assume app.ytdlp is available (passed from main.py)
            if hasattr(self.app, 'ytdlp') and self.app.ytdlp:
                results = await self.app.ytdlp.search(query, max_results=10)
                self._show_results(results)
        except Exception as e:
            self._show_error(str(e))

    def _show_loading(self) -> None:
        self.msg_label.update(f"[{ACCENT_GOLD}]⏳ Mencari...[/]")
        self.msg_label.display = True
        self.list_view.display = False

    def _show_results(self, results: list[TrackInfo]) -> None:
        self.list_view.clear()
        if not results:
            self.msg_label.update(f"[{TEXT_DIM}]Tidak ditemukan hasil.[/]")
            self.msg_label.display = True
            self.list_view.display = False
            return

        for track in results:
            self.list_view.append(SearchResultItem(track))
            
        self.msg_label.display = False
        self.list_view.display = True

    def _show_error(self, msg: str) -> None:
        self.msg_label.update(f"[{STATUS_ERR}]Gagal mencari: {escape(msg)}[/]")
        self.msg_label.display = True
        self.list_view.display = False

    @on(Input.Submitted, "#search_input")
    async def on_submit(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self._show_loading()
            # C-01: Call perform_live_search instead of publishing CMD_SEARCH
            self.perform_live_search(query)

    @on(ListView.Selected, "#search_results")
    async def on_list_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, SearchResultItem):
            # Klik hasil -> publish CMD_PLAY_TRACK dengan TrackInfo tunggal
            await bus.publish(CMD_PLAY_TRACK, event.item.track)
