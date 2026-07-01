# TECH DEBT REPORT — bagas.fm / YTGUI

Effort scale: **Small** (a few hours), **Medium** (a day or two), **Large** (multi-day/architectural).

---

### TD-01 — Abandoned "Fase 3" multi-room refactor left half-wired, with 20+ tests validating a feature that doesn't exist
- **Effort:** Large (to finish) / Medium (to properly roll back)
- **Evidence:** Running `python3 -m pytest tests/ -q` against the codebase as-delivered produces **27 failed, 12 errored, 134 passed, 1 skipped** out of 174 collected tests. The failures cluster almost entirely around one theme:
  - `tests/unit/core/test_room_manager.py` — every test in `TestTask32RoomOwnEventBus`, `TestTask36ServerPerRoomSubscriptions`, `TestTask37NoGlobalBusImports` fails because the production code has no `RoomManager` class, no `on_room_created` callback mechanism, and `server/app.py::create_app` does not accept a room manager.
  - `tests/integration/test_fase1.py` — `TestTask14RoomIdValidation` expects `/ws?room=<id>` query-param routing with a max-rooms limit (HTTP 429) and room-ID validation; the actual `ws_handler` (`server/handlers/websocket.py:56`) takes no room parameter at all.
  - `tests/integration/test_fase0.py` — `TestTask04DownloadSignature` expects command handlers to be registered with signature `handler(room_id, payload)`; the actual `CommandBus.execute` (`core/command_bus.py:28`) calls `handler(data)` — single argument, no room concept.
  - `tests/unit/core/test_command_bus.py::test_command_bus_register_and_execute` fails for the identical reason — the test's mock handler expects `(room_id, payload)`.
- **Why this matters more than a normal test failure:** This is not flakiness or environment drift — it is **documentation, in executable form, of a planned architecture that was never completed**, sitting alongside the actually-shipped single-instance architecture, with nothing in the repository (no `docs/` note, no comment, no `README` caveat) explaining the discrepancy. Any new contributor who runs the test suite will reasonably conclude the codebase is badly broken, when in fact the *implementation* mostly works fine — it's the *tests* that describe a different, unbuilt system.
- **Recommendation:** This needs a product decision, not just an engineering fix:
  1. **If multi-room is still a goal:** Finish it. The DI groundwork is already there (`MpvController`/`LyricsFetcher` already accept an injected `event_bus`), so the remaining work is primarily in `server/app.py` (introduce `RoomManager`, route `/ws?room=`) and `core/command_bus.py` (thread `room_id` through command dispatch). Budget this as a genuine multi-day architecture task, not a quick patch.
  2. **If multi-room is not currently a goal:** Delete `test_room_manager.py`, the room-specific classes in `test_fase0.py`/`test_fase1.py`, and correct `README.md`'s "Multi-room" claims. This is the faster path and is recommended given the project's actual current usage pattern (single admin, personal server).
- **Expected benefit:** Either way, the test suite starts reporting an accurate signal, which is a prerequisite for trusting CI at all.

---

### TD-02 — Test suite cannot run end-to-end without undocumented dev dependencies
- **Effort:** Small
- **Evidence:** `tests/integration/test_e2e.py` (6 tests) and 2 tests in `test_fase1.py` fail with `fixture 'aiohttp_client' not found` until `pytest-aiohttp` is installed. `requirements.txt` contains only runtime dependencies (`yt-dlp`, `aiosqlite`, `aiohttp`, `syncedlyrics`, `structlog`, `prometheus_client`, `opentelemetry-*`) — no `pytest`, `pytest-asyncio`, or `pytest-aiohttp` anywhere, and there is no `requirements-dev.txt`, `pyproject.toml` `[test]` extra, or CI workflow file in the repository to pin/install them automatically.
- **Why it's a problem:** Nobody can reliably run the full test suite without tribal knowledge of exactly which packages to add. This audit had to discover the missing dependency empirically by running the tests and reading the error.
- **Recommendation:** Add `requirements-dev.txt` with `pytest`, `pytest-asyncio`, `pytest-aiohttp` pinned to the versions this suite is known to work with, and add a minimal GitHub Actions (or equivalent) workflow that runs `pip install -r requirements.txt -r requirements-dev.txt && pytest`.
- **Expected benefit:** Reproducible test runs for any contributor; a real CI signal instead of a manually-invoked, easy-to-skip step.

