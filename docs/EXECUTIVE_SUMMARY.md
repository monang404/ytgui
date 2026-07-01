# EXECUTIVE SUMMARY — bagas.fm / YTGUI (YT Termux Player Pro V2)

**Audit date:** 2026-07-01
**Scope:** Full repository as uploaded (`sourcecode.zip`), 221 files, ~8,100 lines of Python (excluding tests/cache), vanilla JS/CSS frontend (~40 files), SQLite storage, aiohttp/websocket server, mpv-based playback engine, yt-dlp integration.
**Method:** Static reading of every non-generated source file, targeted `grep`/pattern scans for security-sensitive constructs, and **actual execution of the bundled test suite** (`pytest`) to separate real defects from cosmetic ones. All findings below are backed by a concrete file path and, where applicable, a command/output.

---

## Overall Scores

| Dimension | Score (1–10) | Notes |
|---|---|---|
| **Code quality** | 6.5 | Individual modules are clean and well-commented; the problem is inconsistency and orphaned code left over from an abandoned refactor. |
| **Security** | 7 | Core attack surface (SQL, stream proxy, auth) is well defended and shows evidence of prior hardening passes. Undermined by secrets/PII shipped inside the audited bundle itself. |
| **Maintainability** | 5.5 | Good separation into `core/engine/server/plugins`, but a large fraction of the test suite no longer matches the implementation, which will actively mislead future contributors. |
| **Production readiness** | 5 | Runs and is functionally sound for its actual use case (single-room, LAN-hosted personal music server), but is **not** production/multi-tenant ready despite documentation implying it is. |
| **Overall** | **6/10** | A capable hobby/personal-server project with real security engineering in it, let down by unfinished architecture work and repo hygiene. |

---

## What This Project Actually Is

This is **not** a generic web app — it's a self-hosted, single-admin YouTube music player/radio (`bagas.fm`) meant to run on a phone (Termux) or PC and be accessed over a LAN by one admin and passive "listen-only" clients. That context matters: several things that would be critical flaws in a multi-tenant SaaS product (single shared `command_bus`/`event_bus`, no per-user data isolation, `0.0.0.0` bind default) are reasonable-to-acceptable design choices *for this use case*, but they directly contradict the "Enterprise Architecture" and "Multi-room" claims in `README.md`. This mismatch between marketing language and actual implementation is the single biggest theme of this audit and is treated as its own top risk below.

## Evidence the Codebase Has Already Been Audited Before

The code is dense with inline markers (`CRITICAL-04 fix`, `TASK-3.3`, `PATCH-YTDLP-RESOLVE-TIMEOUT-01`, `HIGH-03 fix`, `MED-10 fix`, etc.) — **54 distinct patch/task IDs found across 31 files**. Combined with four pre-existing audit documents already in `docs/` (`Bug_Report.md`, `Design_System_Audit.md`, `Music_Player_Audit.md`, `Strength_Report.md`), this indicates several previous audit-and-fix cycles. This audit corroborates several of those prior findings still being open (see `docs/Bug_Report.md` BUG-01/02/03) and surfaces a large body of **new, previously undocumented** findings, especially around test-suite health and repo hygiene, that appear not to have been caught before.

---

## Top Risks (ranked)

