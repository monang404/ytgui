# AI_PLAYBOOK.md
> AI Operating Manual — ytgui / bagas.fm
> Primary consumers: AI coding agents. Updated only on architecture changes.

---

## Executive Summary

| Field | Value |
|---|---|
| Project | ytgui (branded: **bagas.fm**) |
| Purpose | YouTube music player for Termux; browser-based remote UI over WebSocket |
| Stack | Python/aiohttp backend · Vanilla JS frontend · SQLite cache |
| Boundary | Single-room, single-server; no multi-tenancy; no cloud sync |
| Active Refactor | SPRINT 0–8 per MASTER_PLAN (CSS/JS restructure + feature gaps) |

---

## Product Overview

**Users**
- `admin` — full control (play, queue, settings, download)
- `client` — view-only (listen, discover)
- `portal` — unauthenticated; sees login screen only

**Tabs**
| Tab | Purpose |
|---|---|
| home | Now Playing: vinyl, lyrics, queue, player bar |
| search | Full-text track search → enqueue or play |
| radio | Autonomous radio mode (Bagas FM); toggle on/off |
| discover | Browseable history, mood cards, favorites, cached tracks |

**Core Workflows**
1. Auth → WS connect → `auth` cmd → `applyRoleUI()`
2. Play: user action → `wsSend(action)` → backend cmd → `state` msg → `renderFullState()`
3. Radio: toggle btn → `wsSend("radio_toggle")` → `radio_engine._gather_batch()` → continuous auto-next
4. Search: input → `wsSend("search")` → `search_results` msg → `renderSearchResults()`
5. Discover: tab switch / WS open → `wsSend("discover")` → `discover_data` msg → `renderDiscoverTab()`

---

## System Architecture

### Frontend (Vanilla JS, no bundler)

```
web/static/
├── index.html            ← single page; all tabs, sheets, nav
├── css/
│   ├── tokens.css        ← design tokens (colors, spacing, radius) — single source of truth
│   ├── base.css          ← reset + typography + @keyframes [TO BE SPLIT: SPRINT 1-3]
│   ├── layout.css        ← app shell + nav + grid [TO BE SPLIT: SPRINT 2-3]
│   ├── player.css        ← player bar component [TO BE SPLIT: SPRINT 3]
│   ├── tabs.css          ← tab-panel base + nav [TO BE MERGED: SPRINT 3]
│   ├── components.css    ← cards, queue items, search results [TO BE SPLIT: SPRINT 3]
│   └── portal.css        ← login screen (stable, unchanged)
└── js/
    ├── config.js         ← TABS = ["home","search","radio","discover"]
    ├── store.js          ← global mutable state object (not reactive)
    ├── dom.js            ← initDOM() → builds `dom` object via getElementById
    ├── utils.js          ← formatTime, cleanTrackTitle, safeStorage (pending)
    ├── audio.js          ← Web Audio API, browser audio unlock, fake-beat rAF loop
    ├── portal.js         ← login/logout, applyRoleUI()
    ├── ws.js             ← wsConnect, wsSend, handleServerMessage, renderFullState
    ├── events.js         ← all DOM event listeners [TO BE SPLIT: SPRINT 5]
    ├── main.js           ← init(), switchTab(), visualViewport handler, swipe
    └── render/
        ├── player.js     ← renderPlayerBar, renderPlayBtn, renderProgress
        ├── tabs.js       ← renderNowPlaying, renderQueue, renderRadio, renderDiscoverTab [TO BE SPLIT: SPRINT 6]
        ├── lyrics.js     ← renderLyrics, syncLocalLyrics (also in ws.js)
        └── search.js     ← renderSearchResults, updateSearchPlayingState
```

**Script load order (index.html, current)**
```
config → store → dom → utils → render/player → render/tabs → render/lyrics →
render/search → audio → portal → ws → events → main
```

**CSS load order (index.html, current)**
```
tokens → base → layout → player → tabs → components → portal
```

### Backend (Python 3.11+, aiohttp)

