from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical
from rich.markup import escape
from core.state import AppState

class LyricsPanel(Widget):
    """The Synchronized Lyrics panel."""

    def compose(self) -> list[Widget]:
        with Vertical():
            self.content = Static("", id="lyrics_content")
            yield self.content

    def update_state(self, state: AppState) -> None:
        lines = []
        
        if not state.lyrics_lines:
            lines.append("[dim]No lyrics available.[/]")
        else:
            active_idx = state.lyrics_index
            total = len(state.lyrics_lines)
            window_size = min(4, max(2, total // 6))
            
            for i in range(active_idx - window_size, active_idx + window_size + 1):
                if i < 0 or i >= total:
                    continue
                    
                text = state.lyrics_lines[i]
                if not text:
                    continue
                    
                if i == active_idx:
                    lines.append(f"[bold #FF6B35]> {escape(text)}[/]")
                elif i < active_idx:
                    dist = active_idx - i
                    style = "dim" if dist > 2 else ("#666666" if dist > 1 else "#888888")
                    lines.append(f"[{style}]  {escape(text)}[/]")
                else:
                    dist = i - active_idx
                    style = "dim" if dist > 2 else ("#AAAAAA" if dist > 1 else "#CCCCCC")
                    lines.append(f"[{style}]  {escape(text)}[/]")

        self.content.update("\n".join(lines))
