import asyncio
import random
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical, Center
from core.state import AppState, PlayerStatus
from tui.theme import TEXT_DIM, ACCENT_GOLD, TEXT_PRIMARY
from rich.markup import escape

EQ_WIDTH = 39
EQ_HEIGHT = 8

def generate_multiline_eq(is_playing: bool) -> str:
    if not is_playing:
        empty_rows = "\n".join(" " * EQ_WIDTH for _ in range(EQ_HEIGHT - 1))
        bottom_row = "[dim]" + "▄" * EQ_WIDTH + "[/dim]"
        return empty_rows + "\n" + bottom_row

    lines = []
    
    # 10 bands, each width 3, 1 space between
    num_bands = 10
    band_width = 3
    band_heights = [random.randint(1, EQ_HEIGHT) for _ in range(num_bands)]
    
    for row in range(EQ_HEIGHT, 0, -1):
        line_chars = []
        for i in range(num_bands):
            h = band_heights[i]
            if h >= row:
                char = "█"
            elif h == row - 1:
                char = "▄"
            else:
                char = " "
            line_chars.append(char * band_width)
            if i < num_bands - 1:
                line_chars.append(" ") # space between bands
        
        # Color gradient based on row
        if row >= 7:
            color = "red"          # high bands
        elif row >= 4:
            color = "yellow"       # mid bands
        else:
            color = "green"        # low bands
            
        lines.append(f"[{color}]{''.join(line_chars)}[/{color}]")
        
    return "\n".join(lines)


class NowPlayingTab(Widget):
    """The Now Playing Tab showing large track info and a big responsive equalizer."""
    DEFAULT_CSS = """
    NowPlayingTab {
        height: 1fr;
        padding: 2 4;
        align: center middle;
    }
    #np_container {
        height: auto;
        align: center middle;
    }
    #np_eq {
        text-align: center;
        height: 8;
        margin-bottom: 3;
    }
    #np_title {
        text-align: center;
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }
    #np_artist {
        text-align: center;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="np_container"):
            self.eq_animation = Static(generate_multiline_eq(False), id="np_eq")
            self.title = Static("Belum ada lagu yang diputar", id="np_title")
            self.artist = Static("Cari lagu untuk memulai", id="np_artist")
            
            yield self.eq_animation
            yield self.title
            yield self.artist

    def on_mount(self) -> None:
        self._is_playing = False
        # Timer independen 0.1s (10 fps) agar animasi equalizer jauh lebih responsif dan mulus
        self.eq_timer = self.set_interval(0.1, self.tick_eq)

    def tick_eq(self) -> None:
        if self._is_playing:
            self.eq_animation.update(generate_multiline_eq(True))

    def update_state(self, state: AppState) -> None:
        track = state.current_track
        if not track:
            self.title.update("Belum ada lagu yang diputar")
            self.artist.update("Cari lagu untuk memulai")
            self._is_playing = False
            self.eq_animation.update(generate_multiline_eq(False))
            return

        self.title.update(escape(track.title))
        self.artist.update(escape(track.artist))

        # Toggle play/pause state
        was_playing = self._is_playing
        self._is_playing = (state.status == PlayerStatus.PLAYING)
        
        # Segera update ke flat line saat pause tanpa nunggu tick_eq
        if not self._is_playing and was_playing:
            self.eq_animation.update(generate_multiline_eq(False))
