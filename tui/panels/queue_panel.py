from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import OptionList, Static
from textual.containers import Vertical
from rich.markup import escape
from core.state import AppState
from core.event_bus import bus, CMD_QUEUE_SELECT
from tui.theme import TEXT_DIM, ACCENT_FIRE, STATUS_OK

class QueuePanel(Widget):
    """The Queue & Autoplay panel using OptionList for selection."""

    def compose(self) -> ComposeResult:
        with Vertical():
            self.option_list = OptionList(id="queue_list")
            self.footer = Static(f"Radio: [{TEXT_DIM}]OFF[/]", id="queue_footer")
            yield self.option_list
            yield self.footer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_state_hash = None

    def update_state(self, state: AppState) -> None:
        current_hash = hash((
            state.current_track.video_id if state.current_track else None,
            len(state.queue),
            state.queue[0].video_id if state.queue else None,
            self.size.width,
            state.is_radio_mode
        ))
        
        if self._last_state_hash == current_hash:
            return
            
        self._last_state_hash = current_hash
        self.option_list.clear_options()
        
        terminal_width = self.size.width if self.size.width > 0 else 80
        inner_width = terminal_width - 6
        max_title = max(10, inner_width - 12)
        
        if not state.queue and not state.current_track:
            self.option_list.add_option(f"[{TEXT_DIM}]Queue is empty.[/]")
            self.option_list.disabled = True
        else:
            self.option_list.disabled = False
            if state.current_track:
                title = state.current_track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                self.option_list.add_option(f"[{ACCENT_FIRE}]> {escape(title)}[/]")
                
            for i, track in enumerate(state.queue, 1):
                dur = f"{track.duration // 60}:{track.duration % 60:02d}"
                title = track.title
                if len(title) > max_title:
                    title = title[:max_title - 1] + "…"
                self.option_list.add_option(f"  {i}. {escape(title)} [{TEXT_DIM}]{dur}[/]")

        radio = f"[{STATUS_OK}]ON[/]" if state.is_radio_mode else f"[{TEXT_DIM}]OFF[/]"
        self.footer.update(f"Radio: {radio}")

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_index == 0:
            return # Current track or empty queue clicked
        
        queue_index = event.option_index - 1
        if queue_index >= 0:
            await bus.publish(CMD_QUEUE_SELECT, queue_index)
