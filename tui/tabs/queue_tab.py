from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Button, Label
from textual.containers import Vertical, Horizontal
from rich.markup import escape
from core.state import AppState, PlaybackMode
from core.event_bus import bus, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE
from tui.theme import TEXT_DIM, ACCENT_FIRE, STATUS_OK, BORDER, TEXT_PRIMARY
from textual.binding import Binding
from textual import work

class QueueItem(ListItem):
    def __init__(self, index: int, text: str, is_current: bool = False, removable: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_index = index
        self.text = text
        self.is_current = is_current
        self.removable = removable
        if is_current:
            self.add_class("-current")

    def compose(self) -> ComposeResult:
        yield Label(self.text, classes="queue-text")

class QueueTab(Widget):
    """The Queue Tab showing current track and upcoming queue."""
    BINDINGS = [
        Binding("l", "toggle_lyrics", "Toggle Lyrics")
    ]
    
    DEFAULT_CSS = f"""
    QueueTab {{
        height: 1fr;
        padding: 1;
    }}
    #queue_list {{
        height: 1fr;
    }}
    QueueItem {{
        border: round {BORDER};
        margin-bottom: 1;
        padding: 0 1;
        height: auto;
    }}
    QueueItem.-current {{
        border: round {ACCENT_FIRE};
    }}
    QueueItem:hover {{
        border: round {ACCENT_FIRE};
    }}
    .queue-text {{
        width: 1fr;
    }}
    #queue_footer {{
        height: 1;
        margin-top: 1;
        text-align: center;
    }}
    #lyrics_container {{
        height: 8;
        border-top: solid {ACCENT_FIRE};
        padding: 1;
        display: none;
    }}
    #lyrics_toggle_btn {{
        width: 100%;
        height: 1;
        min-height: 1;
        border: none;
        background: transparent;
        color: {ACCENT_FIRE};
        padding: 0;
        margin: 1 0;
    }}
    #lyrics_content {{
        height: 1fr;
        text-align: center;
        content-align: center middle;
    }}
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            self.list_view = ListView(id="queue_list")
            self.footer = Static(f"Mode: [{TEXT_DIM}]QUEUE[/]", id="queue_footer")
            yield self.list_view
            yield self.footer
            
            with Vertical(id="lyrics_container") as self.lyrics_container:
                self.lyrics_toggle_btn = Button("📝 Lirik ▾", id="lyrics_toggle_btn")
                self.lyrics_content = Static("Tidak ada lirik", id="lyrics_content")
                yield self.lyrics_toggle_btn
                yield self.lyrics_content

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_state_hash = None
        self._is_radio = False

    def update_state(self, state: AppState) -> None:
        self._is_radio = state.playback_mode == PlaybackMode.RADIO
        # Radio Mode dan Queue Mode masing-masing punya list lagunya sendiri.
        upcoming = state.radio_queue if self._is_radio else state.queue

        current_hash = hash((
            state.current_track.video_id if state.current_track else None,
            len(upcoming),
            upcoming[0].video_id if upcoming else None,
            state.playback_mode
        ))
        
        # Selalu update lirik jika container lirik tampil, terlepas dari hash list antrean
        if self.lyrics_container.display:
            if getattr(state, "lyrics_loading", False):
                self.lyrics_content.update("[bold yellow]⏳ Memuat lirik...[/bold yellow]")
            elif not state.lyrics_lines:
                self.lyrics_content.update("[dim]Tidak ada lirik tersedia[/dim]")
            else:
                idx = state.lyrics_index
                lines = state.lyrics_lines
                start = max(0, idx - 5)
                end = min(len(lines), idx + 6)
                
                content = ""
                for i in range(start, end):
                    text = lines[i]
                    if i == idx:
                        content += f"[{ACCENT_FIRE}][b]▶ {escape(text)} ◀[/b][/]\n"
                    elif i < idx:
                        content += f"[{TEXT_DIM}][dim]{escape(text)}[/dim][/]\n"
                    else:
                        content += f"[{TEXT_PRIMARY}]{escape(text)}[/]\n"
                self.lyrics_content.update(content.strip())

        # Update List View hanya jika ada perubahan lagu atau mode
        if self._last_state_hash == current_hash:
            return
            
        self._last_state_hash = current_hash
        self._rebuild_list(state, upcoming)

    @work(exclusive=True)
    async def _rebuild_list(self, state: AppState, upcoming: list) -> None:
        await self.list_view.clear()
        
        terminal_width = self.app.size.width if self.app.size.width > 0 else 80
        inner_width = terminal_width - 6
        max_title = max(10, inner_width - 15)
        
        if not upcoming and not state.current_track:
            placeholder = "Radio sedang menyiapkan lagu..." if self._is_radio else "Cari lagu atau aktifkan Radio"
            await self.list_view.append(ListItem(Label(f"[dim]{placeholder}[/dim]")))
        else:
            if state.current_track:
                title = state.current_track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                await self.list_view.append(QueueItem(-1, f"[bold]> {escape(title)}[/bold]", is_current=True))
                
            for i, track in enumerate(upcoming):
                dur = f"{track.duration // 60}:{track.duration % 60:02d}"
                title = track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                await self.list_view.append(QueueItem(i, f"  {i+1}. {escape(title)} [dim]{dur}[/dim]", removable=not self._is_radio))

        mode_str = "[green]RADIO[/green]" if state.playback_mode == PlaybackMode.RADIO else "[dim]QUEUE[/dim]"
        self.footer.update(f"Mode: {mode_str} | 📝 Lirik: Tekan L")
        
        # Update lyrics if visible
        if self.lyrics_container.display:
            if getattr(state, "lyrics_loading", False):
                self.lyrics_content.update("[bold yellow]⏳ Memuat lirik...[/bold yellow]")
            elif not state.lyrics_lines:
                self.lyrics_content.update("[dim]Tidak ada lirik tersedia[/dim]")
            else:
                idx = state.lyrics_index
                lines = state.lyrics_lines
                start = max(0, idx - 5)
                end = min(len(lines), idx + 6)
                
                content = ""
                for i in range(start, end):
                    text = lines[i]
                    if i == idx:
                        content += f"[{ACCENT_FIRE}][b]▶ {escape(text)} ◀[/b][/]\n"
                    elif i < idx:
                        content += f"[{TEXT_DIM}][dim]{escape(text)}[/dim][/]\n"
                    else:
                        content += f"[{TEXT_PRIMARY}]{escape(text)}[/]\n"
                self.lyrics_content.update(content.strip())

    async def action_toggle_lyrics(self) -> None:
        self.lyrics_container.display = not self.lyrics_container.display
        if self.lyrics_container.display:
            self.list_view.display = False
            self.lyrics_container.styles.height = "1fr"
        else:
            self.list_view.display = True
            self.list_view.styles.height = "1fr"
        # Trigger update explicitly
        self._last_state_hash = None

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if self._is_radio:
            return
        if isinstance(event.item, QueueItem) and not event.item.is_current:
            await command_bus.execute(CMD_QUEUE_SELECT, event.item.queue_index)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("rm_"):
            if self._is_radio:
                return
            idx = int(event.button.id.split("_")[1])
            await command_bus.execute(CMD_QUEUE_REMOVE, idx)
            # Prevent list view selection when clicking the remove button
            event.stop()
        elif event.button.id == "lyrics_toggle_btn":
            await self.action_toggle_lyrics()
