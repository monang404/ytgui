# AGENT BRIEF — Execute the bagas.fm / YTGUI Refactor Roadmap


## ROLE

You are a Senior Python/JS engineer doing **incremental, low-risk maintenance** on a working, deployed personal project (a self-hosted YouTube music player). This is not a greenfield rewrite. The existing code mostly works and is used daily. Your job is to fix specific, already-diagnosed issues — not to redesign things that weren't flagged.

## REQUIRED READING BEFORE YOU TOUCH ANYTHING

Read these six files first, in this order. They are the audit that produced your task list. Every task below cites a finding ID (e.g. `SEC-01`, `CQ-03`, `PERF-02`, `TD-01`) — go read that finding's full write-up before implementing it, don't work from the one-line summary alone.

1. `docs/EXECUTIVE_SUMMARY.md`
2. `docs/SECURITY_AUDIT.md`
3. `docs/CODE_QUALITY_REPORT.md`
4. `docs/PERFORMANCE_AUDIT.md`
5. `docs/TECH_DEBT_REPORT.md`
6. `docs/ARCHITECTURE_AUDIT.md`
7. `docs/REFACTOR_ROADMAP.md` — this is your master task list; the phases below mirror it exactly.

## GROUND RULES

1. **One task at a time, in phase order.** Do not start a Phase 2 task before every Phase 1 task is done and verified. Do not start a Phase 3 task before Phase 2's exit criteria are met.
2. **Run the test suite before and after every task.** Baseline first:
   ```bash
   pip install -r requirements.txt --break-system-packages
   pip install pytest pytest-asyncio pytest-aiohttp --break-system-packages
   python3 -m pytest tests/ -q
   ```
   Record the baseline pass/fail count. After each change, re-run and confirm you did not reduce the pass count (increasing it is expected and good, especially in Phase 2).
