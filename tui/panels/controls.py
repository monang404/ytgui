from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Button, Static

from core.event_bus import (
    bus, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_RADIO,
    CMD_TOGGLE_LYRICS, CMD_QUIT
)

class ControlsPanel(Static):
    """The bottom controls panel with clickable buttons."""

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="controls_primary"):
                yield Button("⏮", id="btn_prev", classes="ctrl-sm")
                yield Button("⏯  PLAY / PAUSE", id="btn_pause", classes="ctrl-primary")
                yield Button("⏭", id="btn_next", classes="ctrl-sm")

            with Grid(id="controls_secondary"):
                yield Button("⏹ Stop", id="btn_stop")
                yield Button("🔉", id="btn_voldown")
                yield Button("🔊", id="btn_volup")
                yield Button("📻 Radio", id="btn_radio")
                yield Button("📝 Lirik", id="btn_lyrics")
                yield Button("⬇ DL", id="btn_dl")

            with Horizontal(id="controls_danger"):
                yield Button("🚪 Keluar", id="btn_quit", variant="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn_pause":
            await bus.publish(CMD_TOGGLE_PAUSE)
        elif button_id == "btn_next":
            await bus.publish(CMD_NEXT)
        elif button_id == "btn_prev":
            await bus.publish(CMD_PREV)
        elif button_id == "btn_stop":
            await bus.publish(CMD_STOP)
        elif button_id == "btn_voldown":
            await bus.publish(CMD_VOLUME_DOWN)
        elif button_id == "btn_volup":
            await bus.publish(CMD_VOLUME_UP)
        elif button_id == "btn_dl":
            await bus.publish(CMD_DOWNLOAD)
        elif button_id == "btn_radio":
            await bus.publish(CMD_TOGGLE_RADIO)
        elif button_id == "btn_lyrics":
            await bus.publish("cmd.switch.lyrics.tab")
        elif button_id == "btn_quit":
            await bus.publish(CMD_QUIT)
