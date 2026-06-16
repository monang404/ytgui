from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static
from textual.reactive import reactive

from core.event_bus import (
    bus, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP,
    CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_DOWNLOAD, CMD_TOGGLE_RADIO,
    CMD_TOGGLE_LYRICS, CMD_QUIT
)

class ControlsPanel(Static):
    """The bottom controls panel with clickable buttons."""

    status_msg = reactive("")

    def compose(self) -> ComposeResult:
        with Vertical():
            self.status_label = Static("", id="status_msg", classes="status-label")
            yield self.status_label
            with Horizontal(id="controls_row"):
                yield Button("⏮  Prev", id="btn_prev")
                yield Button("⏯  Play/Pause", id="btn_pause")
                yield Button("⏭  Next", id="btn_next")
                yield Button("⏹  Stop", id="btn_stop")
                yield Button("🔉 Vol-", id="btn_voldown")
                yield Button("🔊 Vol+", id="btn_volup")
                yield Button("⬇  DL", id="btn_dl")
                yield Button("📻 Radio", id="btn_radio")
                yield Button("📝 Lyrics", id="btn_lyrics")
                yield Button("🚪 Quit", id="btn_quit", variant="error")

    def watch_status_msg(self, msg: str) -> None:
        if hasattr(self, 'status_label'):
            self.status_label.update(msg)

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
            await bus.publish(CMD_TOGGLE_LYRICS)
        elif button_id == "btn_quit":
            await bus.publish(CMD_QUIT)
