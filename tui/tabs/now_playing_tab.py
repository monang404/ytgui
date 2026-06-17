import asyncio
import random
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Vertical, Center
from core.state import AppState, PlayerStatus
from tui.theme import TEXT_DIM, ACCENT_GOLD, TEXT_PRIMARY
from rich.markup import escape

ASCII_ART = """[#A0A0C0]
       .─────.       
     .'       '.     
    /           \    
   |    [#FFA500]( O )[/#A0A0C0]    |   
    \           /    
     '.       .'     
       `─────'       
[/]"""

BARS = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

class NowPlayingTab(Widget):
    """The Now Playing Tab showing large track info and an equalizer."""
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
    #np_art {
        text-align: center;
        margin-bottom: 2;
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
        margin-bottom: 2;
    }
    #np_eq {
        text-align: center;
        height: 1;
        margin-top: 1;
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="np_container"):
            yield Static(ASCII_ART, id="np_art")
            self.title = Static("Belum ada lagu yang diputar", id="np_title")
            self.artist = Static("Cari lagu untuk memulai", id="np_artist")
            self.eq_animation = Static("", id="np_eq")
            yield self.title
            yield self.artist
            yield self.eq_animation

    def update_state(self, state: AppState) -> None:
        track = state.current_track
        if not track:
            self.title.update("Belum ada lagu yang diputar")
            self.artist.update("Cari lagu untuk memulai")
            self.eq_animation.update("")
            return

        self.title.update(escape(track.title))
        self.artist.update(escape(track.artist))

        # Equalizer Animation
        if state.status == PlayerStatus.PLAYING:
            # Generate random bars
            eq_str = "".join(random.choice(BARS) for _ in range(30))
            self.eq_animation.update(eq_str)
        else:
            # Flat line when paused or stopped
            self.eq_animation.update(f"[{TEXT_DIM}]" + " " * 30 + f"[/{TEXT_DIM}]")
