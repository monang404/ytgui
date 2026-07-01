# CODE QUALITY REPORT — bagas.fm / YTGUI

Each finding includes severity, location, root cause, impact, and recommendation. Severity scale: Critical / High / Medium / Low.

---

### CQ-01 — God function: `handle_ws_message` dispatches 18 unrelated responsibilities
- **Severity:** Medium
- **File:** `server/handlers/websocket.py`, function `handle_ws_message` (lines 93–345, ~250 lines)
- **Root cause:** Every websocket action (search, discover, favorites, queue mutation, playback transport, radio, settings) was added as another `elif action == "...":` branch in one function instead of being registered as independent handlers.
- **Why it's a problem:** Cyclomatic complexity is very high (18+ branches plus nested error handling); any change to one feature requires scrolling through and understanding all the others; the function cannot be unit-tested per-action without invoking the whole dispatcher; merge conflicts are concentrated in this single file.
- **Recommendation:** Introduce an `action → async handler(data, ctx)` registry (mirroring the existing `CommandBus` pattern already used one layer down) and have `ws_handler` look up the action instead of branching.
- **Expected benefit:** Cyclomatic complexity drops from ~20 to ~2 per handler; each action becomes independently testable; new actions no longer touch this file's diff.

---

### CQ-02 — God class: `ServerManager(tk.Tk)` mixes UI, process supervision, and OS-level port management
- **Severity:** Medium
- **File:** `start.py`, class `ServerManager` (lines 41–823, ~780 lines, 30+ methods)
- **Root cause:** The Tkinter launcher accreted responsibilities over time: window/theme building, dependency checking, subprocess start/stop/restart, cross-platform port-conflict detection (`netstat`/`lsof`/`fuser`/`ss`), process-tree killing, and password reset — all as methods on one class.
- **Why it's a problem:** No separation of concerns between "GUI" and "process control" means the process-management logic can't be reused or tested without a Tk display; the file is the single largest in the codebase (832 lines) and the hardest to safely modify.
- **Recommendation:** Extract `ServerProcessManager` (start/stop/restart/port-detection/kill) and `DependencyChecker` as plain Python classes with no Tk dependency; have `ServerManager` (the Tk widget) hold and delegate to them.
- **Expected benefit:** Process-management logic becomes unit-testable headlessly; GUI file shrinks by roughly half.

---

### CQ-03 — Duplicated PBKDF2 password-hashing implementation (3 copies, 2 of them dead-code fallbacks)
- **Severity:** High
- **Files:** `core/security.py:6-8` (canonical), `start.py:64-70` (`_check_first_run`), `start.py:734-740` (`_on_reset_password`)
- **Root cause:** `start.py` wraps `from core.security import hash_password` in a `try/except ImportError` and re-implements the exact same PBKDF2-SHA256/100000-iteration/salt logic inline as a fallback, and does so **twice independently** in two different methods.
- **Why it's a problem:** This is a security-sensitive routine duplicated three times. If the canonical implementation in `core/security.py` is ever hardened (e.g., iteration count increased, algorithm changed to Argon2), the two silent fallback copies in `start.py` will not be updated and could regenerate weaker password hashes without anyone noticing, since the `except ImportError` path is very rarely exercised in practice (it only triggers if `core.security` is unimportable — but `start.py` already imports plenty of other `core.*`/project modules unconditionally elsewhere, so this defensive fallback is very unlikely to ever be needed).
- **Recommendation:** Delete both fallback copies; import `hash_password` from `core.security` unconditionally, exactly as `config.py` already does. If `start.py` genuinely needs to run without the rest of the package importable, that's a packaging problem to fix at the source, not something to work around with duplicated crypto.
- **Expected benefit:** One source of truth for password hashing; removes ~28 lines of duplicated security-sensitive code.

---

