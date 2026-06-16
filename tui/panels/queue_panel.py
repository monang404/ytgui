from rich.panel import Panel
from rich.text import Text
from core.state import AppState

def render_queue(state: AppState, terminal_width: int = 80) -> Panel:
    """Renders the Queue & Autoplay panel.
    Portrait-optimized: truncates titles, shows fewer items on narrow screens."""
    lines = []
    is_portrait = terminal_width < 90
    inner_width = (terminal_width - 6) if is_portrait else (terminal_width // 2 - 6)
    max_title = max(10, inner_width - 12)  # room for "  1. " prefix + " 3:20" suffix
    max_items = 3 if is_portrait else 5
    
    if not state.queue and not state.current_track:
        lines.append("[dim]Queue is empty.[/]")
    else:
        if state.current_track:
            title = state.current_track.title
            if len(title) > max_title:
                title = title[:max_title - 2] + ".."
            lines.append(f"[#FF6B35]> {title}[/]")
            
        for i, track in enumerate(state.queue[:max_items], 1):
            dur = f"{track.duration // 60}:{track.duration % 60:02d}"
            title = track.title
            if len(title) > max_title:
                title = title[:max_title - 2] + ".."
            lines.append(f"[white]  {i}. {title}[/] [dim]{dur}[/]")
            
        remaining = len(state.queue) - max_items
        if remaining > 0:
            lines.append(f"[dim]  +{remaining} more[/]")

    lines.append("")
    radio = "[green]ON[/]" if state.is_radio_mode else "[dim]OFF[/]"
    lines.append(f"Radio: {radio}")
    
    content = Text.from_markup("\n".join(lines))
    
    return Panel(
        content,
        title="[bold]QUEUE[/]",
        border_style="white",
        padding=(0, 1) if is_portrait else (1, 2),
    )
