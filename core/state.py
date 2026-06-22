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

class PlaybackMode(Enum):
    QUEUE = auto()   # user-directed
    RADIO = auto()   # autonomous, self-sustaining

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

@dataclass
class AppState:
    # Playback
    status:          PlayerStatus  = PlayerStatus.IDLE
    playback_mode:   PlaybackMode  = PlaybackMode.QUEUE
    audio_output:    str           = "device"
    current_track:   Optional[TrackInfo] = None
    position:        float = 0.0
    volume:          int   = 80
    sponsorblock_active: bool = False

    # Queue (hanya aktif di QUEUE mode)
    queue:           deque = field(default_factory=deque)
    # Radio (hanya aktif di RADIO mode) — TIDAK PERNAH dicampur dengan `queue`.
    # Radio harus independen dari Queue Mode (lihat Constitution).
    radio_queue:     deque = field(default_factory=deque)
    history:         deque = field(default_factory=lambda: deque(maxlen=50))

    # Lyrics
    lyrics_lines:    list[tuple[float, str]] = field(default_factory=list)
    lyrics_index:    int = 0
    lyrics_offset:   float = 0.0

    # UI state
    active_tab:      str  = "home"    # "home"|"search"|"radio"|"queue"
    error_msg:       Optional[str] = None
    is_online:       bool = True

    # Download
    download_progress: Optional[float] = None  # 0.0–1.0, None = idle