### CQ-04 — Duplicated "fetch + broadcast discover data" block (3 copies, ~14 lines each)
- **Severity:** Low–Medium
- **File:** `server/handlers/websocket.py` lines 130–146, 167–182, 264–279
- **Root cause:** The sequence `DiscoverService(db)` → fetch recent/favorites/cached/artists/genres → build the `discover_data` message → broadcast, is copy-pasted verbatim into the `discover`, `toggle_favorite`, and `delete_download` action handlers.
- **Why it's a problem:** Any change to what "discover data" contains (e.g., adding a new field) must be made in three places; the first miss produces a client that shows stale/incomplete discover data only in the branches that were forgotten. Classic Shotgun Surgery smell.
- **Recommendation:** Extract `async def broadcast_discover_data(manager, db): ...` as a single function and call it from all three sites.
- **Expected benefit:** ~35 lines removed; future discover-related bugs fixed once instead of up to three times.

---

### CQ-05 — Duplicated download-filename sanitization logic
- **Severity:** Low
- **Files:** `server/handlers/websocket.py:245-247` (inside `delete_download`) and `engine/download_manager.py:68-70` (inside `_do_download`)
- **Root cause:** The `re.sub(r'[\/*?:"<>|]', "", ...)` filename-safe transform and the `"{artist} - {title}.mp3"` path template are duplicated between the code that *creates* the downloaded file's user-facing copy and the code that *deletes* it.
- **Why it's a problem:** If the sanitization rule or naming template ever changes in one place, `delete_download` will look for the old filename pattern and silently fail to remove the user-facing copy, leaving an orphaned file in `downloads/`.
- **Recommendation:** Extract a shared `def user_download_path(artist: str, title: str) -> Path` helper (e.g., in `engine/download_manager.py` or a new `core/naming.py`) used by both call sites.
- **Expected benefit:** Guarantees delete always matches create; removes duplicate regex.

---

