# ARCHITECTURE_LOCK.md
> **Architectural Principles & Constraints**  
> Dokumen ini mendefinisikan **MENGAPA** struktur seperti ini, bukan **BAGAIMANA** implementasinya.  
> Untuk **BAGAIMANA**, lihat `REFACTOR_PLAN_FINAL.md`.

---

## Daftar Isi
1. [Design Principles](#1-design-principles)
2. [Backend Architecture](#2-backend-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Data Flow Rules](#4-data-flow-rules)
5. [Integration Points](#5-integration-points)
6. [Decisions & Rationale](#6-decisions--rationale)

---

## 1. Design Principles

### 1.1 Separation of Concerns
- **Backend**: Engine (playback logic) ≠ Server (HTTP/WebSocket) ≠ Core (shared utilities)
- **Frontend**: Render (DOM updates) ≠ Events (user interaction) ≠ Store (state) ≠ WS (network)
- **Rationale**: Easier to test, modify, reuse. No tangled dependencies.

### 1.2 Unidirectional Data Flow
- **Backend**: Commands DOWN (main → engine), Events UP (engine → server → client)
- **Frontend**: WS ← Store ← Render ← (Events → WS → Server)
- **Rationale**: Predictable behavior, easier to debug state mutations.

### 1.3 Single Responsibility per Module
- `config.py` — **ONLY** environment & security setup, not business logic
- `main.py` — **ONLY** wiring & startup, not orchestration
- `engine/*` — **ONLY** playback domain, not network or persistence details
- `core/*` — **ONLY** shared infrastructure (bus, state, ports), no domain-specific logic

### 1.4 Explicit Contracts via Ports
- `core/ports.py` defines interfaces that **engine** depends on
- **plugins/** implements those interfaces, NOT accessed directly by **engine**
- This allows plugin swapping without code changes

### 1.5 Frontend is Stateless Renderer
- All state lives in `store.js`
- Render functions are **pure**: `store → DOM` with no side effects
- Events are **pure**: collect data, dispatch to `wsSend()` via events.js
- Result: UI can be tested by mocking store

---

## 2. Backend Architecture

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────┐
│          main.py (wiring only)          │ ← Entry point
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│    server/ (HTTP + WebSocket layer)     │ ← Handles client communication
│  - app.py (create_app, routes)          │
│  - handlers/ (http, ws, auth)           │
│  - serializers (track↔dict conversion)  │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│       engine/ (Playback domain)         │ ← Business logic
│  - command_router (commands)            │
│  - playback_controller (main logic)     │
│  - queue_manager (queue state)          │
│  - radio_engine (radio logic)           │
│  - mpv_controller (playback device)     │
│  - download_manager (yt-dlp)            │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│   core/ (Shared infrastructure)         │ ← Cross-cutting concerns
│  - command_bus (async command dispatch) │
│  - event_bus (pub/sub for events)       │
│  - room_manager (multi-user state)      │
│  - ports.py (interface contracts)       │
│  - state.py (data models)               │
│  - security.py (auth/SSRF guards)       │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│    cache/ (Persistence layer)           │ ← Data storage
│  - db.py (SQLite operations)            │
│  - resolver.py (file resolution)        │
└──────────────────┬──────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│    plugins/ (External integrations)     │ ← Third-party adapters
│  - lyrics.py (Genius/Musixmatch API)    │
│  - sponsorblock.py (sponsorblock API)   │
│  - notifications.py (Termux notify)     │
└─────────────────────────────────────────┘
```

### 2.2 Import Rules (Hard Constraints)

```
core    ← GOLDEN LAYER — cannot import from any other layer
           (core is library-like, standalone)

engine  ← can import from: core, plugins (via port only)
           CANNOT import from: server

server  ← can import from: core, engine
           CANNOT import from: plugins directly

plugins ← can import from: core only
           CANNOT import from: engine, server

main    ← wiring layer, can import from all
           BUT contains no business logic
```

**Violation Examples (DO NOT DO THESE):**

```python
# ❌ BAD: core importing engine
# core/state.py
from engine.playback_controller import PlaybackController

# ❌ BAD: engine importing server
# engine/queue_manager.py
from server.handlers.websocket import wsManager

# ❌ BAD: engine importing plugin directly
# engine/playback_controller.py
from integrations.lyrics import LyricsFetcher  # ← WRONG

# ✅ GOOD: engine using port to access plugin
# engine/playback_controller.py
from core.ports import LyricsProvider  # interface
# Implementation injected at startup in main.py
```

### 2.3 Command/Event Pattern

**Commands** (Request → Engine):
```
User Action → server/handlers → command_bus.dispatch(cmd) → engine processes
```

Example:
```python
# server/handlers/websocket.py
command = PlayCommand(track_id="abc123")
await command_bus.dispatch(command)

# engine/playback_controller.py
@command_bus.handle(PlayCommand)
async def on_play(cmd: PlayCommand):
    await self.mpv.play(cmd.track_id)
    self.state.now_playing = ...
    await event_bus.publish(PlaybackStarted(...))
```

**Events** (Engine → Clients):
```
engine publishes → event_bus → server subscribes → websocket broadcast → clients
```

Example:
```python
# engine/playback_controller.py
await event_bus.publish(PlaybackStarted(track_id="abc123", duration_ms=240000))

# server/handlers/websocket.py
@event_bus.on(PlaybackStarted)
async def on_playback_started(evt):
    msg = {"type": "playback_started", "data": evt.to_dict()}
    await wsManager.broadcast(msg)
```

### 2.4 Database Schema

**Constraint:** Only `cache/schema.sql` defines DB structure. Changes need migration.

```sql
-- Immutable structure
CREATE TABLE tracks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  artist TEXT NOT NULL,
  duration_ms INTEGER,
  cached_at TIMESTAMP,
  ttl_seconds INTEGER
);
```

**Access:** Only `cache/db.py` talks to database. Other modules call methods.

```python
# ✅ OK: engine using cache API
tracks = await cache.get_recent(n=10)

# ❌ NOT OK: engine doing raw SQL
cursor.execute("SELECT * FROM tracks")  # Never do this
```

---

## 3. Frontend Architecture

### 3.1 Module Structure

```
web/static/
├── css/
│   ├── tokens.css      ← Design tokens (:root vars)
│   ├── base.css        ← Reset, typography, global
│   ├── layout.css      ← Container, flexbox, grid
│   ├── player.css      ← Player bar, controls
│   ├── tabs.css        ← Tab navigation + content
│   ├── components.css  ← Reusable widgets
│   └── portal.css      ← Admin login modal
│
└── js/
    ├── config.js       ← Constants, seed artists, tab IDs
    ├── store.js        ← Immutable state object + updateStore()
    ├── dom.js          ← Cached DOM references (getElementById results)
    ├── ws.js           ← WebSocket connection + send/receive
    ├── utils.js        ← Helper functions (formatTime, escapeHtml, etc)
    ├── events.js       ← ALL addEventListener() calls + event handlers
    ├── main.js         ← Init sequence + startup
    │
    ├── render/
    │   ├── player.js   ← renderPlayerBar(), renderProgress(), etc
    │   ├── tabs.js     ← renderNowPlaying(), renderQueue(), etc
    │   ├── lyrics.js   ← renderLyrics(), updateOffsetDisplay()
    │   └── search.js   ← renderSearchResults(), showActionModal()
    │
    ├── eq.js           ← tickEQ(), EQ canvas visualization
    ├── audio.js        ← Browser audio, unlockBrowserAudio()
    └── portal.js       ← Admin portal, login session
```

### 3.2 Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  WebSocket Message (from server)                            │
│         ↓                                                    │
│  ws.js: handleServerMessage()                               │
│         ↓                                                    │
│  Update store.js via updateStore(msg)                       │
│         ↓                                                    │
│  Render functions called (render/*.js)                      │
│         ↓                                                    │
│  DOM updated with new content                               │
│         ↓                                                    │
│  User sees updated UI                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  User clicks button                                          │
│         ↓                                                    │
│  events.js: addEventListener callback fires                 │
│         ↓                                                    │
│  Collect data from store (read-only)                        │
│         ↓                                                    │
│  Call wsSend(command_name, data) from ws.js                 │
│         ↓                                                    │
│  Server receives, processes, publishes event                │
│         ↓                                                    │
│  Loop back to top (WS message received)                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 JavaScript Module Rules

**Rule 1: Render functions are PURE**
```javascript
// ✅ OK: Read store, return HTML
function renderPlayerBar() {
  const { isPlaying, track } = store;
  return `<div class="pb"><span>${track.title}</span></div>`;
}

// ❌ NOT OK: Render function with side effects
function renderPlayerBar() {
  wsSend("get_state");  // WRONG — side effect
  localStorage.setItem("state", JSON.stringify(store));  // WRONG
  const bar = document.getElementById("pb");  // WRONG — use dom.js
  return "<div>...";
}
```

**Rule 2: ALL addEventListener in events.js**
```javascript
// events.js (ONLY file with addEventListener)
dom.playBtn.addEventListener("click", () => {
  if (store.isPlaying) {
    wsSend("pause");
  } else {
    wsSend("play");
  }
});

// ✅ OK: render/tabs.js is pure
function renderSearchResults(tracks) {
  return tracks.map(t => `<div class="track">${t.title}</div>`).join("");
}

// ❌ NOT OK: addEventListener in render file
// render/tabs.js — NEVER DO THIS
dom.searchInput.addEventListener("input", (e) => {
  wsSend("search", e.target.value);
});
```

**Rule 3: DOM Cache in dom.js**
```javascript
// dom.js
const dom = {
  app: document.getElementById("app"),
  playBtn: document.getElementById("pb-play"),
  seekBar: document.getElementById("pb-seek"),
  // ... all element refs cached here
};

// ✅ OK: Everywhere uses dom.js cache
function renderPlayerBar() {
  dom.playBtn.classList.toggle("playing", store.isPlaying);
}

// ❌ NOT OK: Direct getElementById in render functions
function renderPlayerBar() {
  document.getElementById("pb-play").classList.toggle(...);  // WRONG
}
```

**Rule 4: wsSend ONLY from events.js**
```javascript
// events.js
dom.playBtn.addEventListener("click", () => {
  wsSend("toggle_play");  // ✅ OK here
});

// render/player.js
function renderPlayerBar() {
  // ❌ NOT OK here
  wsSend("toggle_play");  // WRONG — render has no side effects
  return "...";
}
```

### 3.4 CSS Design Token System

**Single source of truth: `:root {}`**

```css
:root {
  --fm-accent: #e040fb;
  --fm-text-1: #f0f0ff;
  --fm-bg-deep: #0d0d1c;
  /* ... all token defs ... */
}
```

**Rule:** No hex color (#xxx) outside of `:root`
```css
/* ✅ OK: Using token */
.btn { color: var(--fm-accent); }

/* ❌ NOT OK: Hardcoded color */
.btn { color: #e040fb; }  /* WRONG — breaks design system */
```

**Migration path (for existing code):**
1. Define `--fm-*` token in `:root`
2. Use `var(--fm-*)` everywhere
3. Later: refactor old code that has hardcoded colors

---

## 4. Data Flow Rules

### 4.1 Backend: Command Down, Event Up

```
        main.py
          ↓
    command_bus.dispatch(cmd)
          ↓
    server/handlers/websocket.py (receives command)
          ↓
    engine/command_router.py (routes to handler)
          ↓
    engine/playback_controller.py (executes)
          ↓
    event_bus.publish(event)
          ↓
    server/handlers/websocket.py (subscribes)
          ↓
    broadcast to all connected clients
```

**Example: Play command**
```python
# Client sends
{ "cmd": "play", "track_id": "abc123" }

# server/handlers/websocket.py receives
cmd = PlayCommand(track_id=msg["track_id"])
await command_bus.dispatch(cmd)

# engine/playback_controller.py handles
@command_bus.handle(PlayCommand)
async def on_play(cmd):
    await self.mpv.play(cmd.track_id)
    await event_bus.publish(PlaybackStarted(track_id=cmd.track_id))

# server/handlers/websocket.py broadcasts
@event_bus.on(PlaybackStarted)
async def on_started(evt):
    await broadcast_to_clients(evt)

# Client receives
{ "evt": "playback_started", "track_id": "abc123" }
```

### 4.2 Frontend: Store → Render → DOM

**Immutable store**
```javascript
const store = {
  isPlaying: false,
  currentTrack: null,
  queue: [],
  // ... all state here
};

// Only updateStore() modifies it
function updateStore(serverMsg) {
  store.isPlaying = serverMsg.is_playing;
  store.currentTrack = serverMsg.track;
  // ...
}
```

**Render reads store, updates DOM**
```javascript
function renderPlayerBar() {
  const { isPlaying, currentTrack } = store;
  let html = `<div class="pb">`;
  html += `<button class="pb-play ${isPlaying ? 'playing' : ''}">${isPlaying ? '⏸' : '▶'}</button>`;
  html += `<span>${currentTrack?.title || 'Nothing playing'}</span>`;
  html += `</div>`;
  return html;
}

// Called by: ws.js after updateStore()
function render() {
  dom.playerBar.innerHTML = renderPlayerBar();
  dom.queue.innerHTML = renderQueue();
  dom.lyrics.innerHTML = renderLyrics();
}
```

### 4.3 Event → Command Flow

**User clicks play button**
```javascript
// events.js
dom.playBtn.addEventListener("click", () => {
  const trackId = store.currentTrack?.id;
  if (trackId) {
    wsSend("play", { track_id: trackId });
  }
});
```

**Server receives, dispatches command**
```python
# server/handlers/websocket.py
if msg["cmd"] == "play":
    cmd = PlayCommand(track_id=msg["data"]["track_id"])
    await command_bus.dispatch(cmd)
```

**Engine processes, publishes event**
```python
# engine/playback_controller.py
@command_bus.handle(PlayCommand)
async def on_play(cmd):
    result = await self.mpv.play(cmd.track_id)
    await event_bus.publish(PlaybackStarted(track_id=cmd.track_id))
```

---

## 5. Integration Points

### 5.1 Plugin Interface

**Core defines interface, plugins implement:**

```python
# core/ports.py (contract)
class LyricsProvider(Protocol):
    async def fetch(self, title: str, artist: str) -> str:
        """Fetch lyrics for track"""
        ...

class NotificationService(Protocol):
    async def notify(self, title: str, body: str):
        """Send notification to user"""
        ...
```

**Plugin implements interface:**
```python
# plugins/lyrics.py
class GeniusLyricsProvider:
    async def fetch(self, title: str, artist: str) -> str:
        # Genius API call
        ...

# plugins/notifications.py
class TermuxNotificationService:
    async def notify(self, title: str, body: str):
        # Termux notification
        ...
```

**Engine uses via port (not direct import):**
```python
# engine/playback_controller.py
def __init__(self, lyrics_provider: LyricsProvider):
    self.lyrics = lyrics_provider  # Injected

async def get_lyrics(self, track: TrackInfo):
    return await self.lyrics.fetch(track.title, track.artist)
```

**Main.py wires it up:**
```python
# main.py
from plugins.lyrics import GeniusLyricsProvider
from plugins.notifications import TermuxNotificationService
from engine.playback_controller import PlaybackController

lyrics_provider = GeniusLyricsProvider()
notifier = TermuxNotificationService()
playback = PlaybackController(lyrics_provider=lyrics_provider)
```

### 5.2 Multi-Room Architecture

**Each room has isolated state:**

```python
# core/room_manager.py
class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}

    def create_room(self, room_id: str):
        self.rooms[room_id] = Room(
            state=AppState(),
            event_bus=EventBus(),
            command_bus=CommandBus()
        )
```

**WebSocket handler routes to correct room:**
```python
# server/handlers/websocket.py
@app.websocket("/ws/{room_id}")
async def ws_handler(request, room_id: str):
    room = room_manager.get_room(room_id)
    async with WebSocketConnection(room) as conn:
        async for msg in conn:
            cmd = parse_command(msg)
            await room.command_bus.dispatch(cmd)
```

**Result:** No shared state between rooms, no race conditions.

---

## 6. Decisions & Rationale

### Decision: Layered Architecture

**Why not monolithic?**
- Single god file = hard to test, easy to break
- Parallel development conflicts

**Why not "clean architecture" (too strict)?**
- Interfaces are overhead for small codebase (< 10k LOC)
- Sweet spot: layering + ports for plugins only

### Decision: Command/Event Pattern

**Why not direct service calls?**
- Testable: mock command/event bus instead of entire service
- Async-friendly: commands are queued, processed serially
- Auditability: all state changes logged via events

### Decision: Unidirectional Frontend Data Flow

**Why not bidirectional binding (Vue/React)?**
- No framework = explicit control
- Debugging: trace exact line where state changes
- Reusable across platforms (terminal, mobile, web)

### Decision: Design Tokens in CSS

**Why not hardcoded colors?**
- Single source of truth
- Easy rebrand: change `:root` vars, done
- Accessible: consistent contrast ratios

### Decision: No Framework on Frontend

**Why not jQuery/Vue/React?**
- Termux bandwidth constraint: vanilla JS is ~0KB, React is ~40KB
- Full control: understand every line
- No dependency vulnerability surprises

---

## Appendix: Architecture Review Checklist

**For every PR, review:**

- [ ] Import direction: `core ← engine ← server ← main`?
- [ ] Command/event pattern used (not direct calls)?
- [ ] Main.py < 100 lines?
- [ ] No hex color outside `:root`?
- [ ] No addEventListener outside `events.js`?
- [ ] Render functions pure (no wsSend)?
- [ ] Test added for new functionality?
- [ ] Database changes have migration?
- [ ] Commit message follows conventional format?

