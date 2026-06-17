from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Button, Label
from textual.containers import Vertical, Horizontal
from rich.markup import escape
from core.state import AppState, PlaybackMode
from core.event_bus import bus, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE
from tui.theme import TEXT_DIM, ACCENT_FIRE, STATUS_OK
from textual.binding import Binding

class QueueItem(ListItem):
    def __init__(self, index: int, text: str, is_current: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_index = index
        self.text = text
        self.is_current = is_current
        if is_current:
            self.add_class("-current")

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(self.text, classes="queue-text")
            if not self.is_current:
                yield Button("✕", id=f"rm_{self.queue_index}", classes="queue-rm-btn")

class QueueTab(Widget):
    """The Queue Tab showing current track and upcoming queue."""
    BINDINGS = [
        Binding("l", "toggle_lyrics", "Toggle Lyrics")
    ]
    
    DEFAULT_CSS = """
    QueueTab {
        height: 1fr;
        padding: 1;
    }
    #queue_list {
        height: 1fr;
    }
    QueueItem {
        height: 3;
        border: round $border;
        margin-bottom: 1;
    }
    QueueItem.-current {
        border: round $accent;
    }
    QueueItem Horizontal {
        align: left middle;
    }
    .queue-text {
        width: 1fr;
    }
    .queue-rm-btn {
        width: 5;
        height: 1;
        border: none;
        color: $error;
        background: transparent;
        margin-left: 1;
    }
    .queue-rm-btn:hover {
        background: $error-muted;
    }
    #queue_footer {
        height: 1;
        margin-top: 1;
        text-align: center;
    }
    #lyrics_container {
        height: 8;
        border-top: solid $primary;
        padding: 0 1;
        display: none;
    }
    #lyrics_toggle_btn {
        width: 100%;
        height: 3;
        border: none;
        background: transparent;
        color: $accent;
    }
    #lyrics_content {
        height: 1fr;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            self.list_view = ListView(id="queue_list")
            self.footer = Static(f"Mode: [{TEXT_DIM}]QUEUE[/]", id="queue_footer")
            yield self.list_view
            yield self.footer
            
            self.lyrics_container = Vertical(id="lyrics_container")
            with self.lyrics_container:
                self.lyrics_toggle_btn = Button("📝 Lirik ▾", id="lyrics_toggle_btn")
                self.lyrics_content = Static("Tidak ada lirik", id="lyrics_content")
                yield self.lyrics_toggle_btn
                yield self.lyrics_content

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_state_hash = None

    def update_state(self, state: AppState) -> None:
        current_hash = hash((
            state.current_track.video_id if state.current_track else None,
            len(state.queue),
            state.queue[0].video_id if state.queue else None,
            self.size.width,
            state.playback_mode
        ))
        
        if self._last_state_hash == current_hash:
            return
            
        self._last_state_hash = current_hash
        self.list_view.clear()
        
        terminal_width = self.size.width if self.size.width > 0 else 80
        inner_width = terminal_width - 6
        max_title = max(10, inner_width - 15)
        
        if not state.queue and not state.current_track:
            self.list_view.append(ListItem(Label(f"[{TEXT_DIM}]Cari lagu atau aktifkan Radio[/]")))
        else:
            if state.current_track:
                title = state.current_track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                self.list_view.append(QueueItem(-1, f"[{ACCENT_FIRE}]> {escape(title)}[/]", is_current=True))
                
            for i, track in enumerate(state.queue):
                dur = f"{track.duration // 60}:{track.duration % 60:02d}"
                title = track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                self.list_view.append(QueueItem(i, f"  {i+1}. {escape(title)} [{TEXT_DIM}]{dur}[/]"))

        mode_str = f"[{STATUS_OK}]RADIO[/]" if state.playback_mode == PlaybackMode.RADIO else f"[{TEXT_DIM}]QUEUE[/]"
        self.footer.update(f"Mode: {mode_str} | 📝 Lirik: Tekan L")
        
        # Update lyrics if visible
        if self.lyrics_container.display:
            if not state.lyrics_lines:
                self.lyrics_content.update(f"[{TEXT_DIM}]Tidak ada lirik tersedia[/]")
            else:
                idx = state.lyrics_index
                lines = state.lyrics_lines
                start = max(0, idx - 2)
                end = min(len(lines), idx + 3)
                
                content = ""
                for i in range(start, end):
                    text = lines[i][1]
                    if i == idx:
                        content += f"[{ACCENT_FIRE}][b]{escape(text)}[/b][/]\n"
                    else:
                        content += f"[{TEXT_DIM}]{escape(text)}[/]\n"
                self.lyrics_content.update(content.strip())

    async def action_toggle_lyrics(self) -> None:
        self.lyrics_container.display = not self.lyrics_container.display
        if self.lyrics_container.display:
            self.list_view.styles.height = "1fr"
        else:
            self.list_view.styles.height = "1fr"
        # Trigger update explicitly
        self._last_state_hash = None

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, QueueItem) and not event.item.is_current:
            await bus.publish(CMD_QUEUE_SELECT, event.item.queue_index)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("rm_"):
            idx = int(event.button.id.split("_")[1])
            await bus.publish(CMD_QUEUE_REMOVE, idx)
            # Prevent list view selection when clicking the remove button
            event.stop()
        elif event.button.id == "lyrics_toggle_btn":
            await self.action_toggle_lyrics()
