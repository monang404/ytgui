# REFACTOR ROADMAP — bagas.fm / YTGUI

This roadmap sequences every finding from the other six reports into an executable plan. Each phase is gated on the previous one being done, so risk and rework are minimized. No code changes are included here (per audit scope) — this is the *plan* to execute afterward.

---

## Phase 1 — Critical (do this before anything else, ideally this week)

| # | Item | Source | Why first |
|---|---|---|---|
| 1.1 | Rotate admin password; treat all existing session tokens as compromised | `SECURITY_AUDIT.md` SEC-01 | Live credential exposure — every other phase is moot if the server is compromised in the meantime |
| 1.2 | Fix the packaging/export process so it respects `.gitignore` (use `git archive`, not a raw folder copy) | `SECURITY_AUDIT.md` SEC-01, `TECH_DEBT_REPORT.md` TD-07 | Prevents this exact incident from recurring the next time source is shared |
| 1.3 | Purge `data/ytgui.db*`, `cache/library.db*`, `cache/admin_password.txt`, `ytplayer.log` from every location this bundle has been stored (backups, chat history, tickets) | `SECURITY_AUDIT.md` SEC-01 | Closes the exposure window |
| 1.4 | Decide, explicitly and in writing (an issue or a `docs/` note), whether multi-room support is an active goal | `TECH_DEBT_REPORT.md` TD-01 | Every subsequent test/architecture decision in Phase 2-3 depends on this answer |

**Exit criteria:** No secrets in any distributable artifact; a documented decision on multi-room exists.

---

## Phase 2 — High (next 1-2 sprints)

| # | Item | Source | Effort |
|---|---|---|---|
| 2.1 | Execute the Phase 1.4 decision: either finish `RoomManager`/per-room wiring, or delete `test_room_manager.py` + room-specific test classes in `test_fase0.py`/`test_fase1.py` and correct `README.md` | `TECH_DEBT_REPORT.md` TD-01, TD-08 | Large or Medium |
| 2.2 | Add `requirements-dev.txt` (`pytest`, `pytest-asyncio`, `pytest-aiohttp`) and a CI workflow that runs the full suite on every push/PR | `TECH_DEBT_REPORT.md` TD-02, TD-05 | Small |
| 2.3 | Re-run the full test suite after 2.1 and confirm 0 failures/errors before merging anything else | — | Small |
| 2.4 | Wire `evict_stale_tracks()` and `cleanup_sessions()` into a periodic background task in `main.py` | `PERFORMANCE_AUDIT.md` PERF-01, `TECH_DEBT_REPORT.md` TD-03 | Small |
| 2.5 | Fix `PERF-03`: make `YtDlpClient.search()` respect `max_results` in the `ytsearchN:` query instead of hardcoding 10 | `PERFORMANCE_AUDIT.md` PERF-03 | Small |
| 2.6 | Add `CREATE INDEX idx_songs_artist_id ON songs(artist_id);` to `cache/schema.sql` (with a migration path for existing DBs, matching the existing `ALTER TABLE ... ADD COLUMN` try/except pattern already used in `Database.init`) | `PERFORMANCE_AUDIT.md` PERF-02 | Small |

**Exit criteria:** Test suite is green and enforced by CI; the codebase's actual capabilities match its documentation; no known unbounded-growth paths remain.

---

## Phase 3 — Medium (following sprints, can be parallelized across contributors)