```
ytgui/
├── main.py               ← startup: wires DI, creates aiohttp app, runs server
├── config.py             ← CACHE_DIR, STREAM_URL_TTL_SEC, ports, auth secrets
├── core/                 ← pure domain; no imports from server/ or engine/
│   ├── state.py          ← AppState, TrackInfo, PlayerStatus, PlaybackMode, AudioOutput enums
│   ├── events.py         ← domain event dataclasses (TrackStartedEvent, etc.)
│   ├── event_bus.py      ← pub/sub; subscribers registered at startup
│   ├── command_bus.py    ← dispatch commands to handlers
│   ├── ports.py          ← MediaExtractorPort, DatabasePort (interfaces)
│   ├── room_manager.py   ← RoomManager; holds dict of rooms (currently single "default")
│   ├── security.py       ← password hashing, token validation
│   ├── task_utils.py     ← safe_create_task (asyncio wrapper)
│   ├── exceptions.py     ← domain exceptions
│   ├── log_config.py     ← structlog setup
│   └── observability.py  ← metrics
├── engine/               ← business logic; imports core/ only
│   ├── playback_controller.py  ← state machine: IDLE/LOADING/PLAYING/PAUSED/ERROR [352 lines]
│   ├── radio_engine.py         ← autonomous radio batch generation [323 lines]
│   ├── mpv_controller.py       ← mpv subprocess wrapper
│   ├── ytdlp_client.py         ← yt-dlp stream URL resolution
│   ├── download_manager.py     ← background download queue
│   ├── queue_manager.py        ← queue operations (add, remove, reorder)
│   ├── volume_service.py       ← volume control
│   └── command_router.py       ← maps WS commands → engine actions [AT engine/ level, NOT in subdir]
├── cache/
│   ├── db.py             ← SQLite async adapter; get_track, upsert_track, get_random_songs [257 lines]
│   ├── resolver.py       ← CacheResolver: check local → stream_url → fetch
│   ├── schema.sql        ← table definitions
│   └── inject_svgs.py    ← utility
├── server/
│   ├── app.py            ← create_app(): route setup + inline event listeners [172 lines, needs cleanup]
│   ├── middleware.py      ← auth middleware
│   ├── serializers.py    ← state_to_dict for WS broadcast
│   └── handlers/
│       ├── http.py       ← serve_index, health_check, serve_stream, serve_metrics
│       ├── websocket.py  ← ws_handler, ConnectionManager.broadcast
│       └── auth.py       ← login/session handlers
├── services/
│   └── discover_service.py  ← queries db for recent/favorites/cached; single service
├── plugins/
│   ├── lyrics.py         ← LRC fetch + sync
│   ├── notifications.py  ← OS notifications
│   └── sponsorblock.py   ← SponsorBlock API
└── data/
    ├── ytgui.db          ← main SQLite DB
    └── artists.json / artists_enriched.json  ← 2500+ artists seed data (unused in queries)
```

---

# Architecture Decisions (ADR)

This section records architectural decisions that AI agents must preserve unless explicitly instructed otherwise.

---

## ADR-001 — Source of Truth

Status

Accepted

Decision

Source Code is the ultimate source of truth.

AI_PLAYBOOK.md is the verified architectural reference.

CURRENT_TASK.md is the execution backlog.

Rationale

Documentation may become outdated.

Source code reflects the actual implementation.

AI agents must always verify assumptions against source code.

Impact

- Documentation must never override implementation.
- Every architectural change requires updating AI_PLAYBOOK.md.

---

## ADR-002 — Architecture Stability

Status

Accepted

Decision

Prefer incremental improvements over architectural rewrites.

Rationale

Large-scale refactors introduce unnecessary regression risk.

Impact

AI agents should modify only the modules required for the current task.

Repository-wide refactoring is prohibited unless explicitly requested.

---

## ADR-003 — Public Contract Preservation

Status

Accepted

Decision

Public interfaces are considered stable contracts.

Includes

- Public APIs
- Event names
- State keys
- Database schema
- WebSocket payloads

Impact

Changing public contracts requires explicit approval and documentation updates.

