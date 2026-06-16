from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto

class PlayerStatus(Enum):
    IDLE = auto()
    LOADING = auto()
    PLAYING = auto()
    PAUSED = auto()
    BUFFERING = auto()
    ERROR = auto()

@dataclass
class TrackInfo:
    video_id:    str
    title:       str
    artist:      str
    duration:    int           # seconds
    thumbnail:   Optional[str] = None
    local_path:  Optional[str] = None   # None = streaming
    stream_url:  Optional[str] = None
    view_count:  Optional[int] = None

@dataclass
class AppState:
    """
    Mutable singleton container for application state.

    WARNING (HIGH-01): Only mutate from the main asyncio event loop.
    Never mutate directly from executor threads. InputHandler runs
    _read_char in an executor but dispatches mutations via EventBus
    which executes handlers back on the event loop — this is safe.
    """
    status:         PlayerStatus = PlayerStatus.IDLE
    current_track:  Optional[TrackInfo] = None
    queue:          list[TrackInfo] = field(default_factory=list)
    history:        list[TrackInfo] = field(default_factory=list)  # for CMD_PREV
    position:       float = 0.0          # seconds
    volume:         int = 80
    is_radio_mode:  bool = False
    show_lyrics:    bool = True
    lyrics_lines:   list[str] = field(default_factory=list)
    lyrics_index:   int = 0
    error_msg:      Optional[str] = None
    is_online:      bool = True
    next_uri_ready: Optional[str] = None
