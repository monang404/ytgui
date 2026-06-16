import math
import time
from rich.panel import Panel
from rich.text import Text
from core.state import AppState, PlayerStatus

_BAR_CHARS = "▁▂▃▄▅▆▇█"

def _equalizer_frame(t: float, n_bars: int = 16, is_playing: bool = True) -> str:
    """Pseudo-random animated equalizer based on layered sine waves."""
    if not is_playing:
        return "▁" * n_bars
    
    bars = []
    for i in range(n_bars):
        phase = (t * 3.7 + i * 0.8) % (2 * math.pi)
        val = (math.sin(phase) + math.sin(t * 7.1 + i * 1.3)) / 2
        normalized = int((val + 1) / 2 * 7)
        normalized = max(0, min(7, normalized))
        bars.append(_BAR_CHARS[normalized])
        if (i + 1) % 4 == 0:
            bars.append(" ")
    return "".join(bars)

def render_progress(position: float, duration: float, bar_width: int = 20) -> str:
    """Renders the text-based progress bar."""
    if duration <= 0:
        return ""
    pct = min(1.0, position / duration)
    filled = int(pct * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    pos_str = f"{int(position//60):02d}:{int(position%60):02d}"
    dur_str = f"{int(duration//60):02d}:{int(duration%60):02d}"
    return f"[dim]{pos_str}[/] {bar} [dim]{dur_str}[/]"

def render_now_playing(state: AppState, terminal_width: int = 80) -> Panel:
    """Renders the Now Playing panel, adapting to terminal width."""
    is_playing = state.status == PlayerStatus.PLAYING
    is_portrait = terminal_width < 90
    
    # Responsive sizing
    panel_width = terminal_width if is_portrait else terminal_width // 2
    # Account for panel border + padding (2 border + 4 padding = 6)
    inner_width = panel_width - 6
    n_bars = max(6, min(16, inner_width // 2))
    bar_width = max(8, min(30, inner_width - 14))  # 14 = "00:00 " x2 + margin
    
    eq_text = _equalizer_frame(time.time(), n_bars, is_playing)
    
    if not state.current_track:
        content = Text.from_markup(
            "\n[dim]  No track selected.[/]\n\n"
            f"[dim]{eq_text}[/]"
        )
    else:
        track = state.current_track
        # Format view count
        views = ""
        if track.view_count:
            if track.view_count >= 1_000_000:
                views = f"{track.view_count / 1_000_000:.1f}M views"
            elif track.view_count >= 1_000:
                views = f"{track.view_count / 1_000:.0f}K views"
            else:
                views = f"{track.view_count} views"

        # Truncate title if too long for panel
        max_title_len = inner_width - 2
        title_display = track.title[:max_title_len] + ".." if len(track.title) > max_title_len else track.title
        artist_display = track.artist[:max_title_len] + ".." if len(track.artist) > max_title_len else track.artist

        dur_str = f"{track.duration // 60}:{track.duration % 60:02d}"
        via_str = "Cache" if track.local_path else "Stream"
        
        if is_portrait and inner_width < 40:
            # Ultra-compact: everything tight
            lines = [
                f"[bold white]{title_display}[/]",
                f"[dim]{artist_display}[/]",
                f"[dim]{dur_str}  {via_str}[/]",
                "",
                f"[#FF6B35]{eq_text}[/]",
                render_progress(state.position, track.duration, bar_width),
                f"[dim]Vol:{state.volume}%[/]",
            ]
        else:
            lines = [
                f"[bold white]  {title_display}[/]",
                f"[dim]   {artist_display}[/]",
                f"[dim]   {views}  |  {dur_str}[/]" if views else f"[dim]   {dur_str}[/]",
                f"[dim]   Via: {via_str}[/]",
                "",
                f"[#FF6B35]{eq_text}[/]",
                "",
                render_progress(state.position, track.duration, bar_width),
                "",
                f"Vol: {state.volume}%   Gapless: {'ON' if state.next_uri_ready else 'OFF'}"
            ]
        content = Text.from_markup("\n".join(lines))

    # Reduce padding on narrow screens
    pad = (0, 1) if is_portrait and inner_width < 40 else (1, 2)

    return Panel(
        content,
        title="[bold]NOW PLAYING[/]",
        border_style="#FF6B35" if is_playing else "dim",
        padding=pad,
    )
