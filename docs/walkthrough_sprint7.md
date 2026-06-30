# Sprint 7: Backend Cleanup Walkthrough

## What was accomplished

All 3 tasks in Sprint 7 (S7-01, S7-02, S7-03) have been completed successfully. This sprint focused on modularizing and cleaning up the Python backend infrastructure.

1. **`server/app.py` Modularization (S7-01, S7-02)**
   - Extracted all inline event bus subscribers out of `create_app()` into a dedicated setup function inside `server/handlers/event_listeners.py`.
   - Extracted stream URL pre-fetching logic (`_prefetch_stream_url`) into `server/services/stream_prefetch.py`.
   - Extracted WebSocket broadcasting abstractions (`manager.broadcast()`) into `server/services/broadcast_service.py`.
   - `server/app.py` is now strictly focused on routing and dependency injection. Its line count dropped from **172 lines** to **64 lines**.

2. **Playback Controller Subpackage (S7-03)**
   - The monolithic `engine/playback_controller.py` (352 lines) was entirely removed.
   - It was split into a cohesive subpackage under `engine/playback/`:
     - `controller.py`: The `PlaybackController` class responsible for orchestrating state, locking mechanisms, and command delegation.
     - `track_loader.py`: The `TrackLoader` class responsible for URL resolution (via `CacheResolver`), side-task initiation (SponsorBlock, Lyrics), and incrementing DB play counts.
     - `__init__.py`: Preserves the public API, so `from engine.playback import PlaybackController` works properly.
   - All external imports (e.g., in `room_manager.py`, `radio_engine.py`, `queue_manager.py`, and test files) were refactored to point to `engine.playback`.

## Testing & Validation
- **Unit & Integration Tests**: `pytest tests/` was executed at the start and the end of the sprint. The refactoring did not introduce any regressions.
- Note that 8 pre-existing test failures related to older bugs (from `test_radio.py`, `test_lyrics.py`, `test_server_perf.py`, etc.) are still failing, as intended, since Sprint 7 does not address those issues.
- One test module (`test_ws_broadcast.py`) that strictly checked the source code of `server.app` was updated to check the newly extracted `broadcast_service.py`.
