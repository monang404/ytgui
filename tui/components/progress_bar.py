from textual.widgets import Static
from textual.reactive import reactive
from textual import events

from core.event_bus import bus, CMD_SEEK
from tui.theme import TEXT_DIM

class ClickableProgressBar(Static):
    DEFAULT_CSS = """
    ClickableProgressBar {
        height: 1;
        margin-top: 0;
        margin-bottom: 1;
    }
    """
    
    position = reactive(0.0)
    duration = reactive(0.0)

    def render(self) -> str:
        bar_width = max(10, self.size.width - 12)
        
        if self.duration <= 0:
            bar = "[dim]" + "━" * bar_width + "[/dim]"
            return f"[dim]00:00[/dim] {bar} [dim]00:00[/dim]"
            
        pct = min(1.0, max(0.0, self.position / self.duration))
        filled = int(pct * bar_width)
        
        if bar_width > 0:
            if filled <= 0:
                bar = "[yellow]●[/yellow][dim]" + "━" * (bar_width - 1) + "[/dim]"
            elif filled >= bar_width:
                bar = "[yellow]" + "━" * (bar_width - 1) + "●[/yellow]"
            else:
                bar = "[yellow]" + "━" * filled + "●[/yellow][dim]" + "━" * (bar_width - filled - 1) + "[/dim]"
        else:
            bar = ""

        pos_str = f"{int(self.position//60):02d}:{int(self.position%60):02d}"
        dur_str = f"{int(self.duration//60):02d}:{int(self.duration%60):02d}"
        
        return f"[dim]{pos_str}[/dim] {bar} [dim]{dur_str}[/dim]"

    async def on_click(self, event: events.Click) -> None:
        if self.duration <= 0:
            return
        
        bar_start_x = 6
        bar_width = max(10, self.size.width - 12)
        
        click_x = event.x - bar_start_x
        if click_x < 0:
            click_x = 0
        elif click_x > bar_width:
            click_x = bar_width
            
        pct = click_x / bar_width
        seek_to = pct * self.duration
        await bus.publish(CMD_SEEK, seek_to)
