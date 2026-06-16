import asyncio
import time
import datetime
import logging
import os
from rich.live import Live
from rich.layout import Layout
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.event_bus import bus, LOG_MESSAGE, CMD_QUIT
from tui.panels.now_playing import render_now_playing
from tui.panels.queue_panel import render_queue
from tui.panels.lyrics_panel import render_lyrics
from tui.panels.controls import render_controls

logger = logging.getLogger(__name__)

class Dashboard:
    def __init__(self, state, input_handler):
        self.state = state
        self.input_handler = input_handler
        # Force UTF-8 output on Windows to prevent encoding issues
        if os.name == 'nt':
            import sys
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        self.console = Console()
        self._quit = False
        self._status_msg = ""
        self._status_msg_time = 0.0
        self._last_width = 0

    def _make_layout(self) -> Layout:
        """Build a fresh layout based on current terminal size."""
        width = self.console.size.width
        height = self.console.size.height
        layout = Layout(name="root")

        if width < 90:
            # PORTRAIT (Termux / HP / Narrow CMD)
            if height < 30:
                layout.split_column(
                    Layout(name="header", size=1),
                    Layout(name="now_playing", ratio=5),
                    Layout(name="queue", ratio=3),
                    Layout(name="footer", size=4),
                )
            else:
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="now_playing", ratio=5),
                    Layout(name="queue", ratio=2),
                    Layout(name="lyrics", ratio=3),
                    Layout(name="footer", size=5),
                )
        else:
            # LANDSCAPE (Desktop)
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=6),
            )
            layout["body"].split_row(
                Layout(name="now_playing", ratio=1),
                Layout(name="right", ratio=1),
            )
            layout["right"].split_column(
                Layout(name="queue", ratio=2),
                Layout(name="lyrics", ratio=3),
            )
        return layout

    def _render_header(self) -> Panel:
        width = self.console.size.width
        clock = datetime.datetime.now().strftime("%H:%M")
        status_color = "green" if self.state.is_online else "red"

        if width < 50:
            hdr = Text.from_markup(
                f"[bold white]YTPLAYER[/]  [{status_color}]{'ON' if self.state.is_online else 'OFF'}[/]  {clock}"
            )
        else:
            grid = Table.grid(expand=True)
            grid.add_column(justify="left", style="bold white")
            grid.add_column(justify="right", style=f"bold {status_color}")
            st = "[ONLINE]" if self.state.is_online else "[OFFLINE]"
            grid.add_row("YT TERMUX PLAYER PRO v1.0", f"{st}  {clock}")
            hdr = grid
        return Panel(hdr, style="on #1A1A2E", padding=(0, 1))

    def _fill_layout(self, layout: Layout):
        """Populate every panel slot with rendered content."""
        width = self.console.size.width
        height = self.console.size.height
        is_portrait = width < 90
        is_tiny = height < 30 and is_portrait

        # Expire old status messages
        if self._status_msg and (time.time() - self._status_msg_time > 5.0):
            self._status_msg = ""

        layout["header"].update(self._render_header())
        layout["now_playing"].update(render_now_playing(self.state, width))
        layout["queue"].update(render_queue(self.state, width))

        # Lyrics: hide on tiny portrait, respect toggle
        if not is_tiny:
            if self.state.show_lyrics:
                layout["lyrics"].update(render_lyrics(self.state))
            else:
                layout["lyrics"].update(
                    Panel("[dim]Press \\[L] for lyrics[/]",
                          title="[bold]LYRICS[/]", border_style="dim")
                )

        layout["footer"].update(render_controls(
            search_query=self.input_handler.search_buffer,
            is_searching=self.input_handler.is_searching,
            msg=self._status_msg,
            width=width,
            compact=(width < 50),
        ))

    async def run(self):
        bus.subscribe(LOG_MESSAGE, self._on_log_message)
        bus.subscribe(CMD_QUIT, self._on_quit)

        # Build initial layout
        layout = self._make_layout()
        self._fill_layout(layout)
        self._last_width = self.console.size.width

        # screen=True for proper full-screen rendering.
        # refresh_per_second=1 — low auto-refresh to reduce flicker.
        # We manually call live.refresh() at ~3fps in the loop.
        live = Live(
            layout,
            console=self.console,
            screen=True,
            refresh_per_second=1,
            transient=True,
        )

        with live:
            while not self._quit:
                # Rebuild layout only if terminal width actually changed
                new_width = self.console.size.width
                if new_width != self._last_width:
                    self._last_width = new_width
                    layout = self._make_layout()
                    live.update(layout)

                self._fill_layout(layout)
                live.refresh()
                await asyncio.sleep(0.3)  # ~3 fps — smooth enough, less flicker

    async def _on_log_message(self, msg: str):
        self._status_msg = str(msg)
        self._status_msg_time = time.time()

    async def _on_quit(self, _):
        self._quit = True
