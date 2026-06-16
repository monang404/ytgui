class YtPlayerError(Exception):
    """Base exception for YT Termux Player Pro."""
    pass

class MpvConnectionError(YtPlayerError):
    """Raised when unable to connect to the mpv IPC socket."""
    pass

class TrackResolutionError(YtPlayerError):
    """Raised when unable to resolve a track's stream URL or local path."""
    pass

class DownloadError(YtPlayerError):
    """Raised when yt-dlp fails to download a track."""
    pass
