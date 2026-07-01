from dataclasses import dataclass
from typing import Any, Optional

from core.state import TrackInfo

@dataclass
class DomainEvent:
    """Base class for all domain events."""
    pass

@dataclass
class TrackStartedEvent(DomainEvent):
    track: Optional[TrackInfo] = None

@dataclass
class TrackEndedEvent(DomainEvent):
    reason: str = ""

@dataclass
class TrackProgressEvent(DomainEvent):
    position: float = 0.0

@dataclass
class TrackDurationEvent(DomainEvent):
    duration: float = 0.0

@dataclass
class QueueUpdatedEvent(DomainEvent):
    pass

@dataclass
class LyricsUpdatedEvent(DomainEvent):
    pass

@dataclass
class DownloadCompleteEvent(DomainEvent):
    track: Optional[TrackInfo] = None

@dataclass
class DownloadProgressEvent(DomainEvent):
    progress: float = 0.0

@dataclass
class LogMessageEvent(DomainEvent):
    message: str = ""

@dataclass
class TrackPauseChangedEvent(DomainEvent):
    is_paused: bool = False