### CQ-06 — Dead code left over from an abandoned refactor / removed feature
- **Severity:** Low
- **Locations:**
  - `engine/radio_engine.py:19` — `_RADIO_SEARCH_SEM = asyncio.Semaphore(4)` is defined and never referenced anywhere in the codebase (including tests).
  - `engine/radio_engine.py:43-50` — `_normalize_title()` is only referenced from `tests/integration/test_fase0.py`; no production code path calls it.
  - `server/middleware.py:4-5` — `def check_rate_limit_sync(): pass` is a stub that is never called or imported anywhere (`check_rate_limit`, the async version, is what's actually used).
  - `cache/db.py:56-80,229-232` — `evict_stale_tracks()` and `cleanup_sessions()` are fully implemented but never invoked by any scheduler (see `PERFORMANCE_AUDIT.md` PERF-05).
- **Why it's a problem:** Dead code increases the surface a reader has to understand to trust that "everything here matters," and specifically for `_normalize_title`/`_RADIO_SEARCH_SEM` it signals an incomplete removal of a deduplication/rate-limiting feature that may have been silently dropped from Radio Mode without a decision being recorded anywhere.
- **Recommendation:** Either wire these back in (if the feature was meant to stay) or delete them along with their now-orphaned tests.
- **Expected benefit:** Smaller, more trustworthy codebase; removes ambiguity about whether radio search is still rate-limited/deduplicated by title.

---

### CQ-07 — Vestigial `if True:` block
- **Severity:** Low (cosmetic, but signals unfinished cleanup)
- **File:** `plugins/lyrics.py:74` — `if True:` wraps the bulk of `fetch()`'s body with no corresponding `else`.
- **Root cause:** Almost certainly a leftover from a removed conditional (e.g., "if not cached lyrics") during refactoring.
- **Recommendation:** Remove the `if True:` and de-indent the block.

---

### CQ-08 — Inconsistent request_id/property-command plumbing duplicated across three near-identical methods
- **Severity:** Low
- **File:** `engine/mpv_controller.py` — `_command()` (267-283), `_get_property()` (285-301), and (indirectly) `_set_property()` (303-304) all repeat the same "increment `_request_id` under `_req_lock`, register a `Future` in `_pending`, `json.dumps` + write + `drain`, `wait_for(..., timeout=2.0)`" sequence.
- **Why it's a problem:** Any bug fix to the request/response correlation protocol (e.g., changing the timeout, adding a retry) needs to be applied in two places by hand; `_command` and `_get_property` have already drifted slightly in structure despite doing the same thing.
- **Recommendation:** Factor the shared body into a private `async def _send_request(self, payload_command: list) -> Any` used by both.
- **Expected benefit:** Removes ~15 duplicated lines; guarantees `_command` and `_get_property` can never silently diverge in timeout/error handling again.

---

### CQ-09 — `except Exception: pass` silently swallows first-run password generation failures
- **Severity:** Medium
- **File:** `start.py:83-84`
```python
except Exception as e:
    pass
```
- **Why it's a problem:** If admin-password bootstrap fails for any reason (disk full, permission denied), the user gets no error, no log entry, and no password — they will be silently locked out of admin mode with zero diagnostic information. `e` is even captured and then discarded.
- **Recommendation:** At minimum, log the exception via `self._write_log(f"Failed to generate initial password: {e}", "err")`, which the class already has available.

---

### CQ-10 — Hardcoded / magic values without named constants
- **Severity:** Low
- **Examples:**
  - `server/handlers/auth.py:11-12` — `WINDOW_AUTH = 300`, `WINDOW_CMD = 60` are local constants (good), but the magic number `5` (max login attempts, line 40) and `30` (max commands/min in `middleware.py:15`) are inlined rather than named alongside them.
  - `engine/volume_service.py` — volume ceiling of `150` (per `docs/Bug_Report.md` BUG-02) is not defined as a shared constant with the frontend's `max="100"` slider attribute, so the two can drift (confirmed pre-existing bug, still present).
  - `engine/radio_engine.py:29-33` — good counter-example: `MAX_TRACK_DURATION`, `TRACKS_PER_ARTIST_TARGET`, etc. are properly named module constants. This file should be the template for the others.
- **Recommendation:** Promote the auth/rate-limit thresholds to named constants next to `WINDOW_AUTH`/`WINDOW_CMD`; move the volume ceiling into `config.py` and have both backend and (via a small `/api/config` or the existing `state` push) frontend read from a single source.

---

### CQ-11 — Repo hygiene: generated/runtime artifacts committed inside the audited source tree
- **Severity:** Medium (quality) / High (see `SECURITY_AUDIT.md` SEC-01 for the security angle)
- **Files:** `cache/library.db` (68K), `cache/library.db-shm/-wal`, `data/ytgui.db` (244K) + `-wal` (2.0MB), `ytplayer.log` (580K, 4095 lines), `cache/admin_password.txt`, `cache/mp3/` — all present despite `.gitignore` explicitly excluding every one of them.
- **Why it's a problem:** Beyond the security exposure, these files bloat the "source" bundle by several megabytes of non-source content, make diffs/reviews noisy if ever accidentally committed, and the `ytplayer.log` in particular is a live log of test-suite runs interleaved with the pytest fixture output (`{"event": "Async Handler bad_handler error on 'LogMessageEvent'..."`), meaning **test execution and application runtime share the same log sink**, which is also a logging-configuration issue (see `TECH_DEBT_REPORT.md`).
- **Recommendation:** Confirm the packaging/export step used to produce distributable bundles honors `.gitignore`; add a `Makefile`/script target (`make dist`) that does `git archive` instead of a raw directory zip, which structurally cannot include gitignored files.

---

### CQ-12 — Comment quality
- **Positive:** The Indonesian-language inline comments consistently explain *why*, not *what* (e.g., `# TASK-1.1: Tolak semua format non-pbkdf2 — hapus plaintext fallback` in `core/security.py:11`), which is exactly the right kind of comment to keep.
- **Negative:** A handful of comments are now misleading after code drift — e.g. `cache/db.py::toggle_favorite` docstring claims *"Atomic: satu UPDATE statement — tidak ada SELECT+UPDATE race condition"* (lines 363-364), but the method actually performs a `SELECT` (existence check), then the atomic `UPDATE`, then another `SELECT` (to read back the new value) — three round trips, not one. The core toggle itself is atomic; the surrounding existence-check/read-back is not, and a fast double-click could theoretically read back a value from an interleaved second call. The comment overstates the guarantee.
- **Recommendation:** Reword the docstring to scope the "atomic" claim to the `UPDATE` statement specifically, not the method as a whole.
