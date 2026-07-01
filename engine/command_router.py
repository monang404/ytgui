import structlog
from core.command_bus import (
    command_bus,
    CMD_PLAY_TRACK, CMD_TOGGLE_PAUSE, CMD_NEXT, CMD_PREV, CMD_STOP, CMD_SEEK,
    CMD_SET_MODE, CMD_QUEUE_SELECT, CMD_QUEUE_REMOVE, CMD_QUEUE_ADD, CMD_QUEUE_REPLACE, CMD_QUEUE_REORDER,
    CMD_RADIO_RANDOMIZE, CMD_SET_OUTPUT, CMD_SET_SPONSORBLOCK, CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_VOLUME_SET,
    CMD_LYRICS_OFFSET
)


logger = structlog.get_logger(__name__)

class CommandRouter:
    """
    Rutes Global CommandBus requests ke RoomPlaybackController yang sesuai.
    """
    def __init__(self, playback_controller, volume_service):
        self.playback_controller = playback_controller
        self.volume_service = volume_service
        
        command_bus.register(CMD_PLAY_TRACK, self._route(lambda c, data: c._on_cmd_play_track(data)))
        command_bus.register(CMD_TOGGLE_PAUSE, self._route(lambda c, data: c._on_cmd_toggle_pause(data)))
        command_bus.register(CMD_NEXT, self._route(lambda c, data: c._on_next(data)))
        command_bus.register(CMD_PREV, self._route(lambda c, data: c._on_prev(data)))
        command_bus.register(CMD_STOP, self._route(lambda c, data: c._on_stop(data)))
        command_bus.register(CMD_SEEK, self._route(lambda c, data: c._on_seek(data)))
        command_bus.register(CMD_SET_MODE, self._route(lambda c, data: c._on_set_mode(data)))
        command_bus.register(CMD_QUEUE_SELECT, self._route(lambda c, data: c._on_queue_select(data)))
        command_bus.register(CMD_QUEUE_REMOVE, self._route(lambda c, data: c._on_queue_remove(data)))
        command_bus.register(CMD_QUEUE_ADD, self._route(lambda c, data: c._on_queue_add(data)))
        command_bus.register(CMD_QUEUE_REPLACE, self._route(lambda c, data: c._on_queue_replace(data)))
        command_bus.register(CMD_QUEUE_REORDER, self._route(lambda c, data: c._on_queue_reorder(data)))
        command_bus.register(CMD_RADIO_RANDOMIZE, self._route(lambda c, data: c._on_radio_randomize(data)))
        command_bus.register(CMD_SET_OUTPUT, self._route(lambda c, data: c._on_set_output(data)))
        command_bus.register(CMD_SET_SPONSORBLOCK, self._route(lambda c, data: c._on_set_sponsorblock(data)))
        command_bus.register(CMD_LYRICS_OFFSET, self._route(lambda c, data: c._on_lyrics_offset(data)))
        
        command_bus.register(CMD_VOLUME_UP, self._route_volume(lambda v, data: v._on_volume_up(data)))
        command_bus.register(CMD_VOLUME_DOWN, self._route_volume(lambda v, data: v._on_volume_down(data)))
        command_bus.register(CMD_VOLUME_SET, self._route_volume(lambda v, data: v._on_volume_set(data)))

    def _route(self, action):
        async def handler(data):
            import asyncio
            res = action(self.playback_controller, data)
            if asyncio.iscoroutine(res):
                return await res
            return res
        return handler

    def _route_volume(self, action):
        async def handler(data):
            import asyncio
            res = action(self.volume_service, data)
            if asyncio.iscoroutine(res):
                return await res
            return res
        return handler