---

## ADR-004 — Verification First

Status

Accepted

Decision

Every implementation must be verified before completion.

Required Verification

- Build
- Lint
- Tests
- Regression
- Manual Verification (if applicable)

Impact

No task may be marked as Done without successful verification.

---


### Database

**Engine:** SQLite (async via aiosqlite or similar)
**Schema file:** `cache/schema.sql`
**Key tables:** `tracks` (video_id PK, title, artist, duration, thumbnail, local_path, stream_url, stream_url_ts, play_count, last_played, is_favorite), `artists`/`genres` (seed data, not used in active queries)
**Key methods (db.py):**
- `get_track(video_id)` → TrackInfo | None
- `upsert_track(track)` → void
- `get_random_songs(limit, exclude_ids)` → list[TrackInfo] — **no artist filter parameter**
- `update_stream_url_only(video_id, url)` → void
- `get_all_artists()` → list[str]

### WebSocket Protocol

**Client → Server:** `{ type: "cmd", action: str, data: {} }`

| action | effect |
|---|---|
| `auth` | `{ token }` → authenticate session |
| `play` | `{ video_id }` → enqueue + play |
| `pause` / `resume` / `stop` | playback control |
| `next` / `prev` | skip track |
| `seek` | `{ position }` |
| `volume` | `{ value }` |
| `enqueue` | `{ video_id }` |
| `search` | `{ q }` |
| `discover` | → triggers discover_data response |
| `radio_toggle` | on/off |
| `radio_randomize` | `{ seed_artist? }` — seed_artist currently ignored by engine |
| `set_output` | `{ output: "browser"|"device" }` |
| `favorite` | `{ video_id }` |
| `download` | `{ video_id }` |

**Server → Client:** typed messages

| type | payload |
|---|---|
| `state` | full AppState dict via serializers.state_to_dict |
| `progress` | `{ position, status, server_ts }` |
| `search_results` | list of track dicts |
| `discover_data` | `{ recent, favorites, cached_tracks }` |
| `lyrics` | `{ lyrics_lines, lyrics_timestamps, lyrics_index, lyrics_offset, lyrics_loading }` |
| `auth_status` | `{ success, token?, message? }` |
| `favorite_status` | `{ video_id, is_favorite }` |
| `log` | string message |
| `error` | string message |

### State Management

**Backend:** `AppState` dataclass in `core/state.py`. Single instance per room. Mutated by engine layer only.
**Frontend:** `store` plain object in `store.js`. Mutated by `handleServerMessage()` in `ws.js`. No reactivity — manual `renderFullState()` or targeted render calls after mutation.

**Key store fields:**
```
status: "IDLE"|"LOADING"|"PLAYING"|"PAUSED"|"ERROR"
playback_mode: "QUEUE"|"RADIO"
audio_output: "browser"|"device"
userRole: "portal"|"client"|"admin"
current_track: TrackInfo | null
position: float
volume: int
queue: TrackInfo[]
radio_queue: TrackInfo[]
discover_recent / discover_favorites / discover_cached: TrackInfo[]
active_tab: "home"|"search"|"radio"|"discover"
```

---

## Runtime Flow

### Startup (Backend)
1. `main.py` → reads config, initializes SQLite, creates `RoomManager`
2. Instantiates `YtdlpClient`, `MpvController`, `PlaybackController`, `RadioEngine`
3. Registers event bus subscribers (TrackStartedEvent → `_on_track_started` in `app.py`)
4. Creates aiohttp app via `server/app.py::create_app()`
5. Binds routes; starts aiohttp runner

### Auth Flow (Frontend)
1. Page load → `init()` → `initPortal()` → shows portal screen
2. Admin submits credentials → `wsSend("auth", {token})` (token from localStorage if existing)
3. Server responds `auth_status` → `applyRoleUI()` → hides portal, shows app
4. Role stored in `localStorage("ytgui_user_role")` and `store.userRole`

