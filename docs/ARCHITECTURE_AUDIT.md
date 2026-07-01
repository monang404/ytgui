# ARCHITECTURE AUDIT — bagas.fm / YTGUI

## 1. Folder / Module Map (as found)

```
config.py                  # env-driven config, secret bootstrapping
main.py                    # process entrypoint (asyncio orchestration)
start.py / start.sh / .bat # Tkinter launcher GUI + cross-platform bootstrap script
core/                       # domain primitives: state, events, command/event bus, security, ports
engine/                     # playback domain: mpv IPC, yt-dlp client, radio, queue, download, volume
  engine/playback/          # PlaybackController (orchestrates engine + core.state)
server/                     # aiohttp web layer: app wiring, http/ws handlers, middleware, serializers
  server/handlers/          # http.py, websocket.py, auth.py, event_listeners.py
  server/services/          # stream_prefetch, broadcast_service
services/                   # discover_service.py (cross-cutting query service over db)
cache/                      # SQLite access layer (db.py) + schema.sql + runtime cache dir (mp3, sockets)
data/                       # one-off/offline data-prep scripts (enrich, export, verify) + seed json/db
plugins/                    # optional integrations: lyrics (lrclib/syncedlyrics), sponsorblock, termux notifications
web/static/                 # vanilla JS/CSS/HTML frontend, no build step
tests/                      # unit + integration, pytest
docs/                       # 4 pre-existing audit documents (QA/design/strength reports)
scratch/, scripts/          # dev-only helper scripts (should not ship)
```

This is a reasonable, conventional layered layout for a project of this size. `core/ports.py` defines real `typing.Protocol` interfaces (`AudioPlayerPort`, `MediaExtractorPort`, `DatabasePort`, `LyricsProvider`, `SponsorBlockProvider`) and `engine`/`cache`/`plugins` provide concrete implementations of them — this is a genuine, if partial, application of the Ports & Adapters (hexagonal) pattern the README claims, not just a buzzword. `core/command_bus.py` and `core/event_bus.py` implement a CQRS-flavored single-writer command bus + pub/sub event bus, which is an appropriate pattern for a stateful realtime player.

## 2. The Central Architectural Problem: Two Competing Designs in One Codebase

There is clear, testable evidence (see `TECH_DEBT_REPORT.md` TD-01 and the pytest run referenced throughout this audit) that the project underwent a **"Fase 3" architecture migration** intended to move from:

- **Global singletons** (`command_bus = CommandBus()` at module scope in `core/command_bus.py`; `bus` global singleton imported as fallback in `core/event_bus.py`, `plugins/lyrics.py:29`, `engine/mpv_controller.py:40`)

to:

- **Per-room instances** (a `RoomManager` owning independent `EventBus` instances per room, `MpvController`/`LyricsFetcher` receiving their bus via dependency injection, `server/app.py::create_app` taking a `room_manager` instead of a single `playback_controller`, and `/ws?room=<id>` routing).

The dependency-injection *half* of this migration was completed — `MpvController.__init__` and `LyricsFetcher.__init__` both accept an `event_bus` parameter and only fall back to the global singleton `if event_bus is None` (see `engine/mpv_controller.py:38-42`, `plugins/lyrics.py:27-31`). But the *composition root* was never finished: `server/app.py::create_app(playback_controller, ytdlp, db)` still constructs exactly one `PlaybackController` and one `ConnectionManager` for the entire process, and `core/command_bus.py`'s `command_bus` singleton is still imported directly by handler modules (`server/handlers/websocket.py:8`) rather than being resolved per-room.

**Net effect:** the DI plumbing for multi-room exists, but nothing in the runtime path ever actually creates more than one room. `RoomManager` does not exist anywhere in the `core/`, `engine/`, or `server/` trees — it only exists as a name inside test files (`tests/unit/core/test_room_manager.py`, `tests/integration/test_fase1.py`). Running those tests fails immediately (see `TECH_DEBT_REPORT.md`), which is the most reliable way to confirm this isn't a subtle abstraction the audit missed — the project's own test authors expected this class to exist and it doesn't.

**Architectural recommendation:** treat this as a fork-in-the-road decision, not a bug to patch around. Multi-room is a substantial feature (per-room mpv process, per-room queue/radio state, per-room auth) — either commit to finishing it with a real `Room`/`RoomManager` composition root, or roll the scope back to the single-instance design that is actually running today and stop advertising multi-room support until it exists.

## 3. Coupling & Cohesion

