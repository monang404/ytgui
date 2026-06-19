import time
import asyncio
from textual.app import ComposeResult
from textual.widget import Widget
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label, Static, Button
from textual.containers import Vertical, Center
from textual import work, on
from rich.markup import escape
from core.state import TrackInfo
from core.event_bus import bus, CMD_PLAY_TRACK, CMD_QUEUE_ADD, LOG_MESSAGE
from tui.theme import TEXT_DIM, ACCENT_GOLD, STATUS_OK, STATUS_ERR

class SearchActionModal(ModalScreen[str]):
    DEFAULT_CSS = """
    SearchActionModal {
        align: center middle;
        background: $background 80%;
    }
    #action_modal {
        width: 60;
        height: auto;
        padding: 2;
        background: $surface;
        border: thick $primary;
    }
    #action_title {
        text-align: center;
        margin-bottom: 2;
        text-style: bold;
    }
    #action_buttons {
        layout: horizontal;
        align: center middle;
        height: 3;
    }
    """
    def __init__(self, track_title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track_title = track_title

    def compose(self) -> ComposeResult:
        with Vertical(id="action_modal"):
            yield Label(f"Apa yang ingin dilakukan dengan '{escape(self.track_title)}'?", id="action_title")
            with Center(id="action_buttons"):
                yield Button("▷ Putar", id="play_now", variant="primary")
                yield Button("+ Antrean", id="enqueue")
                yield Button("Batal", id="cancel", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)


class SearchResultItem(ListItem):
    def __init__(self, track: TrackInfo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.track = track

    def compose(self) -> ComposeResult:
        dur = f"{self.track.duration // 60}:{self.track.duration % 60:02d}"
        if self.track.local_path:
            via = r"\[✓] Cache"
            yield Label(f"[bold]{escape(self.track.title)}[/bold] - {escape(self.track.artist)} [dim]{dur}[/dim] | [green]{via}[/green]")
        else:
            via = r"\[☁] Stream"
            yield Label(f"[bold]{escape(self.track.title)}[/bold] - {escape(self.track.artist)} [dim]{dur}[/dim] | [dim]{via}[/dim]")

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
            yield Input(placeholder="ketik pencarian...", id="search_input")
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
        
        if self._search_timer:
            self._search_timer.stop()

        if not query:
            self.msg_label.update(f"[{TEXT_DIM}]Ketik nama lagu atau artis[/]")
            self.msg_label.display = True
            self.list_view.display = False
            self.list_view.clear()
            self._last_query = ""
            return

        if query != self._last_query:
            self._last_query = query
            self._search_timer = self.set_timer(0.5, lambda: self.perform_live_search(query))

    @work(exclusive=True)
    async def perform_live_search(self, query: str) -> None:
        self._show_loading()
        try:
            if hasattr(self.app, 'ytdlp') and self.app.ytdlp:
                results = await self.app.ytdlp.search(query, max_results=10)
                self._show_results(results)
        except Exception as e:
            self._show_error(str(e))

    def _show_loading(self) -> None:
        self.msg_label.update("[bold yellow]⏳ Mencari...[/bold yellow]")
        self.msg_label.display = True
        self.list_view.display = False

    def _show_results(self, results: list[TrackInfo]) -> None:
        self.list_view.clear()
        if not results:
            self.msg_label.update("[dim]Tidak ditemukan hasil.[/dim]")
            self.msg_label.display = True
            self.list_view.display = False
            return

        for track in results:
            self.list_view.append(SearchResultItem(track))
            
        self.msg_label.display = False
        self.list_view.display = True

    def _show_error(self, msg: str) -> None:
        self.msg_label.update(f"[red]Gagal mencari: {escape(msg)}[/red]")
        self.msg_label.display = True
        self.list_view.display = False

    @on(Input.Submitted, "#search_input")
    async def on_submit(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            if self._search_timer:
                self._search_timer.stop()
            self.perform_live_search(query)

    @on(ListView.Selected, "#search_results")
    async def on_list_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, SearchResultItem):
            track = event.item.track
            
            def handle_action(action_id: str | None):
                if action_id == "play_now":
                    asyncio.create_task(bus.publish(CMD_PLAY_TRACK, track))
                elif action_id == "enqueue":
                    asyncio.create_task(bus.publish(CMD_QUEUE_ADD, track))

            self.app.push_screen(SearchActionModal(track.title), handle_action)

