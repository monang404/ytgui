from rich.panel import Panel
from rich.text import Text
from core.state import AppState

def render_lyrics(state: AppState) -> Panel:
    """Renders the Synchronized Lyrics panel.
    Portrait-optimized: compact padding, gradient coloring."""
    lines = []
    
    if not state.lyrics_lines:
        lines.append("[dim]No lyrics available.[/]")
    else:
        active_idx = state.lyrics_index
        total = len(state.lyrics_lines)
        window_size = min(4, max(2, total // 6))
        
        for i in range(active_idx - window_size, active_idx + window_size + 1):
            if i < 0 or i >= total:
                continue  # Don't add blank lines — saves vertical space
                
            text = state.lyrics_lines[i]
            if not text:
                continue
                
            if i == active_idx:
                lines.append(f"[bold #FF6B35]> {text}[/]")
            elif i < active_idx:
                dist = active_idx - i
                style = "dim" if dist > 2 else ("#666666" if dist > 1 else "#888888")
                lines.append(f"[{style}]  {text}[/]")
            else:
                dist = i - active_idx
                style = "dim" if dist > 2 else ("#AAAAAA" if dist > 1 else "#CCCCCC")
                lines.append(f"[{style}]  {text}[/]")

    content = Text.from_markup("\n".join(lines))
    
    return Panel(
        content,
        title="[bold]LYRICS[/]",
        border_style="white",
        padding=(0, 1),
    )