---

### TD-03 — Dead cleanup routines (`evict_stale_tracks`, `cleanup_sessions`) never scheduled
- **Effort:** Small
- **See:** `PERFORMANCE_AUDIT.md` PERF-01 for full detail. Listed here because it's as much a "code that was written and then never finished being integrated" debt item as it is a performance issue.

---

### TD-04 — Duplicated password-hashing fallback logic in `start.py`
- **Effort:** Small
- **See:** `CODE_QUALITY_REPORT.md` CQ-03 for full detail.

---

### TD-05 — No CI/CD configuration of any kind in the repository
- **Effort:** Small (to bootstrap) / ongoing
- **Evidence:** No `.github/workflows/`, `.gitlab-ci.yml`, `azure-pipelines.yml`, or equivalent found anywhere in the tree.
- **Why it's a problem:** Combined with TD-01 and TD-02, this means the 27 failing / 12 erroring tests have almost certainly never been surfaced to anyone in an automated way — they can only have been discovered by manually running `pytest`, which this audit's evidence suggests either wasn't done recently or the results were not acted on.
- **Recommendation:** Add a minimal CI workflow (lint + test) as a first step even before deeper fixes; this alone will prevent further regressions from compounding the existing debt.

---

### TD-06 — Frontend has no test coverage at all
- **Effort:** Medium
- **Evidence:** `tests/` contains exclusively Python tests; no `web/static/js/**/*.test.js`, no JS test runner config, no `package.json` at all in the repository.
- **Why it's a problem:** The frontend (~25 JS files, `store.js` as a hand-rolled state container, non-trivial rendering/diffing logic in `queue.js`) is entirely unverified by automation; correctness currently depends solely on manual QA (as evidenced by `docs/Bug_Report.md`, which reads like the output of exactly that kind of manual pass).
- **Recommendation:** Not urgent given the project's scale, but worth at minimum adding lightweight tests for the pure functions that don't touch the DOM (`utils.js::cleanTrackTitle`, `escapeHtml`, `formatTime`) using a zero-config runner (e.g., `node --test` needs no bundler for plain functions like these).
- **Expected benefit:** Regression protection for the logic most likely to silently break (text-cleaning regexes, time formatting) without requiring a full frontend test-infrastructure investment.

---

### TD-07 — Repo hygiene / packaging process leaks gitignored files (cross-reference)
- **Effort:** Small
- **See:** `SECURITY_AUDIT.md` SEC-01 and `CODE_QUALITY_REPORT.md` CQ-11. Listed here too because fixing the *packaging process* (not just deleting the leaked files once) is a process/tooling debt item independent of the security severity.

---

### TD-08 — `README.md` overstates the current architecture ("Enterprise", "Multi-room", "Hexagonal Architecture") relative to what's actually running
- **Effort:** Small
- **Evidence:** `README.md` line ~19: *"Arsitektur Enterprise & Multi-room: Dibangun dengan Hexagonal Architecture (Ports and Adapters), pola CommandBus & EventBus, serta mendukung Multi-room..."* — Hexagonal Architecture and CommandBus/EventBus are accurate (see `ARCHITECTURE_AUDIT.md` section 1). Multi-room is not (see TD-01).
- **Why it's a problem:** Documentation that overstates capability erodes trust once a reader (contributor, evaluator, this audit) discovers the gap, and can lead to wasted effort by anyone who tries to actually use multi-room expecting it to work.
- **Recommendation:** Update the README to match TD-01's resolution once decided — either "Multi-room (in progress)" with a link to tracking issue, or remove the claim.

---

## Effort Summary

| ID | Item | Effort |
|---|---|---|
| TD-01 | Multi-room refactor: finish or roll back | Large / Medium |
| TD-02 | Missing dev-dependency pinning for tests | Small |
| TD-03 | Wire up dead cleanup routines | Small |
| TD-04 | Duplicated password-hashing fallback | Small |
| TD-05 | No CI configuration | Small |
| TD-06 | Zero frontend test coverage | Medium |
| TD-07 | Packaging process leaks gitignored files | Small |
| TD-08 | README overstates architecture | Small |