### Playback Flow
1. User action → `wsSend("play"|"enqueue", {video_id})` → `command_router.py`
2. `playback_controller.py` resolves via `cache/resolver.py` (local → stream_url cache → yt-dlp)
3. `mpv_controller.py` starts playback
4. Progress events → `TrackProgressEvent` → `app.py._on_progress()` → WS broadcast `progress` msg
5. Frontend `handleServerMessage("progress")` → `renderProgress()` + `renderPlayBtn()`

### Radio Flow
1. Toggle → `wsSend("radio_toggle")` → engine sets `playback_mode = RADIO`
2. `radio_engine._gather_batch()` → `db.get_random_songs()` → fills `radio_queue`
3. Auto-next via `TrackEndedEvent` → engine pulls next from `radio_queue`
4. When queue low → engine prefetches next batch

### Render Flow
`handleServerMessage("state")` → `Object.assign(store, msg.data)` → `renderFullState()`:
- `renderHeader()`, `renderNowPlaying()`, `renderProgress()`, `renderPlayerBar()`, `renderRadio()`, `renderQueue()`, `renderLyrics()`, `renderSettingsSheet()`

---

## Module Ownership

### Frontend Modules

| Module | Purpose | Dependencies | Public API | Failure Mode |
|---|---|---|---|---|
| `config.js` | Constants | none | `TABS` | — |
| `store.js` | Mutable global state | none | `store` object | Stale state if WS drops |
| `dom.js` | DOM references | store | `dom` object, `initDOM()` | Null refs if IDs missing |
| `utils.js` | Pure helpers | none | `formatTime`, `cleanTrackTitle` | localStorage crash in Safari Private |
| `audio.js` | Browser audio + fake-beat | store, dom | `getOrInitAudio()`, `syncBrowserAudio()`, `_resumeAndPlay()` | rAF leak if not cancelled |
| `portal.js` | Auth UI | store, dom, ws | `initPortal()`, `applyRoleUI()`, `logout()` | — |
| `ws.js` | WS lifecycle + message dispatch | store, dom, all render/* | `wsConnect()`, `wsSend()`, `renderFullState()` | Reconnect loop on disconnect |
| `events.js` | All DOM event listeners | store, dom, ws, render/* | `initEvents()` | — |
| `main.js` | Entry point + switchTab + swipe | store, dom, ws, events | `switchTab()` | swipe false-positive on vertical scroll |
| `render/player.js` | Player bar rendering | store, dom | `renderPlayerBar()`, `renderPlayBtn()`, `renderProgress()` | — |
| `render/tabs.js` | Multi-tab rendering | store, dom, utils | `renderNowPlaying()`, `renderQueue()`, `renderRadio()`, `renderDiscoverTab()`, `renderRecentRow()` | — |
| `render/lyrics.js` | Lyrics rendering | store, dom | `renderLyrics()` | — |
| `render/search.js` | Search results rendering | store, dom | `renderSearchResults()`, `updateSearchPlayingState()`, `updateDiscoverPlayingState()` | — |

### Backend Modules

| Module | Purpose | Imports | Forbidden Imports |
|---|---|---|---|
| `core/*` | Domain logic | stdlib only | server/, engine/, cache/ |
| `engine/*` | Business logic | core/ | server/ |
| `cache/*` | Persistence | core/ | server/, engine/ |
| `server/*` | HTTP/WS layer | core/, engine/, cache/, services/ | Must not contain business logic |
| `services/*` | Cross-layer orchestration | core/, cache/ | — |
| `plugins/*` | Optional features | core/ | — |

---

# Module Contract Template

Every core module should follow this contract.

---

Module

Purpose

Responsibilities

Inputs

Outputs

Dependencies

Public Interfaces

Internal Interfaces

Owned State

External State Access

Failure Modes

Fallback Strategy

Side Effects

Performance Considerations

Security Considerations

Verification Procedure

Regression Coverage

Must Preserve

Must Not Change

Owner

Status

Confidence

## Folder Responsibilities

| Folder | Allowed | Forbidden |
|---|---|---|
| `core/` | Domain types, events, ports, state, security | DB access, HTTP, subprocess |
| `engine/` | Playback state machine, mpv, yt-dlp, radio batch | HTTP routes, WS broadcast |
| `cache/` | SQLite read/write, URL caching, schema | HTTP, playback decisions |
| `server/` | Route setup, WS handling, auth middleware, serialization | Business logic, direct DB |
| `services/` | Cross-layer orchestration | Must not import server/ |
| `web/static/css/` | Visual styles only | No logic |
| `web/static/js/render/` | DOM mutation based on store | Event listeners, WS calls |
| `web/static/js/` (root) | Event binding, WS, state, init | Direct DOM styling (use classes) |

---

## Feature Inventory

| Feature | Status | Owner Module | Risk | Notes |
|---|---|---|---|---|
| Auth (admin/client/portal) | VERIFIED WORKING | portal.js, server/handlers/auth.py | low | localStorage token persistence |
| Playback (QUEUE mode) | VERIFIED WORKING | playback_controller.py, render/player.js | low | — |
| Radio mode | PARTIALLY WORKING | radio_engine.py | medium | `seed_artist` param accepted but ignored |
| Search | VERIFIED WORKING | ws.js, render/search.js | low | — |
| Lyrics sync | VERIFIED WORKING | plugins/lyrics.py, render/lyrics.js | low | — |
| Queue drag-reorder | VERIFIED WORKING | events.js | low | — |
| Download | VERIFIED WORKING | download_manager.py | low | — |
| SponsorBlock | VERIFIED WORKING | plugins/sponsorblock.py | low | — |
| Discover tab | PARTIALLY WORKING | discover_service.py, render/tabs.js | high | mood cards no listeners; "See all" links dead; no skeleton loading; cold-start empty state |
| Browser audio output | VERIFIED WORKING | audio.js | medium | Fake-beat rAF loop leaks when PAUSED |
| Cover art / ambient | VERIFIED WORKING | render/tabs.js | low | localStorage no TTL; Safari Private crashes |
| Mini player (non-home tabs) | BUG | events.js | medium | No tap-to-home listener on pb-track-info |
| Radio LIVE badge | BUG | render/tabs.js | low | Always visible regardless of radio state |
| Artist randomize (Acak Artis) | NOT WORKING | radio_engine.py, db.py | high | UI exists but seed_artist never reaches DB query |
| Touch swipe nav | PARTIALLY WORKING | main.js | low | No vertical-scroll guard (false positive) |
| Safe-area (iOS notch) | BUG | main.js | low | `--sab` setProperty duplicate |
| Keyboard shortcuts | VERIFIED WORKING | events.js | low | No pointer:fine guard → fires on touch |

---

## Coding Standards

### Naming
- JS: `camelCase` functions/vars; `UPPER_SNAKE` constants; `dom.camelCase` for DOM refs
- Python: `snake_case` everywhere; `PascalCase` classes; `_underscore` private methods
- CSS: `kebab-case` classes; `--kebab-case` CSS variables; BEM-ish but not strict

### Architecture Rules
- Never mix render logic with event handlers
- Never put `@media` queries in `components/` CSS (after refactor)
- `core/` is a dependency-free domain layer — no imports from other layers
- One source of truth: `store` (frontend), `AppState` (backend)
- Never duplicate a WS message type; never rename existing ones

### State Management
- Frontend: mutate `store` only in `handleServerMessage()` or targeted event handlers
- Backend: mutate `AppState` only in `engine/` layer; never in `server/`
- Dirty-flag pattern exists for queue/radio renders in `ws.js` (`_lastQueueSnapshot`, `_lastRadioSnapshot`)

### Event Naming (WS — DO NOT RENAME)
`auth`, `play`, `pause`, `resume`, `stop`, `next`, `prev`, `seek`, `volume`, `enqueue`, `search`, `discover`, `radio_toggle`, `radio_randomize`, `set_output`, `favorite`, `download`

Response types: `state`, `progress`, `search_results`, `discover_data`, `lyrics`, `auth_status`, `favorite_status`, `log`, `error`

### CSS Rules
- All variables from `tokens.css` only — no hardcoded colors or pixel values outside tokens
- `!important` only in platform overrides; must include comment explaining why
- Mobile-first: components default to mobile; platform files override upward

### Error Handling
- Backend: wrap all async operations in try/except; log via structlog; emit `LogMessageEvent` for user-visible errors
- Frontend: `localStorage` access needs try/catch (`safeStorage()` helper — **not yet implemented**, tracked in SPRINT 0.7)
- WS: auto-reconnect via `wsReconnectTimer` (2s delay, no exponential backoff)

### Testing
- Backend: `pytest tests/` — unit + integration suite exists; **run before and after every backend change**
- Do NOT overwrite `tests/integration/test_fase0.py` or `test_fase1.py` (pre-existing, different scope)
- New SPRINT tests go in `tests/integration/test_sprint_<N>.py`
- Frontend: manual only (no automated test framework)

---

## AI Constraints

**NEVER:**
- Rename WS action or response type strings
- Rename `store` keys
- Change `core/state.py` field names without full audit of serializers and frontend
- Introduce a bundler or module system (no `import/export` in browser JS)
- Use `localStorage` without try/catch
- Add `@media` queries inside `components/*.css` files (after SPRINT 2)
- Overwrite `tests/integration/test_fase0.py` or `test_fase1.py`
- Start SPRINT N+1 before SPRINT N is verified stable

**ALWAYS:**
- Run `grep -n "<target>"` before editing any file (line numbers drift after edits)
- Run `pytest tests/` before AND after backend changes
- Verify both blocks are truly identical before deleting a duplicate
- One task = one commit
- Re-verify source code before trusting line numbers in any document

---

## Verification Protocol

### Before Coding
- [ ] `grep -n "<target>"` confirms exact line numbers
- [ ] Both blocks confirmed identical before deleting duplicates (use `diff` or side-by-side grep)
- [ ] `pytest tests/` passes (backend tasks only)
- [ ] Understand which render functions will be affected

### During Coding
- [ ] One task at a time
- [ ] No mixing of refactor + bug fix in same commit
- [ ] CSS `@media` stays in platform files, not component files

### After Coding
- [ ] `grep -c "<deleted_selector>"` confirms removal
- [ ] `pytest tests/` passes (backend tasks)
- [ ] Manual visual test at affected breakpoint
- [ ] `index.html` references updated if files moved

---

## Regression Matrix

| Area | Key Check | Expected |
|---|---|---|
| Playback | play/pause/next/prev | Immediate response; player bar updates |
| Queue | Add, remove, drag-reorder | Queue list re-renders; order persists |
| Radio | Toggle on/off | Badge shows only when ON; auto-next works |
| Search | Type query → results | Results appear; play from results works |
| Auth | Login/logout cycle | Role UI applied correctly |
| Discover | Tab switch | recent/favorites/cached render; no empty flash |
| Lyrics | Track with LRC | Lines sync to position |
| Settings | Sheet open/close | All toggles functional |
| WS | Disconnect + reconnect | State resumes within 2s |
| CSS | Desktop ≥1024px | Sidebar visible, vol-grp resolved (no contradiction) |
| CSS | Mobile <600px | All touch targets ≥44×44px |
| CSS | `prefers-reduced-motion` | All infinite animations stop |
| Safari iOS Private | Cover art | No crash; fallback image shown |

---

## Technical Debt

### Critical
| ID | Issue | File | Evidence |
|---|---|---|---|
| TD-C1 | `seed_artist` accepted, never applied | `engine/radio_engine.py:311`, `cache/db.py:199` | `get_random_songs()` has no artist param; comment at line 311 confirms |
| TD-C2 | CSS duplicat block 147–472 in base.css | `web/static/css/base.css` | VERIFIED via grep; `.btn-shuffle` appears 2× |
| TD-C3 | `.vol-grp` show/hide contradiction | `web/static/css/layout.css:134,355,430` | Three rules in two separate `@media (min-width:1024px)` blocks conflict |
| TD-C4 | `localStorage` without try/catch | `web/static/js/utils.js:48,68,76` | Crashes Safari Private Mode |
| TD-C5 | rAF loop never cancelled when PAUSED | `web/static/js/audio.js:~44-73` | `tick()` always reschedules regardless of status |

### High
| ID | Issue | File |
|---|---|---|
| TD-H1 | Google Fonts loaded 2× | `index.html:10-11` (preload) + `15-17` (blocking) |
| TD-H2 | `--sab` CSS var set twice identically | `main.js:54-55` |
| TD-H3 | Mini player has no tap-to-home listener | `events.js` (0 grep results for `pbTrackInfo` click) |
| TD-H4 | mood-card has no event listener | `events.js` (0 grep results for `mood-card`) |
| TD-H5 | `.disc-row2` has no CSS definition | All CSS files (0 grep results) |
| TD-H6 | Radio LIVE badge always visible | `index.html` + render logic |
| TD-H7 | `home-recent-item` class used for radio queue items | `render/tabs.js` (class collision) |

### Medium
| ID | Issue | File |
|---|---|---|
| TD-M1 | `events.js` 720 lines, mixed concerns | `web/static/js/events.js` |
| TD-M2 | `render/tabs.js` 455 lines, mixed concerns | `web/static/js/render/tabs.js` |
| TD-M3 | Swipe handler no vertical-scroll guard | `main.js` |
| TD-M4 | `localStorage` cover art no TTL | `utils.js` |
| TD-M5 | `_on_track_started` inline in app.py | `server/app.py` |
| TD-M6 | `@media (min-width:1024px)` 3× in layout.css | `web/static/css/layout.css:34,412,451` |

### Low
| ID | Issue |
|---|---|
| TD-L1 | `label-link` "Acak Artis" touch target ~24px (needs 44px) |
| TD-L2 | `home-fav-btn` 40px (needs 44px) |
| TD-L3 | `.sr-more-btn` 34px (needs 44px) |
| TD-L4 | Radio queue not reset scroll on randomize |
| TD-L5 | `rt-sub` text same for LOADING and PLAYING states |
| TD-L6 | "New Release" label is semantic lie (actually last-played) |
| TD-L7 | `home-header` empty but consumes 28px on mobile |
| TD-L8 | No skeleton loading in Discover (empty state flash) |
| TD-L9 | No artist distribution guarantee in radio batch |

---

## Known Limitations

- No multi-room support (room_manager exists but single "default" room used)
- No offline/PWA (service worker intentionally disabled during dev)
- `artists.json` / `artists_enriched.json` (2500+ records) not used in any live query
- No pagination or "load more" in Discover
- No progress bar in mini player (non-home tabs)
- `get_random_songs()` has no artist filter; `PARTITION BY artist_id` not implemented
- No `stream_url` pre-fetch for radio track transitions (only next-queue item prefetched)

---

## Glossary

| Term | Definition |
|---|---|
| `store` | Frontend global state object in `store.js` |
| `dom` | Frontend DOM reference object populated by `initDOM()` |
| `AppState` | Backend domain state dataclass in `core/state.py` |
| QUEUE mode | `playback_mode = QUEUE`; user-directed playback from `store.queue` |
| RADIO mode | `playback_mode = RADIO`; autonomous playback from `store.radio_queue` |
| mini player | `#player-bar` shown in non-home tabs as compact overlay |
| fake-beat | rAF animation loop in `audio.js` simulating equalizer beat |
| `safeStorage()` | Planned localStorage wrapper with try/catch (not yet implemented) |
| SPRINT | Execution phase in MASTER_PLAN; numbered 0–8 |
| `wsSend` | Client-side function to send command over WebSocket |
| `renderFullState()` | Triggers all render functions from current `store` state |
| `applyRoleUI()` | Shows/hides UI elements based on `store.userRole` |
| CacheResolver | `cache/resolver.py`; resolves track URL from local → cache → yt-dlp |
| seed_artist | Radio parameter for artist-weighted batch; accepted but not applied to query |