3. **Never invent scope.** If a task references a decision that hasn't been made yet (see Task 1.4 below), stop and ask the human instead of guessing. Do not silently pick an answer for architecturally significant questions.
4. **Preserve existing patterns.** This codebase has consistent conventions (structlog logging, `safe_create_task` for background tasks, `Protocol`-based ports in `core/ports.py`, parameterized SQL only, `asyncio.create_subprocess_exec` never `shell=True`). Match them — don't introduce a new logging library, a new async pattern, or a new dependency unless a task explicitly calls for it.
5. **Small, reviewable diffs.** One finding ID = one commit (or one small group of commits if the finding naturally splits). Write commit messages referencing the finding ID, e.g. `fix(security): remove shell=True from port-detection subprocess calls [SEC-02]`.
6. **Don't touch what wasn't flagged.** The audit explicitly lists what's already good (see "What Was Checked and Found Clean" in `SECURITY_AUDIT.md` and "What's Genuinely Good" in `EXECUTIVE_SUMMARY.md`). Leave that code alone.
7. **Indonesian-language comments and strings are intentional** (this is an Indonesian-market app) — do not translate them to English as a side effect of your edits.
8. **After finishing each phase**, write a short status update appended to `docs/audit/EXECUTION_LOG.md` (create it if it doesn't exist): what you did, what you verified, what you skipped and why, and the before/after test pass count.

---

## PHASE 1 — CRITICAL (do first, stop and confirm with the human before proceeding to Phase 2)

- [ ] **1.1 / 1.3 — Secrets exposure (`SEC-01`).** These are *operational* actions, not code changes: rotate the admin password, invalidate old sessions, and purge `data/ytgui.db*`, `cache/library.db*`, `cache/admin_password.txt`, `ytplayer.log` from the working tree if they are still present. **Do not attempt this yourself if you don't have the operational access to rotate the live server's credentials — flag it to the human explicitly and move on to 1.2.**
- [ ] **1.2 — Packaging process (`SEC-01`, `TD-07`).** Add a `Makefile` target or shell script (e.g. `scripts/make_dist.sh`) that produces distributable archives via `git archive HEAD -o dist.zip` (or equivalent) instead of a raw directory copy, so gitignored files structurally cannot be included. Verify by running it and confirming `admin_password.txt`, `*.db`, `*.log` are absent from the output archive.
- [ ] **1.4 — Multi-room decision (`TD-01`).** **STOP HERE. Do not decide this yourself.** Ask the human: *"Is multi-room support (per-room EventBus, `RoomManager`, `/ws?room=` routing) still an active goal, or should it be rolled back?"* Their answer determines the scope of Phase 2, Task 2.1. Do not proceed past this point until you have an answer recorded in `docs/audit/EXECUTION_LOG.md`.

**Phase 1 exit criteria:** no secrets in any distributable artifact; multi-room decision is recorded in writing.

---

## PHASE 2 — HIGH

- [ ] **2.1 — Resolve the multi-room test/code mismatch (`TD-01`).**
  - If the human said **"roll back"**: delete `tests/unit/core/test_room_manager.py` in full; remove the room-specific test classes (`TestTask14RoomIdValidation`, room-scoped parts of `TestTask02RetryCountReset`/`TestTask03RadioBgTasksCancel`/`TestTask04DownloadSignature`) from `tests/integration/test_fase0.py` and `tests/integration/test_fase1.py` — but do **not** delete the parts of those files testing behavior that *does* exist (read each test individually; some file names are shared between room-specific and non-room-specific tests). Update `README.md` to remove or caveat the "Multi-room" claim.
  - If the human said **"finish it"**: this is a multi-day architectural task, not something to attempt in one pass. Break it into its own sub-plan (introduce `RoomManager`, thread `room_id` through `CommandBus.execute`, update `server/app.py::create_app` signature and all its callers including `main.py`) and confirm the sub-plan with the human before writing code.
- [ ] **2.2 — Test infra (`TD-02`, `TD-05`).** Create `requirements-dev.txt` with `pytest`, `pytest-asyncio`, `pytest-aiohttp` (pin to versions confirmed working during your baseline run). Add a CI workflow file (ask the human which CI provider they use — GitHub Actions is a reasonable default if unspecified) that installs both requirements files and runs `pytest`.
- [ ] **2.3 — Verify.** Re-run the full suite. Target: 0 failed, 0 errored. If any remain and are unrelated to the room refactor, document them individually in `EXECUTION_LOG.md` and ask the human whether to fix now or defer.
- [ ] **2.4 — Wire up dead cleanup routines (`PERF-01`, `TD-03`).** In `main.py`, add a periodic background task following the exact pattern already used for `mpv_reconnect_checker` (`safe_create_task`, infinite loop with `asyncio.sleep`) that calls `db.evict_stale_tracks()` and `db.cleanup_sessions()` on a sensible interval (daily is reasonable; make it configurable via `config.py` if there's already a precedent for that). Add or update a unit test asserting the task is scheduled at startup.
- [ ] **2.5 — Fix yt-dlp search result count (`PERF-03`).** In `engine/ytdlp_client.py::search()`, change `url = f"ytsearch10:{query}"` to use `max_results` in the query string. Verify existing tests for this method still pass, and check whether any test currently hardcodes an assumption of exactly 10 results.
- [ ] **2.6 — Add missing DB index (`PERF-02`).** In `cache/schema.sql`, add `CREATE INDEX IF NOT EXISTS idx_songs_artist_id ON songs(artist_id);`. Since existing DBs are migrated via `Database.init()`'s `try/except` `ALTER TABLE` pattern rather than schema.sql alone for new columns, follow the same defensive pattern for this index (wrap in `try/except` at startup, since `CREATE INDEX IF NOT EXISTS` is idempotent and safe to just add directly to `schema.sql`/`executescript` — confirm this is sufficient by checking how existing indexes in `schema.sql` are applied to already-existing databases).

**Phase 2 exit criteria:** test suite is green and CI-enforced; README accurately describes the shipped architecture; no unbounded-growth code paths remain.

---

## PHASE 3 — MEDIUM

Work through these independently; each is self-contained. Suggested order (roughly duplication/security first, then perf/style):

- [ ] **3.1 — Remove `shell=True` (`SEC-02`).** In `start.py`, rewrite the `lsof`/`fuser`/`ss` subprocess calls to use list-form arguments (`shell=False`, the default). Test manually if possible (start the app, occupy the port with another process, confirm port-conflict detection still works on your platform) since this code path likely isn't covered by the automated test suite — check, and add a test if none exists.
- [ ] **3.2 — Extract `broadcast_discover_data()` (`CQ-04`).** Deduplicate the three copies in `server/handlers/websocket.py` (in the `discover`, `toggle_favorite`, `delete_download` branches) into one function, called from all three sites.
- [ ] **3.3 — Extract `user_download_path()` (`CQ-05`).** Deduplicate the filename-sanitization + path-building logic shared between `server/handlers/websocket.py::delete_download` and `engine/download_manager.py::_do_download`.
- [ ] **3.4 — Remove duplicated password-hashing fallback (`CQ-03`, `TD-04`).** In `start.py`, remove both inline PBKDF2 fallback implementations; import `hash_password` from `core.security` unconditionally, matching how `config.py` already does it.
- [ ] **3.5 — Parallelize broadcast (`PERF-04`).** In `ConnectionManager.broadcast()`, replace the sequential `for`/`await` loop with `asyncio.gather(..., return_exceptions=True)`, then filter dead connections from the results.
- [ ] **3.6 — Dispatcher refactor (`CQ-01`).** Only attempt this after Phase 2.1 is fully resolved (its shape depends on whether room_id needs threading through). Convert `handle_ws_message`'s `if/elif` chain into an `action -> handler` registry. Do this incrementally — move 2-3 actions at a time, run tests after each batch, don't do all 18 branches in one commit.
- [ ] **3.7 — Discover.js rendering (`PERF-06`).** Apply the DOM-node-reuse pattern from `queue.js::renderList` to `discover.js::renderDiscoverTab`. This touches five near-identical sections (favorites/recent/artists/genres/cached) — refactor one section first, confirm visually/behaviorally it still works, then apply the same pattern to the rest.
- [ ] **3.8 — Log swallowed exception (`CQ-09`).** In `start.py::_check_first_run`'s `except Exception as e: pass`, replace with a call to `self._write_log(...)`.
- [ ] **3.9 — Remove dead code (`CQ-06`).** Delete `_RADIO_SEARCH_SEM` and `check_rate_limit_sync()`. For `_normalize_title()`: check with the human whether radio-mode title-deduplication was intentionally dropped; if yes, delete the function and its tests in `test_fase0.py`; if it should come back, that's a separate small feature task, not a cleanup task.
- [ ] **3.10 — Remove vestigial `if True:` (`CQ-07`).** In `plugins/lyrics.py::fetch()`, remove the dead conditional and de-indent.

**Phase 3 exit criteria:** no known duplication remains in the touched paths; frontend rendering is consistent between `queue.js` and `discover.js`; dead code is gone or has a recorded reason to stay.

---

## PHASE 4 — NICE TO HAVE

Only pick these up opportunistically, e.g. when touching a file for an unrelated reason, or if explicitly asked to continue past Phase 3.

- [ ] **4.1** Extract `ServerProcessManager`/`DependencyChecker` out of `ServerManager(tk.Tk)` (`CQ-02`).
- [ ] **4.2** Factor `MpvController._command`/`_get_property` shared plumbing into one `_send_request()` (`CQ-08`).
- [ ] **4.3** Move magic numbers (login-attempt limit, command-rate limit, volume ceiling) into named shared constants, and make the frontend volume slider's `max` attribute consistent with the backend ceiling (`CQ-10`).
- [ ] **4.4** Gate reverse-proxy IP trust behind an explicit config flag, don't trust `X-Forwarded-For` unconditionally if this is ever added (`SEC-05`, `SEC-06`).
- [ ] **4.5** Add tests for pure JS helpers (`cleanTrackTitle`, `escapeHtml`, `formatTime`) using `node --test` (`TD-06`).
- [ ] **4.6** Use `secrets.compare_digest` for the admin username comparison (`SEC-04`).
- [ ] **4.7** Correct the `toggle_favorite` docstring's overstated "atomic" claim (`CQ-12`).
- [ ] **4.8** Defer: consider a connection-pool/write-queue abstraction over the shared SQLite connection only if concurrent load actually becomes a measured problem (`PERF-05`).

---

## WHEN YOU'RE DONE (or done with a phase)

Summarize in `docs/audit/EXECUTION_LOG.md`:
- Which finding IDs were addressed, in which commits
- Test pass count before/after
- Anything skipped, and why
- Any new findings you noticed while working (don't fix them silently — log them for the next audit pass)

Do not mark a finding as resolved unless the test suite (and, for UI changes, manual verification) confirms it.
