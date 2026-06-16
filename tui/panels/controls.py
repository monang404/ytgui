from rich.panel import Panel
from rich.text import Text

def render_controls(search_query: str = "", is_searching: bool = False,
                    msg: str = "", width: int = 80, compact: bool = False) -> Panel:
    """Renders the footer panel with controls and search input.
    Portrait-optimized: compact mode uses abbreviated shortcuts."""
    
    if compact:
        # Ultra-compact for very narrow screens
        shortcuts = (
            "[dim]P[/]:Play [dim]N[/]:Next [dim]B[/]:Prev [dim]S[/]:Stop\n"
            "[dim]U/D[/]:Vol [dim]M[/]:DL [dim]R[/]:Radio [dim]Q[/]:Quit"
        )
    elif width < 70:
        # Medium-compact
        shortcuts = (
            "[dim]\\[P][/] Play  [dim]\\[N][/] Next  [dim]\\[B][/] Prev  [dim]\\[S][/] Stop\n"
            "[dim]\\[U/D][/] Vol  [dim]\\[M][/] DL  [dim]\\[R][/] Radio  [dim]\\[Q][/] Quit"
        )
    else:
        shortcuts = (
            "[dim]\\[P][/] Pause/Play  [dim]\\[N][/] Next  [dim]\\[B][/] Prev  [dim]\\[S][/] Stop  [dim]\\[U][/] Vol+  [dim]\\[D][/] Vol-\n"
            "[dim]\\[M][/] Download & Cache  [dim]\\[R][/] Radio Mode  [dim]\\[L][/] Toggle Lyrics  [dim]\\[Q][/] Quit"
        )
    
    sep_width = max(10, min(width - 6, 70))
    
    if is_searching:
        search_prompt = f"[bold #FFC107]SEARCH> {search_query}_[/]"
    else:
        search_prompt = "[dim]/ to search[/]"
    
    lines = [
        shortcuts,
        "─" * sep_width,
        search_prompt,
    ]
    if msg:
        # Truncate message to fit width
        max_msg = max(10, width - 8)
        display_msg = msg[:max_msg] + ".." if len(msg) > max_msg else msg
        lines.append(f"[#FFC107]{display_msg}[/]")
        
    content = Text.from_markup("\n".join(lines))
    
    return Panel(
        content,
        title="[bold]CONTROLS[/]",
        border_style="#FFC107" if is_searching else "dim",
        padding=(0, 1),
    )
