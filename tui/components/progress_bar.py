from textual.widgets import Static
from textual.reactive import reactive
from textual import events

from core.event_bus import bus, CMD_SEEK
from tui.theme import TEXT_DIM

class ClickableProgressBar(Static):
    DEFAULT_CSS = """
    ClickableProgressBar {
        height: 2;
        padding-top: 1;
    }
    """
    
    position = reactive(0.0)
    duration = reactive(0.0)

    def render(self) -> str:
        if self.duration <= 0:
            return ""
        
        bar_width = max(10, self.size.width - 16)
        pct = min(1.0, self.position / self.duration)
        filled = int(pct * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        pos_str = f"{int(self.position//60):02d}:{int(self.position%60):02d}"
        dur_str = f"{int(self.duration//60):02d}:{int(self.duration%60):02d}"
        
        return f"[{TEXT_DIM}]{pos_str}[/] {bar} [{TEXT_DIM}]{dur_str}[/]"

    async def on_click(self, event: events.Click) -> None:
        if self.duration <= 0:
            return
        
        bar_start_x = 6
        bar_width = max(10, self.size.width - 16)
        
        click_x = event.x - bar_start_x
        if click_x < 0:
            click_x = 0
        elif click_x > bar_width:
            click_x = bar_width
            
        pct = click_x / bar_width
        seek_to = pct * self.duration
        await bus.publish(CMD_SEEK, seek_to)