### 1. 🔴 CRITICAL — Secrets, session tokens, and developer PII are present in the audited source bundle
`cache/admin_password.txt` (hashed admin password), `data/ytgui.db` + `-wal` (2 MB, contains a live `sessions` table with auth tokens), `cache/library.db`, and `ytplayer.log` (580 KB access/error log containing LAN IP addresses, browser user-agents, and a Windows path revealing the developer's full real name: `C:\Users\PUTRA JAYA LIMBANGAN\...`) are **all included in the zip**, despite `.gitignore` explicitly excluding every one of them. This proves the packaging/distribution process (however this bundle was produced — zip export, backup, dev-machine copy) does not respect the gitignore boundary that the project author clearly intended as the secrets boundary. See `SECURITY_AUDIT.md` SEC-01.

### 2. 🔴 HIGH — ~22% of the test suite is broken, and it's broken in a very specific, diagnostic way
Running `pytest tests/` yields **27 failed, 12 errored, 134 passed, 1 skipped** (174 total). The failures are not flaky — they are all one story: a "Fase 3" per-room architecture refactor (`RoomManager`, per-room `EventBus`, `/ws?room=`, room-scoped command handlers `handler(room_id, payload)`) was tested extensively (`tests/unit/core/test_room_manager.py`, `tests/integration/test_fase1.py`, part of `tests/integration/test_fase0.py`) but **was never merged into, or was reverted out of, the actual implementation** (`server/app.py::create_app` still takes a single global `playback_controller`; `core/command_bus.py` is a plain module-level singleton). This directly falsifies the "Multi-room" and "per-room state isolation" claims in `README.md`. See `TECH_DEBT_REPORT.md` TD-01 and `ARCHITECTURE_AUDIT.md`.

### 3. 🟠 HIGH — No integration tests can run out-of-the-box
The 6 `test_e2e.py` tests and 2 of the `test_fase1.py` tests fail immediately with `fixture 'aiohttp_client' not found` because `pytest-aiohttp` is not declared as a dependency anywhere (`requirements.txt` has none of `pytest`, `pytest-asyncio`, or `pytest-aiohttp`). There is no CI config in the repo to catch this. Effectively, nobody can run the full test suite without already knowing which undocumented packages to install. See `TECH_DEBT_REPORT.md` TD-02.

### 4. 🟡 MEDIUM — Unbounded local growth: two garbage-collection routines exist but are never called
`Database.evict_stale_tracks()` and `Database.cleanup_sessions()` are fully implemented, tested, and referenced in `core/ports.py`, but **no scheduler anywhere in `main.py`/`start.py`/`engine/` ever invokes them**. On a long-running install this means the `sessions` table and the cached-track rows/`cache/mp3` directory grow forever. See `PERFORMANCE_AUDIT.md` PERF-05 and `CODE_QUALITY_REPORT.md`.

### 5. 🟡 MEDIUM — Dead code and orphaned symbols from the abandoned refactor
`_RADIO_SEARCH_SEM` (`engine/radio_engine.py:19`) is defined and never referenced anywhere, including tests. `_normalize_title()` in the same file is only referenced by tests, not by any production code path. `middleware.py::check_rate_limit_sync()` is an empty `pass` function that is never called. These are low-severity individually but are symptomatic of the same unfinished-refactor problem as risk #2.

---

## What's Genuinely Good (don't lose this in the rewrite)

- **SQL layer (`cache/db.py`, `services/discover_service.py`)**: 100% parameterized queries, no string-built SQL from user input, atomic favorite-toggle.
- **Streaming proxy (`server/handlers/http.py::serve_stream`)**: real SSRF protection (scheme+domain allow-listing on the resolved YouTube CDN URL), real path-traversal protection (`resolve().is_relative_to()`), video-ID regex validation before touching the filesystem.
- **Auth (`core/security.py`, `server/handlers/auth.py`)**: PBKDF2-SHA256 with per-password salt, `secrets.compare_digest`, per-IP rate limiting with stale-entry pruning, plaintext-password fallback explicitly removed (`TASK-1.1`).
- **mpv IPC layer (`engine/mpv_controller.py`)**: correctly handles request-id correlation under an `asyncio.Lock`, has automatic reconnect with backoff, and degrades gracefully instead of crashing the process.
- **Frontend XSS discipline**: virtually every place track metadata (title/artist, which originates from untrusted YouTube data) is written into `innerHTML`, it is passed through a real `escapeHtml()` helper first.

---

## Recommended Immediate Actions (this week)

1. Rotate the admin password and purge `data/ytgui.db`, `cache/admin_password.txt`, `cache/library.db`, `ytplayer.log` from wherever this bundle has been stored/shared; add a packaging step (or pre-commit hook) that refuses to zip anything matching `.gitignore`.
2. Decide, explicitly, whether multi-room is an active goal. If yes, finish `RoomManager`/per-room bus and delete no test until it passes. If no, delete `test_room_manager.py`, the room-only parts of `test_fase0.py`/`test_fase1.py`, and rewrite `README.md` to stop claiming multi-room/enterprise architecture.
3. Add `pytest`, `pytest-asyncio`, `pytest-aiohttp` to a `requirements-dev.txt` and wire up a minimal CI workflow so "134 passed" doesn't quietly hide "12 errored".
4. Wire `evict_stale_tracks()` and `cleanup_sessions()` into a periodic task (the codebase already has the `safe_create_task` pattern used elsewhere for this).

See `REFACTOR_ROADMAP.md` for the full phased plan.
