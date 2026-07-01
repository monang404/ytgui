"""
Purpose: Menyimpan state aplikasi YTGUI V2, termasuk status pemutar, mode pemutaran, lagu saat ini, antrean, riwayat, status download, lirik, dan tab aktif.
Subscribes to: (tidak ada)
Publishes: (tidak ada)
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
from collections import deque

class PlayerStatus(Enum):
    IDLE     = auto()
    LOADING  = auto()
    PLAYING  = auto()
    PAUSED   = auto()
    ERROR    = auto()

class AudioOutput(str, Enum):
    DEVICE = "device"
    BROWSER = "browser"

class PlaybackMode(Enum):
    QUEUE = auto()
    RADIO = auto()

@dataclass
class TrackInfo:
    video_id:   str
    title:      str
    artist:     str
    duration:   int
    thumbnail:  Optional[str] = None
    local_path: Optional[str] = None
    stream_url: Optional[str] = None
    view_count: Optional[int] = None
    stream_url_ts: Optional[int] = None
    play_count: Optional[int] = None
    last_played: Optional[int] = None
    is_favorite: Optional[int] = 0

@dataclass
class AppState:
    status:          PlayerStatus  = PlayerStatus.IDLE
    playback_mode:   PlaybackMode  = PlaybackMode.QUEUE
    audio_output:    AudioOutput   = AudioOutput.BROWSER
    current_track:   Optional[TrackInfo] = None
    position:        float = 0.0
    duration:        float = 0.0
    volume:          int   = 80
    sponsorblock_active: bool = True

    queue:           deque = field(default_factory=deque)
    radio_queue:     deque = field(default_factory=deque)
    history:         deque = field(default_factory=lambda: deque(maxlen=50))

    lyrics_lines:    list[str] = field(default_factory=list)
    lyrics_timestamps: list[float] = field(default_factory=list)
    lyrics_index:    int = 0
    lyrics_offset:   float = 0.0
    lyrics_loading:  bool = False

    active_tab:      str  = "home"
    error_msg:       Optional[str] = None
    is_online:       bool = True

    download_progress: Optional[float] = None