- **`core/command_bus.py` and `core/event_bus.py`**: good cohesion, minimal coupling — they know nothing about mpv, yt-dlp, or aiohttp. This is the strongest part of the architecture.
- **`server/handlers/websocket.py`**: acts as the composition point for almost every feature (search, discover, favorites, queue, radio, downloads) in a single 345-line file with one giant `if/elif` dispatcher (`handle_ws_message`). This is a **God Function** by count of responsibilities (18 distinct `action` branches) even though each branch itself is short. See `CODE_QUALITY_REPORT.md` CQ-01.
- **`engine/radio_engine.py`** explicitly documents its own boundary in its module docstring ("Radio must NEVER depend on Queue Empty events") — this is a good example of intentional decoupling being written down, not just implied.
- **`services/discover_service.py`** and **`cache/db.py`** overlap significantly: `DiscoverService` re-implements query composition patterns already present in `Database` rather than delegating to it consistently (both files independently touch `self.db._conn.execute(...)` for `DiscoverService`, reaching *through* the `Database` object into its private `_conn` attribute rather than through a public method — see `services/discover_service.py:22,49,76,103,119`). This is a **Law of Demeter violation**: `DiscoverService` depends on `Database`'s internal implementation detail (`_conn`), so any change to how `Database` manages its connection (e.g., connection pooling) will silently break `DiscoverService` without a type-checker or interface catching it.

## 4. Dependency Graph Observations

- No circular imports were found between `core/`, `engine/`, `server/`, `cache/`, `plugins/`. The dependency direction is consistently `server → engine → core` and `engine/plugins → cache/core`, which is correct layering.
- `config.py` is imported directly (not injected) by `cache/db.py`, `engine/ytdlp_client.py`, `engine/mpv_controller.py`, `server/handlers/http.py`, `server/handlers/auth.py`, and others — this is a common and acceptable pattern for a small app, but it does mean `config.py`'s module-level side effects (password generation/printing, socket-path `mkdir`) run as an implicit part of import order, which makes the app harder to unit-test in isolation (confirmed by the amount of `unittest.mock.patch` scaffolding required in the test suite to work around this).
- `core.command_bus`'s module-level singleton (instantiated at import time) means **any test that imports `websocket.py` transitively imports and mutates a shared `CommandBus` instance** unless carefully reset between tests — this is very likely a contributing cause to some of the test failures observed (handlers registered once leaking across test cases via `CommandBus.register()`'s "already registered" `RuntimeError` guard at `core/command_bus.py:20-21`).

## 5. SOLID / Clean Architecture Compliance

| Principle | Assessment |
|---|---|
| **Single Responsibility** | Mostly good at the class level (`MpvController` only does mpv IPC, `YtDlpClient` only does extraction). Violated at the file level in `server/handlers/websocket.py` (dispatcher owns 18 unrelated feature branches) and `start.py` (832 lines mixing Tkinter UI, process supervision, port-killing OS calls, and dependency checking in one file/class). |
| **Open/Closed** | `CommandBus.register()` raising on duplicate registration is a good OCP-supporting guard, but the `websocket.py` `if/elif` chain must be edited (not extended) for every new action — a command-registry-driven dispatch (mapping `action → handler` similarly to how `command_bus` already maps `command → handler`) would fix this and remove ~150 lines of branching. |
| **Liskov Substitution** | The `Protocol`-based ports (`core/ports.py`) are honored by their implementations as far as this audit could verify by signature comparison. |
| **Interface Segregation** | Good — `TrackRepositoryPort` and `SessionRepositoryPort` are separated and composed into `DatabasePort`, rather than one fat interface. |
| **Dependency Inversion** | Partially achieved (ports exist, some DI happens) but undermined by the global singletons (`command_bus`, `bus`) that make the "inversion" optional rather than enforced — code can always reach for the global instead of the injected one, and several modules do. |

## 6. Scalability

For its actual target deployment (one process, one admin, a handful of LAN listeners) the architecture is appropriately sized — there is no over-engineering for horizontal scale (no unnecessary message queue, no premature microservices). The main scalability question is **not** "does this scale to many servers" but **"does the multi-room claim hold up for even a modest number of concurrent independent rooms on one machine"**, and per section 2 above, the answer today is no — it is single-room only.

## 7. Frontend Architecture

`web/static/js` is organized by concern (`render/`, `events/`, `services/`, `platform/`) with a single global `store` object (`store.js`) as the source of truth and a thin `ws.js` bridging server pushes into store mutations — a reasonable, framework-free MVU-ish pattern for a project this size. No build step, no bundler, no `package.json` — all JS is hand-written ES2017+ and loaded via plain `<script>` tags (confirmed via `web/static/index.html` and absence of any `package.json`/`webpack`/`vite` config anywhere in the tree). This is a legitimate choice for a small self-hosted app and keeps the deployment footprint small, at the cost of no minification/bundling/tree-shaking and no compile-time type checking of the ~25 JS files.
