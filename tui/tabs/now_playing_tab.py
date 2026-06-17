import asyncio
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

class NowPlayingTab(Widget):
    """The Now Playing Tab showing large track info and lyrics."""
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
    #np_lyrics {
        text-align: center;
        color: $accent;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="np_container"):
            yield Static(ASCII_ART, id="np_art")
            self.title = Static("Belum ada lagu yang diputar", id="np_title")
            self.artist = Static("Cari lagu untuk memulai", id="np_artist")
            self.lyrics = Static("", id="np_lyrics")
            yield self.title
            yield self.artist
            yield self.lyrics

    def update_state(self, state: AppState) -> None:
        track = state.current_track
        if not track:
            self.title.update("Belum ada lagu yang diputar")
            self.artist.update("Cari lagu untuk memulai")
            self.lyrics.update("")
            return

        self.title.update(escape(track.title))
        self.artist.update(escape(track.artist))

        # Update Lirik
        if state.lyrics_lines and 0 <= state.lyrics_index < len(state.lyrics_lines):
            current_line = state.lyrics_lines[state.lyrics_index]
            # Format text as bold to make it clear it's the lyric
            self.lyrics.update(f"[bold]{escape(current_line[1])}[/bold]")
        else:
            if state.status == PlayerStatus.PLAYING:
                self.lyrics.update(f"[{TEXT_DIM}]...[/{TEXT_DIM}]")
            else:
                self.lyrics.update("")
