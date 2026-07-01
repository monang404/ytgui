"""
Shared fixtures for all unit tests.
"""

import pytest
import asyncio
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

from core.log_config import setup_logging

setup_logging()

from core.event_bus import EventBus
from core.state import AppState, TrackInfo, PlayerStatus, PlaybackMode


@pytest.fixture
def bus():
    """Fresh EventBus instance for each test."""
    return EventBus()


@pytest.fixture
def state():
    """Fresh AppState instance for each test."""
    return AppState()


@pytest.fixture
def sample_track():
    """A sample TrackInfo for testing."""
    return TrackInfo(
        video_id="dQw4w9WgXcQ",
        title="Never Gonna Give You Up",
        artist="Rick Astley",
        duration=212,
        thumbnail="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    )


@pytest.fixture
def sample_track_2():
    """A second sample TrackInfo for testing."""
    return TrackInfo(
        video_id="xvFZjo5PgG0",
        title="Bohemian Rhapsody",
        artist="Queen",
        duration=354,
        thumbnail="https://i.ytimg.com/vi/xvFZjo5PgG0/hqdefault.jpg",
    )


@pytest.fixture
def sample_track_3():
    """A third sample TrackInfo for testing."""
    return TrackInfo(
        video_id="3tmd-ClpJxA",
        title="Somebody That I Used to Know",
        artist="Gotye",
        duration=244,
        thumbnail=None,
    )


@pytest.fixture
def sample_track_json():
    """Load raw yt-dlp dict from sample_track.json fixture file."""
    filepath = FIXTURES_DIR / "sample_track.json"
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
