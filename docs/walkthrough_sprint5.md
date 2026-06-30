# Walkthrough: Sprint 5 — JS Events Split

Sprint 5 has been successfully completed. The massive `events.js` file (over 700 lines of code) has been entirely refactored and modularized into a new `events/` folder. This drastically improves code navigation and separation of concerns by grouping event bindings logically.

## Refactoring Overview (S5-01)

### 1. `events/player-events.js`
This module now encapsulates all logic related to media playback controls and player interactions, including:
- Mini player interactions (tap-to-home from Sprint 0 S0-06).
- Play/Pause/Next/Prev buttons and global shortcuts (`keydown`).
- Progress bar manipulation (`pointerdown`, `pointermove`, `pointerup`).
- Volume slider handling.
- Event delegation for playing tracks from the Discover, Favorites, and Search result lists.
- Search functionality (input debouncing, sending search requests, clear button).
- Radio toggles and download/output buttons.

### 2. `events/queue-events.js`
Dedicated exclusively to the queue list functionality:
- Queue item selection and removal.
- The complex Pointer Events API-based drag-and-drop logic for reordering queue items.

### 3. `events/lyrics-events.js`
Manages all interactions related to the lyrics view:
- Opening and closing the lyrics overlay.
- Triggering lyric synchronization controls and adjusting the lyrics offset.

### 4. `events/settings-events.js`
Consolidates the settings and help modal interactions:
- Opening and closing settings and help sheets.
- Global functions: `openSettings()`, `closeSettings()`, `renderSettingsSheet()`, and `closeMainOverlay()`.
- Toggling SponsorBlock, Audio Output destination, and stopping playback.

### 5. `events/index.js`
Acts as the central point for initializing all event listeners across the application.
- Replaces the original `events.js` entry point.
- Directly handles UI/navigation events (mood cards, portal auth buttons).
- Sequentially calls the initialization functions of all sub-modules:
  - `initPlayerEvents()`
  - `initQueueEvents()`
  - `initLyricsEvents()`
  - `initSettingsEvents()`

## Configuration and Cleanup
- The original `web/static/js/events.js` file has been safely removed.
- `web/static/index.html` was updated to import all these new scripts inside the `<script>` block before `main.js` and `portal.js`.

## Validation
- `CURRENT_TASK.md` has been updated to mark Sprint 5 as **Done**.
- The `Current Sprint` status is now **SPRINT 6**.