| # | Item | Source | Effort |
|---|---|---|---|
| 3.1 | Remove `shell=True` from `start.py`'s port-detection subprocess calls; use argument-list form | `SECURITY_AUDIT.md` SEC-02 | Small |
| 3.2 | Extract shared `broadcast_discover_data()` helper to remove the 3x duplicated block in `websocket.py` | `CODE_QUALITY_REPORT.md` CQ-04 | Small |
| 3.3 | Extract shared `user_download_path()` helper to remove duplicated filename-sanitization logic | `CODE_QUALITY_REPORT.md` CQ-05 | Small |
| 3.4 | Remove the duplicated PBKDF2 fallback implementations in `start.py`; import `hash_password` from `core.security` unconditionally | `CODE_QUALITY_REPORT.md` CQ-03, `TECH_DEBT_REPORT.md` TD-04 | Small |
| 3.5 | Replace the sequential `for ws in ...: await ws.send_str(...)` broadcast loop with `asyncio.gather` | `PERFORMANCE_AUDIT.md` PERF-04 | Small |
| 3.6 | Refactor `handle_ws_message`'s 18-branch `if/elif` into an action-registry dispatch pattern | `CODE_QUALITY_REPORT.md` CQ-01 | Medium |
| 3.7 | Apply `queue.js`'s DOM-reuse rendering pattern to `discover.js` instead of full `innerHTML` replacement | `PERFORMANCE_AUDIT.md` PERF-06 | Medium |
| 3.8 | Log the swallowed exception in `start.py::_check_first_run`'s `except Exception: pass` | `CODE_QUALITY_REPORT.md` CQ-09 | Small |
| 3.9 | Delete confirmed dead code: `_RADIO_SEARCH_SEM`, `check_rate_limit_sync()`; decide the fate of `_normalize_title()` (wire it back in or delete it + its tests) | `CODE_QUALITY_REPORT.md` CQ-06 | Small |
| 3.10 | Remove the vestigial `if True:` block in `plugins/lyrics.py::fetch()` | `CODE_QUALITY_REPORT.md` CQ-07 | Small |

**Exit criteria:** No known code duplication in security-sensitive or high-churn paths; frontend rendering strategy is consistent; no dead code remains without an explicit decision recorded.

---

## Phase 4 — Nice to Have (opportunistic, no urgency)

| # | Item | Source | Effort |
|---|---|---|---|
| 4.1 | Extract `ServerProcessManager`/`DependencyChecker` out of the `ServerManager(tk.Tk)` God class | `CODE_QUALITY_REPORT.md` CQ-02 | Medium |
| 4.2 | Factor `MpvController`'s `_command`/`_get_property` shared plumbing into one `_send_request()` | `CODE_QUALITY_REPORT.md` CQ-08 | Small |
| 4.3 | Move magic numbers (login-attempt limit `5`, command-rate limit `30`, volume ceiling `150`) into named, shared constants | `CODE_QUALITY_REPORT.md` CQ-10 | Small |
| 4.4 | Reconsider `client_ip` derivation (`request.remote`) for forward-compatibility with reverse-proxy deployments, gated behind an explicit trusted-proxy config flag | `SECURITY_AUDIT.md` SEC-05, SEC-06 | Medium |
| 4.5 | Add lightweight tests for pure JS helper functions (`cleanTrackTitle`, `escapeHtml`, `formatTime`) | `TECH_DEBT_REPORT.md` TD-06 | Medium |
| 4.6 | Use `secrets.compare_digest` for the admin username comparison in `handle_auth` | `SECURITY_AUDIT.md` SEC-04 | Small |
| 4.7 | Correct the `toggle_favorite` docstring's "atomic" claim to scope it accurately to the `UPDATE` statement | `CODE_QUALITY_REPORT.md` CQ-12 | Small |
| 4.8 | Consider a connection-pool or write-queue abstraction over the single shared `aiosqlite` connection if/when concurrent load increases | `PERFORMANCE_AUDIT.md` PERF-05, `ARCHITECTURE_AUDIT.md` §3 | Large (defer until needed) |

---

## Sequencing Notes

- **Phase 1 must complete before Phase 2** — there is no value in fixing tests or performance on top of a codebase whose distribution process is actively leaking credentials.
- **Phase 2.1 (the multi-room decision) gates almost everything else in code quality and architecture** — several Phase 3 items (notably 3.6, the dispatcher refactor) will look different depending on whether room-scoping needs to be threaded through them. It is worth resolving 2.1 before starting 3.6 specifically.
- Phases 3 and 4 are otherwise largely independent of each other and can be parallelized across multiple contributors or done opportunistically alongside feature work.
- No item in this roadmap requires a new external dependency, a data migration with downtime, or a breaking API change for end users — all changes are internal engineering hygiene.
