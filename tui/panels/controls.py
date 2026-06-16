from rich.panel import Panel
from rich.text import Text

def render_controls(search_query: str = "", is_searching: bool = False,
                    msg: str = "", width: int = 80, compact: bool = False) -> Panel:
    """Renders the footer panel with controls and search input.
    Portrait-optimized: compact mode uses abbreviated shortcuts."""
    
    if is_searching:
        search_prompt = f"[bold #FFC107]SEARCH> {search_query}_[/]"
    else:
        search_prompt = "[bold #FFC107]Press '/' to Search[/]"

    if compact:
        # Ultra-compact for very narrow screens (2 lines total)
        lines = [
            f"{search_prompt} [dim]| P:Play N:Next S:Stop Q:Quit[/]",
            "[dim]U/D:Vol M:DL R:Radio L:Lyrics B:Prev[/]"
        ]
    elif width < 70:
        # Medium-compact (2 lines total)
        lines = [
            f"{search_prompt}  [dim]| \\[P] Play  \\[N] Next  \\[S] Stop  \\[Q] Quit[/]",
            "[dim]\\[U/D] Vol  \\[M] DL  \\[R] Radio  \\[L] Lyrics  \\[B] Prev[/]"
        ]
    else:
        # Full width (3 lines total)
        lines = [
            search_prompt,
            "[dim]\\[P] Pause/Play  \\[N] Next  \\[B] Prev  \\[S] Stop  \\[U/D] Vol+/-[/]",
            "[dim]\\[M] Download & Cache  \\[R] Radio Mode  \\[L] Toggle Lyrics  \\[Q] Quit[/]"
        ]
    
    if msg:
        # Override the last line with status message if exists
        max_msg = max(10, width - 8)
        display_msg = msg[:max_msg] + ".." if len(msg) > max_msg else msg
        lines[-1] = f"[#FFC107]{display_msg}[/]"
        
    content = Text.from_markup("\n".join(lines))
    
    return Panel(
        content,
        title="[bold]CONTROLS[/]",
        border_style="#FFC107" if is_searching else "dim",
        padding=(0, 1),
    )
