import math
import time
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from rich.markup import escape
from textual.reactive import reactive
from textual import events

from core.event_bus import bus, CMD_SEEK
from core.state import AppState, PlayerStatus
from tui.theme import TEXT_DIM, ACCENT_GOLD, STATUS_ERR, TEXT_PRIMARY, ACCENT_FIRE

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

class ClickableProgressBar(Static):
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

class NowPlayingPanel(Widget):
    """The Now Playing panel with EQ and Progress Bar."""

    status_msg = reactive("")

    def compose(self) -> ComposeResult:
        with Vertical():
            self.info_label = Static("", id="np_info")
            self.progress_bar = ClickableProgressBar("", id="np_progress")
            self.status_line = Static("", id="np_status", classes="status-label")
            yield self.info_label
            yield self.progress_bar
            yield self.status_line

    def watch_status_msg(self, msg: str) -> None:
        if hasattr(self, 'status_line'):
            self.status_line.update(msg)

    def update_state(self, state: AppState) -> None:
        is_playing = state.status == PlayerStatus.PLAYING
        inner_width = self.size.width if self.size.width > 0 else 40
        n_bars = max(6, min(16, inner_width // 2))
        
        eq_text = _equalizer_frame(time.time(), n_bars, is_playing)
        is_compact = self.size.height <= 8
        
        if state.status == PlayerStatus.ERROR and getattr(state, 'error_msg', ''):
            self.info_label.update(
                f"\n[bold {STATUS_ERR}]  ⚠ Error Sistem[/]\n\n"
                f"[{TEXT_DIM}]  {escape(state.error_msg)}[/]\n\n"
                f"[{TEXT_DIM}]  Restart aplikasi setelah masalah teratasi.[/]"
            )
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.status_line.display = not is_compact
            return

        if state.status == PlayerStatus.LOADING:
            dots = "." * (int(time.time() * 2) % 4)
            track_name = state.current_track.title if state.current_track else "..."
            self.info_label.update(
                f"\n[{ACCENT_GOLD}]  ⏳ Memuat{dots}[/]\n\n"
                f"[{TEXT_DIM}]  {escape(track_name[:40])}[/]\n\n"
                f"[{TEXT_DIM}]{eq_text}[/]"
            )
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.status_line.display = not is_compact
            return

        if not state.current_track:
            hint_lines = [
                "",
                f"[bold {TEXT_PRIMARY}]  YT Termux Player Pro[/]",
                "",
                f"[{TEXT_DIM}]  Tekan [bold {ACCENT_GOLD}]/[/] untuk mencari lagu[/]",
                f"[{TEXT_DIM}]  Ketik nama lagu atau artis, lalu Enter[/]",
                "",
            ]
            if not is_compact:
                hint_lines += [
                    f"[{TEXT_DIM}]  Shortcut: [bold]P[/]=Pause  [bold]N[/]=Next  [bold]B[/]=Prev[/]",
                    f"[{TEXT_DIM}]            [bold]U[/]/[bold]D[/]=Vol  [bold]R[/]=Radio  [bold]Q[/]=Quit[/]",
                    "",
                ]
            hint_lines.append(f"[{TEXT_DIM}]{eq_text}[/]")
            self.info_label.update("\n".join(hint_lines))
            self.progress_bar.position = 0
            self.progress_bar.duration = 0
            self.status_line.display = not is_compact
        else:
            track = state.current_track
            views = ""
            if track.view_count:
                if track.view_count >= 1_000_000:
                    views = f"{track.view_count / 1_000_000:.1f}M views"
                elif track.view_count >= 1_000:
                    views = f"{track.view_count / 1_000:.0f}K views"
                else:
                    views = f"{track.view_count} views"

            max_title_len = max(10, inner_width - 2)
            title_display = track.title[:max_title_len - 1] + "…" if len(track.title) > max_title_len else track.title
            artist_display = track.artist[:max_title_len - 1] + "…" if len(track.artist) > max_title_len else track.artist

            dur_str = f"{track.duration // 60}:{track.duration % 60:02d}"
            via_str = "Cache" if track.local_path else "Stream"
            
            if is_compact:
                lines = [
                    f"[bold {TEXT_PRIMARY}]  {escape(title_display)}[/]",
                    f"[{TEXT_DIM}]   {escape(artist_display)}[/]",
                    f"[{ACCENT_FIRE}]{eq_text}[/]"
                ]
                self.status_line.display = False
            else:
                lines = [
                    f"[bold {TEXT_PRIMARY}]  {escape(title_display)}[/]",
                    f"[{TEXT_DIM}]   {escape(artist_display)}[/]",
                    f"[{TEXT_DIM}]   {views}  |  Via: {via_str}  |  Vol: {state.volume}%[/]",
                    "",
                    f"[{ACCENT_FIRE}]{eq_text}[/]",
                    ""
                ]
                self.status_line.display = True
                
            self.info_label.update("\n".join(lines))
            self.progress_bar.position = state.position
            self.progress_bar.duration = track.duration
