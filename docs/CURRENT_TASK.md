Document Metadata

Field| Value
Document| CURRENT_TASK.md
Purpose| Single implementation backlog for AI coding agents
Primary Consumer| AI Coding Agents
Secondary Consumer| Human Engineers
Update Frequency| After every completed task
Companion Document| AI_PLAYBOOK.md
Source of Truth| Source Code → AI_PLAYBOOK.md → CURRENT_TASK.md
Read Order| Read AI_PLAYBOOK.md first, then CURRENT_TASK.md
Scope| Active implementation work only

---

AI Read Order

Before making any code changes, follow this sequence:

1. Read AI_PLAYBOOK.md
2. Read CURRENT_TASK.md
3. Open only the source files referenced by the current task.
4. Discover additional files incrementally through imports or call graphs.
5. Do not scan the entire repository unless explicitly required.

---

Current Execution

Field| Value
Current Sprint| SPRINT 8
Current Task| S8-05
Next Task| S8-06
Current Status| Ready
Blockers| None

---

Status Summary

Status| Count
Backlog| 0
Ready| 0
In Progress| 0
Blocked| 0
Verification| 0
Done| 52
Unverified| 0

«Keep this table updated after every completed task.»

---

AI Execution Rules

Always

- Complete tasks sequentially unless dependencies allow parallel execution.
- Verify every implementation against the source code.
- Run all required verification steps before marking a task as Done.
- Update this document immediately after task completion.
- Preserve architecture, module ownership, and public contracts.

Never

- Skip verification.
- Modify unrelated files.
- Rename public APIs.
- Rename event names.
- Rename state keys.
- Change contracts without updating AI_PLAYBOOK.md.
- Mark a task as Done without successful verification.

---

Task Completion Protocol

After completing a task:

1. Update task status.
2. Execute all verification steps.
3. Execute regression checks.
4. Record verification results.
5. Update affected task dependencies if necessary.
6. Continue to the next eligible task.

If any verification fails:

- Stop implementation.
- Investigate the failure.
- Fix the issue.
- Re-run verification.
- Do not continue until verification passes.

---

Navigation

This document contains:

- Sprint Backlog
- Features
- Bug Fixes
- Refactoring Tasks
- Technical Debt
- Dependencies
- Verification Results
- Completed Tasks
- Unverified Findings

For architecture, coding standards, runtime flow, constraints, and verification protocols, refer to AI_PLAYBOOK.md


# CURRENT_TASK.md
> Implementation backlog for ytgui / bagas.fm  
> Every task is verified against source code in `ytgui-main__1_.zip`.  
> Source code always wins over documentation.  
> AI agents: read `AI_PLAYBOOK.md` before executing any task.

---

## SPRINT 0 — Critical Bugfixes (No Structural Changes)

> All tasks in this sprint operate in-place. No files moved, no folders created.  
> Complete and verify every task before starting Sprint 1.

---

### S0-01

- **ID:** S0-01
- **Title:** Remove duplicate CSS block in base.css (lines 365–472)
- **Type:** Bug
- **Priority:** Critical
- **Status:** Done
- **Description:** `base.css` contains an exact duplicate of the player control CSS block. The block spanning roughly lines 147–274 (`.pb-ctrl`, `.pb-badges`, `.btn-shuffle`, `.btn-repeat`, `.btn-play`, `.btn-prev`, `.btn-next`, `.pb-ctrl .pb-sec`, and the mini-player `@media (max-width: 1023px)` override) is repeated verbatim starting at line 365. The second copy always wins specificity battles silently, making edits to the first copy have no visible effect.
- **Evidence:**
  - `grep -n "btn-shuffle" web/static/css/base.css` → lines 186 and 384 (duplicate confirmed)
  - `grep -n "pb-ctrl .pb-sec" web/static/css/base.css` → lines 167 and 365 (duplicate confirmed)
  - `wc -l web/static/css/base.css` → 617 lines (expected ~300 after dedup)
- **Affected Files:** `web/static/css/base.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `grep -c "\.btn-shuffle, \.btn-repeat {" web/static/css/base.css` returns `1`
  - `grep -c "pb-ctrl .pb-sec" web/static/css/base.css` returns `1`
  - `wc -l web/static/css/base.css` is approximately half the current value
  - All player controls render identically before and after
- **Verification Steps:**
  1. `grep -n "\.pb-ctrl {" web/static/css/base.css` — note both line numbers
  2. View both blocks side-by-side and confirm identical content with `diff`
  3. Delete the second block (lines ~365–472)
  4. Run regression: player bar visible, play/pause/next/prev/shuffle/repeat buttons render correctly at all breakpoints
- **Risk:** Low — removing a true duplicate; second copy is always overriding first anyway
- **Estimated Impact:** Eliminates silent specificity bugs; reduces CSS file size ~50%

---

### S0-02

- **ID:** S0-02
- **Title:** Remove duplicate Google Fonts blocking load in index.html
- **Type:** Bug
- **Priority:** High
- **Status:** Done
- **Description:** `index.html` loads the Inter font twice: once via a non-blocking `<link rel="preload">` with `onload` swap (correct pattern, lines 10–11), and again via a blocking `<link rel="stylesheet">` (lines 15–17 with a redundant `<link rel="preconnect">` at line 15). The blocking load adds a render-blocking network request to Google Fonts on every page load.
- **Evidence:**
  - `grep -n "fonts.googleapis" web/static/index.html` → lines 8, 10, 11, 15, 17
  - Line 10: `preload as="style" onload=...` (correct)
  - Line 17: `rel="stylesheet"` (blocking, redundant)
- **Affected Files:** `web/static/index.html`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `grep -c "fonts.googleapis.com/css" web/static/index.html` returns `2` (preload + noscript fallback only)
  - No `<link rel="stylesheet" href="https://fonts.googleapis.com...">` remains outside `<noscript>`
  - Font loads correctly in browser Network tab (single request)
- **Verification Steps:**
  1. `grep -n "fonts.googleapis" web/static/index.html` before edit
  2. Remove lines 15–17 (`<link rel="preconnect">` duplicate + `<link rel="stylesheet">` blocking load)
  3. Hard-reload page, open Network tab → confirm 1 font CSS request, not 2
- **Risk:** Low
- **Estimated Impact:** Eliminates render-blocking resource; improves First Contentful Paint

---

### S0-03

- **ID:** S0-03
- **Title:** Remove duplicate `--sab` setProperty call in main.js
- **Type:** Bug
- **Priority:** High
- **Status:** Done
- **Description:** `main.js` lines 54–55 call `document.documentElement.style.setProperty("--sab", "env(safe-area-inset-bottom)")` twice in immediate succession with identical arguments. No effect other than a redundant DOM write.
- **Evidence:**
  - `grep -n "\-\-sab" web/static/js/main.js` → lines 54 and 55, content identical
- **Affected Files:** `web/static/js/main.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `grep -c "\-\-sab" web/static/js/main.js` returns `1`
  - Safe-area bottom inset still applies on iOS devices
- **Verification Steps:**
  1. `grep -n "\-\-sab" web/static/js/main.js` — confirm two identical lines
  2. Delete one line
  3. Test on iPhone (or simulator) — nav bar bottom spacing unchanged
- **Risk:** None
- **Estimated Impact:** Minor; eliminates pointless redundant DOM write

---

### S0-04

- **ID:** S0-04
- **Title:** Resolve `.vol-grp` show/hide contradiction in layout.css
- **Type:** Bug
- **Priority:** Critical
- **Status:** Done
- **Description:** `layout.css` has three conflicting rules for `.vol-grp` inside `@media (min-width: 1024px)` blocks: line 134 sets `display: none !important`, line 355 repeats `display: none !important`, and line 430 sets `display: flex`. Two separate `@media (min-width: 1024px)` blocks exist (lines 34, 412, 451) and they contradict each other depending on cascade order. The volume slider behavior on desktop is undefined and browser-dependent.
- **Evidence:**
  - `grep -n "vol-grp" web/static/css/layout.css` → lines 134, 355, 430
  - `grep -n "min-width: 1024px" web/static/css/layout.css` → lines 34, 412, 451
  - Line 134: `#player-bar .vol-grp { display: none !important; }`
  - Line 355: same rule repeated
  - Line 430: `.pb-ctrl .vol-grp { display: flex; ... }`
- **Affected Files:** `web/static/css/layout.css`
- **Dependencies:** None — decision must be made before Sprint 2 merges these blocks
- **Acceptance Criteria:**
  - Single, unambiguous CSS rule governs `.vol-grp` visibility on desktop
  - No `!important` conflict remains (or only one intentional `!important` with comment)
  - Volume slider visually behaves as intended at ≥1024px width
  - `grep -c "vol-grp" web/static/css/layout.css` returns `1` (or `2` max if show/hide on different selectors intentionally)
- **Verification Steps:**
  1. Decide: should volume slider be visible on desktop? (per REFACTOR_PLAN: yes, in player bar)
  2. Remove lines 134 and 355 (the `display: none !important` rules)
  3. Ensure line 430's `display: flex` is inside the correct `@media (min-width: 1024px)` block
  4. Resize browser to ≥1024px — confirm vol slider visible, no flicker
  5. Resize to <1024px — confirm vol slider hidden
- **Risk:** Medium — affects desktop layout; visual regression possible if decision wrong
- **Estimated Impact:** Eliminates undefined behavior on desktop; fixes vol slider UX

---

### S0-05

- **ID:** S0-05
- **Title:** Remove duplicate `@media (max-width: 480px)` block in tabs.css
- **Type:** Bug
- **Priority:** Medium
- **Status:** Done
- **Description:** `tabs.css` has two identical `@media (max-width: 480px)` blocks at lines 74 and 77 with the same rules for `.discover-section`, `.fav-card`, `.sr-item { flex: 1 1 100% }`.
- **Evidence:**
  - `grep -n "max-width: 480px" web/static/css/tabs.css` → lines 74 and 77
- **Affected Files:** `web/static/css/tabs.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `grep -c "max-width: 480px" web/static/css/tabs.css` returns `1`
  - Discover section, fav cards, and search result items still stack full-width on small screens
- **Verification Steps:**
  1. Confirm both blocks are identical via `diff` or side-by-side view
  2. Delete one block
  3. Test at 375px viewport — discover/fav/search items still full-width
- **Risk:** Low
- **Estimated Impact:** Removes confusing duplication; no visual change expected

---

### S0-06

- **ID:** S0-06
- **Title:** Add tap-to-home listener on mini player track info
- **Type:** Bug
- **Priority:** High
- **Status:** Done
- **Description:** When the user is on the Search, Radio, or Discover tab, `#player-bar` shows as a mini player. Tapping the track title/artist area should navigate to the Home tab. No such listener exists. `grep "pbTrackInfo" events.js` returns zero results.
- **Evidence:**
  - `grep -n "pbTrackInfo" web/static/js/events.js` → 0 results
  - `grep -n "switchTab.*home" web/static/js/events.js` → 0 results for mini player context
  - `dom.pbTrackInfo` is populated by `initDOM()` in `dom.js`
- **Affected Files:** `web/static/js/events.js`
- **Dependencies:** `dom.js` must expose `dom.pbTrackInfo`; `switchTab` must be accessible
- **Acceptance Criteria:**
  - Tapping the track info area in mini player while on any non-home tab switches to Home tab
  - Tap does not trigger when already on Home tab (no-op or guard)
  - No interference with seek bar or other player bar interactions
- **Verification Steps:**
  1. Navigate to Search tab while a track is playing
  2. Tap track title/artist in the mini player bar at bottom
  3. App navigates to Home tab
  4. Repeat from Radio and Discover tabs
- **Risk:** Low
- **Estimated Impact:** Fixes UX dead zone; critical for mobile usability

---

### S0-07

- **ID:** S0-07
- **Title:** Implement `safeStorage()` helper and wrap all `localStorage` access in utils.js
- **Type:** Bug
- **Priority:** Critical
- **Status:** Done
- **Description:** `utils.js` lines 48, 68, and 76 access `localStorage` directly without try/catch. Safari Private Mode throws a `SecurityError` when any `localStorage` API is called, crashing cover art caching entirely. No `safeStorage()` helper exists anywhere in the codebase.
- **Evidence:**
  - `grep -n "localStorage" web/static/js/utils.js` → lines 48, 68, 76 — no try/catch
  - `grep -n "safeStorage" web/static/js/utils.js web/static/js/ws.js web/static/js/events.js` → 0 results (helper does not exist)
- **Affected Files:** `web/static/js/utils.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `safeStorage` function exported/available globally with `get(key)`, `set(key, value)`, `remove(key)` — all wrapped in try/catch
  - All `localStorage` access in `utils.js` replaced with `safeStorage` calls
  - In Safari Private Mode (or with `localStorage` mocked to throw): cover art fallback renders, no uncaught console error
  - `grep -n "localStorage" web/static/js/utils.js` returns 0 direct calls (all via safeStorage)
- **Verification Steps:**
  1. Implement `safeStorage` at top of `utils.js` (or as a separate small section)
  2. Replace lines 48, 68, 76 with `safeStorage` calls
  3. In browser DevTools, run `Object.defineProperty(window, 'localStorage', { get: () => { throw new Error("blocked"); } })`
  4. Navigate to app → cover art fallback image loads, no crash in console
- **Risk:** Low
- **Estimated Impact:** Fixes crash in Safari Private Mode; affects all iOS users in private browsing

---

### S0-08

- **ID:** S0-08
- **Title:** Cancel rAF loop when not PLAYING in audio.js (fake-beat)
- **Type:** Bug
- **Priority:** Critical
- **Status:** Done
- **Description:** `audio.js` `startFakeBeatLoop()` runs `_fakeBeatRaf = requestAnimationFrame(tick)` on every frame unconditionally. When `store.status !== 'PLAYING'`, the function clears CSS properties and returns early — but still reschedules itself via the `_fakeBeatRaf = requestAnimationFrame(tick)` on line 50 (before the status check). The rAF loop never terminates while the page is open, wasting CPU even when paused or idle. Note: current code sets `_fakeBeatRaf` then checks status, so cancellation must be added in the non-PLAYING branch.
- **Evidence:**
  - `grep -n "requestAnimationFrame\|cancelAnimationFrame\|_fakeBeatRaf" web/static/js/audio.js` → lines 44, 46, 50, 73
  - Line 50: `_fakeBeatRaf = requestAnimationFrame(tick);` — executed before status check
  - No `cancelAnimationFrame` call exists anywhere in `audio.js`
  - `sed -n '44,75p' web/static/js/audio.js` confirms the structure
- **Affected Files:** `web/static/js/audio.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - When `store.status !== 'PLAYING'`, `cancelAnimationFrame(_fakeBeatRaf)` is called and `_fakeBeatRaf` is set to `null`
  - Loop restarts when status returns to `PLAYING`
  - DevTools Performance tab: 0 rAF callbacks during PAUSED state (record 10s)
- **Verification Steps:**
  1. `sed -n '44,75p' web/static/js/audio.js` — confirm exact line structure before editing
  2. In the non-PLAYING branch, before `return`, add: `cancelAnimationFrame(_fakeBeatRaf); _fakeBeatRaf = null;`
  3. Ensure the loop restarts when playback resumes (check call sites of `startFakeBeatLoop()`)
  4. DevTools Performance recording during PAUSED: rAF callbacks drop to 0
- **Risk:** Medium — loop restart logic must be verified; confirm `startFakeBeatLoop` is called on PLAYING state transition
- **Estimated Impact:** Eliminates continuous CPU drain during pause/idle; critical for mobile battery

---

### S0-09

- **ID:** S0-09
- **Title:** Wire `seed_artist` through to DB query or remove "Acak Artis" UI
- **Type:** Bug
- **Priority:** Critical
- **Status:** Done
- **Description:** The "Acak Artis" button (`#radio-randomize-btn`) sends `wsSend("radio_randomize")` but does not pass `seed_artist`. `radio_engine.py::_gather_batch()` accepts `prioritized_artist` parameter but the comment at line 311 explicitly states it is ignored: `"Since we shifted to pure random DB, we just return random songs for now."` `db.py::get_random_songs()` has no artist parameter whatsoever. The feature is completely broken end-to-end: UI exists, WS command fires, parameter is accepted but silently dropped, and DB query ignores it.
- **Evidence:**
  - `grep -n "def get_random_songs" cache/db.py` → line 199: signature `(self, limit: int = 12, exclude_ids: set[str] = None)` — no artist param
  - `sed -n '303,320p' engine/radio_engine.py` → comment at line 311 confirms intentional ignore
  - `grep -n "radio-randomize\|Acak Artis" web/static/index.html` → line 289: button exists
  - `grep -n "radioRandomizeBtn" web/static/js/events.js` → line 176: `wsSend("radio_randomize")` with no seed_artist payload
- **Affected Files:** `engine/radio_engine.py`, `cache/db.py`, `web/static/js/events.js`, `web/static/index.html`
- **Dependencies:** S0-08 (stabilize audio loop first); Sprint 8 tasks S8-01, S8-02 for full implementation
- **Acceptance Criteria (Option A — Remove UI):**
  - `#radio-randomize-btn` removed from `index.html`
  - All JS references to `dom.radioRandomizeBtn` removed from `events.js`
  - No dead UI element remains
- **Acceptance Criteria (Option B — Implement, defer to Sprint 8):**
  - Move full implementation to S8-01/S8-02
  - This task: mark button as `disabled` with `title="Em desenvolvimento"` to communicate non-function
- **Verification Steps:**
  - Option A: `grep -n "radio-randomize" web/static/index.html web/static/js/events.js` → 0 results
  - Option B: button renders as disabled; Sprint 8 tasks exist in backlog
- **Risk:** High — product decision required before coding
- **Estimated Impact:** Eliminates misleading broken UI; unblocks Sprint 8 proper implementation

---

### S0-10

- **ID:** S0-10
- **Title:** Hide radio LIVE badge when radio is OFF
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** The `.radio-live-badge` element in `index.html` line 259 is always present in the DOM and always visible. CSS class `.radio-featured.on` only animates the `.badge-dot` (pulse animation) but does not hide the entire badge when radio is off. The badge text "LIVE" and red border remain visible even when `store.playback_mode === 'QUEUE'`.
- **Evidence:**
  - `grep -n "radio-live-badge" web/static/index.html` → line 259: always rendered
  - `sed -n '541,565p' web/static/css/components.css` → `.radio-live-badge { display: flex; ... }` — no conditional hide
  - `grep -n "radio-featured.on .radio-live-badge" web/static/css/components.css` → line 626: only animates `.badge-dot`, does not control badge visibility
  - `sed -n '229,252p' web/static/js/render/tabs.js` → `renderRadio()` does not set `display` on badge
- **Affected Files:** `web/static/js/render/tabs.js`, `web/static/css/components.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - Badge hidden (or `opacity: 0`) when `store.playback_mode !== 'RADIO'`
  - Badge visible when `store.playback_mode === 'RADIO'`
  - Toggle is reactive — switching radio on/off updates badge without page reload
- **Verification Steps:**
  1. Load app with radio OFF → LIVE badge not visible
  2. Toggle radio ON → LIVE badge appears
  3. Toggle radio OFF → LIVE badge disappears
- **Risk:** Low
- **Estimated Impact:** Removes false "LIVE" signal; improves UI honesty

---

### S0-11

- **ID:** S0-11
- **Title:** Fix touch target for "Acak Artis" button (min 44x44px)
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** `#radio-randomize-btn` uses class `.label-link` which has no `padding` or `min-height` set. The button renders at approximately 24px height, well below the 44px minimum touch target. Inline styles on the element (`style="background:none; border:none; display:flex; align-items:center; gap:6px; font-family:inherit;"`) do not include height.
- **Evidence:**
  - `grep -n "radio-randomize-btn" web/static/index.html` → line 289: inline styles, no height
  - `grep -n "label-link" web/static/css/base.css` → lines 359 and 557: only `font-size`, `color`, `font-weight`, no min-height
  - No `min-height` or `padding` on `.label-link` or `#radio-randomize-btn` in any CSS file
- **Affected Files:** `web/static/css/base.css` or `web/static/css/components.css`
- **Dependencies:** S0-09 (if button is removed, this task is moot)
- **Acceptance Criteria:**
  - `#radio-randomize-btn` computed height ≥44px
  - No visual overflow of surrounding layout
- **Verification Steps:**
  1. Inspect element in DevTools → computed height ≥44px
  2. Add `padding: 12px 8px; min-height: 44px;` to `#radio-randomize-btn` or `.label-link`
- **Risk:** Low
- **Estimated Impact:** Accessibility compliance; reduces accidental miss-taps on mobile

---

### S0-12

- **ID:** S0-12
- **Title:** Fix touch target for `.home-fav-btn` (40px → 44px)
- **Type:** Bug
- **Priority:** Low
- **Status:** Done
- **Description:** `.home-fav-btn` in `player.css` line 214 is explicitly set to `width: 40px; height: 40px` — 4px short of the 44px minimum.
- **Evidence:**
  - `sed -n '214,232p' web/static/css/player.css` → `width: 40px; height: 40px`
- **Affected Files:** `web/static/css/player.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `.home-fav-btn` computed size ≥44×44px
- **Verification Steps:**
  1. Change `width: 40px; height: 40px` to `width: 44px; height: 44px` in `player.css`
  2. Inspect computed size in DevTools → ≥44×44px
  3. Visually confirm button does not clip or overlap adjacent elements
- **Risk:** Low
- **Estimated Impact:** Accessibility compliance

---

### S0-13

- **ID:** S0-13
- **Title:** Fix touch target for `.sr-more-btn` (34px → 44px)
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** `.sr-more-btn` in `components.css` line 398 is set to `width: 34px; height: 34px` — 10px short of minimum.
- **Evidence:**
  - `sed -n '398,415p' web/static/css/components.css` → `width: 34px; height: 34px`
- **Affected Files:** `web/static/css/components.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `.sr-more-btn` computed size ≥44×44px
- **Verification Steps:**
  1. Change to `width: 44px; height: 44px`
  2. Inspect computed size → ≥44×44px
  3. Search result rows visually intact
- **Risk:** Low
- **Estimated Impact:** Accessibility compliance

---

### S0-14

- **ID:** S0-14
- **Title:** Add CSS definition for `.disc-row2`
- **Type:** Bug
- **Priority:** High
- **Status:** Done
- **Description:** `index.html` line 350 uses `class="disc-row2"` on the discover-favorites container (`id="discover-favorites"`). No CSS rule for `.disc-row2` exists in any CSS file — confirmed by `grep -rn "disc-row2" web/static/css/` returning 0 results. The element has zero layout definition.
- **Evidence:**
  - `grep -n "disc-row2" web/static/index.html` → line 350: used as class
  - `grep -rn "disc-row2" web/static/css/` → 0 results
- **Affected Files:** `web/static/css/components.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `.disc-row2` has a CSS definition providing flex layout
  - Discover favorites section renders with proper spacing and structure
- **Verification Steps:**
  1. Add `.disc-row2 { display: flex; flex-direction: column; gap: var(--s2); }` to `components.css`
  2. Open Discover tab with favorites populated → cards have structured layout
- **Risk:** Low
- **Estimated Impact:** Fixes invisible layout class; Discover tab structure correct

---

### S0-15

- **ID:** S0-15
- **Title:** Rename "New Release" label to "Terakhir Diputar" in Discover tab
- **Type:** Bug
- **Priority:** Low
- **Status:** Done
- **Description:** The Discover tab shows a section labeled "New Release" but `discover_service.py::get_recent()` queries `ORDER BY last_played DESC` — it returns recently played tracks, not new YouTube releases. The label is semantically incorrect.
- **Evidence:**
  - `cat services/discover_service.py` → `ORDER BY last_played DESC` in `get_recent()`
  - Label text confirmed as misleading by MASTER_PLAN section 0.15
- **Affected Files:** `web/static/index.html` (label text) or `web/static/js/render/tabs.js` (if rendered dynamically)
- **Dependencies:** None
- **Acceptance Criteria:**
  - Section label reads "Terakhir Diputar" (or equivalent accurate text)
  - No other semantically incorrect labels in Discover tab
- **Verification Steps:**
  1. `grep -n "New Release" web/static/index.html web/static/js/render/tabs.js`
  2. Change to "Terakhir Diputar"
  3. Open Discover tab → correct label visible
- **Risk:** None
- **Estimated Impact:** Correctness; UX honesty

---

### S0-16

- **ID:** S0-16
- **Title:** Add event listeners to mood cards in Discover tab
- **Type:** Bug
- **Priority:** High
- **Status:** Done
- **Description:** Mood cards in the Discover tab are purely decorative — no click/tap handler exists. `grep "mood-card" web/static/js/events.js` returns 0 results. Tapping a mood card does nothing.
- **Evidence:**
  - `grep -n "mood-card" web/static/js/events.js` → 0 results
  - `grep -n "mood-card" web/static/index.html` → cards exist in HTML
- **Affected Files:** `web/static/js/events.js`
- **Dependencies:** `switchTab()` must be accessible; search input must be settable
- **Acceptance Criteria:**
  - Tapping "Chill" card → switches to Search tab, pre-fills search input with "chill music"
  - Tapping "Romantic" card → Search tab, "romantic music"
  - Tapping "Energetic" card → Search tab, "energetic music"
  - Search executes automatically after tab switch (or user can see the pre-filled query)
- **Verification Steps:**
  1. Tap each mood card → Search tab opens with correct pre-filled query
  2. `grep -n "mood-card" web/static/js/events.js` → ≥1 result after implementation
- **Risk:** Low
- **Estimated Impact:** Discover tab becomes functional entry point for discovery

---

### S0-17

- **ID:** S0-17
- **Title:** Remove or implement "See All" / "Lihat Semua" links in Discover
- **Type:** Bug
- **Priority:** Medium
- **Status:** Done
- **Description:** "See all" / "Lihat Semua" links in the Discover tab have no event listener. `grep "see-all\|seeAll\|Lihat Semua" web/static/js/events.js` returns 0 results. Tapping them does nothing.
- **Evidence:**
  - `grep -n "see-all\|Lihat Semua" web/static/index.html` → links exist (no results found in search above; if HTML uses different text, re-verify with `grep -n "Lihat" web/static/index.html`)
  - `grep -n "see-all\|seeAll" web/static/js/events.js` → 0 results
- **Affected Files:** `web/static/index.html`, `web/static/js/events.js`
- **Dependencies:** S8-07 (full pagination) if implementing; otherwise remove links
- **Acceptance Criteria (Remove approach):**
  - No dead "See All" links visible to users
- **Acceptance Criteria (Implement minimal approach):**
  - Clicking expands the list to show all available items in that category
- **Verification Steps:**
  1. Re-verify with `grep -n "Lihat\|see.all" web/static/index.html` to find exact element
  2. Either add listener or remove element
  3. No dead interactive elements in Discover tab
- **Risk:** Low
- **Estimated Impact:** Eliminates dead UI; UX clarity

---

### S0-18

- **ID:** S0-18
- **Title:** Reset radio queue scroll position after "Acak Artis"
- **Type:** Bug
- **Priority:** Low
- **Status:** Done
- **Description:** After tapping "Acak Artis" and radio queue re-renders, `#radio-queue-list` scroll position is not reset. User remains scrolled to wherever they were in the old list.
- **Evidence:**
  - `grep -n "scrollTop" web/static/js/render/tabs.js web/static/js/events.js` → 0 results
  - `grep -n "radioRandomizeBtn" web/static/js/events.js` → line 176: `wsSend("radio_randomize")` with no `scrollTop` reset
- **Affected Files:** `web/static/js/events.js`
- **Dependencies:** S0-09 (if Acak Artis button is removed, this is moot)
- **Acceptance Criteria:**
  - After radio randomize, `dom.radioQueueList.scrollTop = 0` is set
  - Radio queue list scrolls back to top after each randomize
- **Verification Steps:**
  1. Scroll radio queue to bottom
  2. Tap "Acak Artis"
  3. List scrolls back to top
- **Risk:** None
- **Estimated Impact:** UX polish

---

### S0-19

- **ID:** S0-19
- **Title:** Differentiate `rt-sub` text for LOADING/PLAYING states
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** `renderRadio()` in `render/tabs.js` lines 244–246 sets `dom.rtSub.textContent` to either `'Menyetel lagu otomatis...'` (radio on) or `'Aktifkan untuk putar otomatis'` (radio off). It does not distinguish between `store.status === 'LOADING'` and `store.status === 'PLAYING'` — so while a track is buffering, the text shows "Menyetel lagu otomatis..." instead of something like "Memuat..." or the actual track title.
- **Evidence:**
  - `sed -n '244,252p' web/static/js/render/tabs.js` → only `isRadio` check, no `store.status` branch
  - `grep -n "store.status" web/static/js/render/tabs.js` → status checked elsewhere (lines 39, 58, 65, 198) but not in `renderRadio()`
- **Affected Files:** `web/static/js/render/tabs.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - `rt-sub` shows "Memuat..." when `store.status === 'LOADING'` and radio is on
  - `rt-sub` shows current track title (or "Menyetel lagu otomatis...") when `store.status === 'PLAYING'`
  - `rt-sub` shows "Aktifkan untuk putar otomatis" when radio is off
- **Verification Steps:**
  1. Throttle network to Slow 3G
  2. Toggle radio on → "Memuat..." visible during buffer
  3. Track starts playing → text changes to track info or "Menyetel..."
- **Risk:** Low
- **Estimated Impact:** Better feedback during loading; UX polish

---

### S0-20

- **ID:** S0-20
- **Title:** Fix or remove empty `home-header` on mobile
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** `index.html` lines 88–93 render a `<header class="home-header">` containing two empty `<div>` elements. CSS hides it at small breakpoints (`display: none !important` at layout.css lines 220 and 303), but the header may be visible at mid-range breakpoints consuming vertical space. Even if hidden everywhere, the empty markup should be resolved.
- **Evidence:**
  - `sed -n '88,96p' web/static/index.html` → header contains `<div></div>` and `<div style="display:flex; align-items:center; gap:8px;"></div>` — empty
  - `grep -n "home-header" web/static/css/layout.css` → lines 220, 303: `display: none !important`
- **Affected Files:** `web/static/index.html`, optionally `web/static/css/layout.css`
- **Dependencies:** None
- **Acceptance Criteria:**
  - Either: header is populated with branding (`.home-brand` / `.home-greeting` classes that have CSS)
  - Or: header element removed from HTML and all CSS references cleaned up
  - No empty space consumed in the home tab layout
- **Verification Steps:**
  1. Test at iPhone SE (375px) — no unexplained gap above content
  2. Test at 768px — no unexplained gap
  3. If removing: `grep -n "home-header" web/static/index.html` → 0 results
- **Risk:** Low
- **Estimated Impact:** Vertical space reclaimed on home tab

---

### S0-21

- **ID:** S0-21
- **Title:** Add `prefers-reduced-motion` block to disable infinite animations
- **Type:** Technical Debt
- **Priority:** High
- **Status:** Done
- **Description:** No CSS file in the project contains any `@media (prefers-reduced-motion: reduce)` rule. At least 10+ infinite CSS animations exist (`fm-spin` for vinyl, `eq-bounce` for equalizer, `ambientDrift`, `idle-text-fade`, `pulse-antenna`, `pulse-live`, `bounce-wave-*`, `transmit-radio`). Users with vestibular disorders or motion sensitivity get no accommodation. This violates WCAG 2.1 Success Criterion 2.3.3.
- **Evidence:**
  - `grep -rn "prefers-reduced-motion" web/static/` → 0 results
  - `grep -rn "@keyframes" web/static/css/` → multiple animation definitions confirmed
- **Affected Files:** `web/static/css/base.css` (short term); `web/static/css/base/animations.css` (after Sprint 1)
- **Dependencies:** None (can be added immediately; Sprint 1 will move animations to `base/animations.css`)
- **Acceptance Criteria:**
  - `@media (prefers-reduced-motion: reduce)` block exists that stops all infinite animations
  - With OS "Reduce Motion" enabled: vinyl does not spin, equalizer does not bounce, ambient does not drift
  - With "Reduce Motion" disabled: all animations run normally
- **Verification Steps:**
  1. Enable "Reduce Motion" in OS accessibility settings (or DevTools media emulation)
  2. Open app → all infinite animations stopped
  3. Disable "Reduce Motion" → animations resume
- **Risk:** Low
- **Estimated Impact:** Accessibility compliance; eliminates motion sickness risk for users

---

### S0-22

- **ID:** S0-22
- **Title:** Add vertical-scroll guard to swipe gesture handler in main.js
- **Type:** Bug
- **Priority:** Medium
- **Status:** Done
- **Description:** The touch swipe handler in `main.js` only checks `Math.abs(touchEndX - touchStartX) > 80` for horizontal swipe detection. No `deltaY` comparison exists. When scrolling a long list (queue, discover) at a slight diagonal angle, the gesture can be misread as a tab-switch swipe.
- **Evidence:**
  - `sed -n '70,92p' web/static/js/main.js` → only `touchStartX` tracked; `deltaX > 80` check only; no `deltaY` or `touchStartY`
  - `let touchStartX = 0` on line 72; no `touchStartY` variable
- **Affected Files:** `web/static/js/main.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - Swipe is only recognized when `Math.abs(deltaX) > 80 && Math.abs(deltaX) > Math.abs(deltaY) * 1.5`
  - `touchStartY` tracked alongside `touchStartX`
  - Vertical scrolling in queue and discover lists does not accidentally trigger tab switch
- **Verification Steps:**
  1. Scroll down in a long queue list with a slightly diagonal gesture → no tab switch
  2. Horizontal swipe left/right → tab switch still works
- **Risk:** Low
- **Estimated Impact:** Eliminates accidental tab-switch during vertical scroll; critical for discover and queue UX

---

### S0-23

- **ID:** S0-23
- **Title:** Remove duplicate `.pb-ctrl .pb-sec` from `base.css`
- **Type:** Refactor
- **Priority:** Low
- **Status:** Done
- **Description:** `.pb-ctrl .pb-sec { order: 2; ... }` appears at both line 167 and line 365 in `base.css`. This is part of the broader duplication in S0-01 but is worth tracking explicitly since REFACTOR_PLAN lists it separately as BUG-CSS-04.
- **Evidence:**
  - `grep -n "pb-ctrl .pb-sec" web/static/css/base.css` → lines 167 and 365
- **Affected Files:** `web/static/css/base.css`
- **Dependencies:** S0-01 (block deletion in S0-01 should eliminate this; verify after S0-01 is done)
- **Acceptance Criteria:**
  - `grep -c "pb-ctrl .pb-sec" web/static/css/base.css` returns `1`
- **Verification Steps:**
  - After S0-01 is complete, run `grep -c "pb-ctrl .pb-sec" web/static/css/base.css` — should return `1`
  - If still `2`, delete the second occurrence manually
- **Risk:** None
- **Estimated Impact:** Avoids rule conflict; subsumed by S0-01

---

### S0-24

- **ID:** S0-24
- **Title:** Use `home-recent-item` class only for Home tab; rename radio queue item class
- **Type:** Bug
- **Priority:** Medium
- **Status:** Done
- **Description:** `render/tabs.js` uses `home-recent-item` as the class for both Home tab recent items AND radio queue items. Lines 313 and 347 set `div.className = "home-recent-item"` in radio queue rendering context. This class collision means Home-specific CSS styling bleeds into Radio queue items.
- **Evidence:**
  - `grep -n "home-recent-item" web/static/js/render/tabs.js` → lines 203, 313, 347, 416, 435
  - Lines 313 and 347 are in radio queue context (inside `renderList` called with `isRadioList = true`)
- **Affected Files:** `web/static/js/render/tabs.js`, `web/static/css/components.css` (add new class)
- **Dependencies:** None
- **Acceptance Criteria:**
  - Radio queue items use class `radio-queue-item` (new class)
  - `home-recent-item` used only for Home tab recent history items
  - CSS for `radio-queue-item` is self-contained (copy/adapt from `home-recent-item` if needed)
  - Visual appearance of both lists unchanged
- **Verification Steps:**
  1. `grep -n "home-recent-item" web/static/js/render/tabs.js` after fix → only in non-radio contexts
  2. Home recent items and Radio queue items both render correctly
  3. Styling changes to `home-recent-item` do not affect radio queue
- **Risk:** Medium — requires verifying all render paths in `renderList()`
- **Estimated Impact:** Eliminates CSS class collision; enables independent styling of home vs radio lists

---

## SPRINT 1 — CSS Base Layer

> Prerequisite: All Sprint 0 tasks complete and stable.  
> Do NOT start Sprint 1 until Sprint 0 passes the full regression matrix in AI_PLAYBOOK.md.

---

### S1-01

- **ID:** S1-01
- **Title:** Create `web/static/css/base/` folder and extract reset styles
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Extract CSS reset rules (box-sizing, margin/padding 0, body defaults) from `base.css` into `web/static/css/base/reset.css`.
- **Evidence:** `base.css` confirmed at 617 lines (post S0-01 will be ~300); reset block exists at top of file
- **Affected Files:** `web/static/css/base.css` (source), `web/static/css/base/reset.css` (new), `web/static/index.html` (add `<link>`)
- **Dependencies:** S0-01 (base.css must be clean first)
- **Acceptance Criteria:**
  - `web/static/css/base/reset.css` exists with box-sizing, margin/padding reset, body defaults
  - Content removed from `base.css`
  - `index.html` loads `base/reset.css` before other base files
  - Visual regression: no change to any UI element appearance
- **Verification Steps:**
  1. `grep -n "box-sizing" web/static/css/base.css` → 0 results after move
  2. Full cross-browser visual check at all breakpoints
- **Risk:** Low
- **Estimated Impact:** Establishes clean base layer architecture

---

### S1-02

- **ID:** S1-02
- **Title:** Extract typography helpers to `base/typography.css`
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Extract font-face declarations, type scale helpers, and text utility classes from `base.css` into `web/static/css/base/typography.css`.
- **Evidence:** `base.css` contains typography rules; confirmed by inspection
- **Affected Files:** `web/static/css/base.css`, `web/static/css/base/typography.css` (new), `web/static/index.html`
- **Dependencies:** S1-01
- **Acceptance Criteria:**
  - `base/typography.css` contains all type-related rules
  - No type rules remain in `base.css`
  - Fonts render correctly in all tabs
- **Verification Steps:**
  1. `grep -n "font-family\|font-size\|letter-spacing" web/static/css/base.css` → 0 results after move
  2. Visual check: all text renders with correct Inter font and sizing
- **Risk:** Low
- **Estimated Impact:** Typographic concerns isolated; easier to update font stack

---

### S1-03

- **ID:** S1-03
- **Title:** Extract all `@keyframes` to `base/animations.css` with `prefers-reduced-motion` block
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Extract all `@keyframes` declarations from `base.css` (fm-spin, eq-bounce, lyric-pop, idle-text-fade, ambientDrift) into `web/static/css/base/animations.css`. Simultaneously apply the `prefers-reduced-motion` fix from S0-21 in the same file. For `idle-text-fade`, apply the `will-change: transform, opacity` fix or remove `filter: blur()` per-frame as noted in MASTER_PLAN Sprint 1 step 3.
- **Evidence:**
  - `@keyframes` in `base.css` confirmed; `prefers-reduced-motion` absent confirmed (S0-21)
  - `idle-text-fade` uses non-composited properties per MASTER_PLAN Sprint 1 note
- **Affected Files:** `web/static/css/base.css`, `web/static/css/base/animations.css` (new), `web/static/index.html`
- **Dependencies:** S0-21, S1-02
- **Acceptance Criteria:**
  - `base/animations.css` contains all `@keyframes` + `prefers-reduced-motion` block
  - `@keyframes` removed from `base.css`
  - `idle-text-fade` animation is GPU-compositable (no `filter: blur()` per-frame, or `will-change` added)
  - With "Reduce Motion" on: all infinite animations stop
  - Vinyl spin, equalizer bounce, lyric pop all work normally when "Reduce Motion" off
- **Verification Steps:**
  1. `grep -n "@keyframes" web/static/css/base.css` → 0 results after move
  2. OS-level Reduce Motion on → animations stop
  3. Vinyl spins normally on Home tab when Reduce Motion off
- **Risk:** Medium — `idle-text-fade` GPU fix must be tested on budget Android/iPhone
- **Estimated Impact:** All animations centralized; accessibility compliance

---

### S1-04

- **ID:** S1-04
- **Title:** Update `index.html` CSS `<link>` order for new base/ structure
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Update `index.html` to load the new `base/reset.css`, `base/typography.css`, `base/animations.css` in place of (or before) the original `base.css`. Follow the load order defined in `REFACTOR_PLAN.md` section 2.1.
- **Evidence:** Current `index.html` CSS load order confirmed via `grep -n "<link" web/static/index.html`
- **Affected Files:** `web/static/index.html`
- **Dependencies:** S1-01, S1-02, S1-03
- **Acceptance Criteria:**
  - `tokens.css` → `base/reset.css` → `base/typography.css` → `base/animations.css` → remaining CSS
  - No double-loading of any rule
  - Full visual regression passes
- **Verification Steps:**
  1. `grep -n "<link rel=\"stylesheet\"" web/static/index.html` → confirm correct order
  2. Full regression matrix from AI_PLAYBOOK.md
- **Risk:** Medium — wrong load order causes cascade failures
- **Estimated Impact:** Foundation for Sprint 2 and 3 CSS restructure

---

## SPRINT 2 — CSS Platform Layer

> Prerequisite: Sprint 1 complete and all breakpoints visually verified.

---

### S2-01

- **ID:** S2-01
- **Title:** Create `web/static/css/platform/` and consolidate all `@media` queries
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Collect ALL `@media` blocks from `base.css`, `layout.css`, `tabs.css`, `components.css`, `player.css` and consolidate them into `platform/mobile.css`, `platform/tablet.css`, `platform/desktop.css`, `platform/landscape.css`, `platform/safe-area.css`. Resolve the `@media (min-width: 1024px)` triplication in `layout.css` (lines 34, 412, 451) into a single `platform/desktop.css` block. Final `.vol-grp` rule lives only in `platform/desktop.css` (from S0-04 decision).
- **Evidence:**
  - `grep -n "min-width: 1024px" web/static/css/layout.css` → lines 34, 412, 451
  - `grep -rn "@media" web/static/css/` → media queries scattered across all files
- **Affected Files:** All CSS files, `web/static/index.html`
- **Dependencies:** S0-04 (vol-grp resolved), S1-04
- **Acceptance Criteria:**
  - Zero `@media` blocks remain in `components/` files (after Sprint 3)
  - Single `@media (min-width: 1024px)` block in `platform/desktop.css`
  - All five platform files exist with correct breakpoint content
  - Full regression at every breakpoint in AI_PLAYBOOK regression matrix
- **Verification Steps:**
  - After completion: `grep -rn "@media" web/static/css/components/` → 0 results
  - Each platform file contains only rules for its breakpoint
  - Test all device sizes from AI_PLAYBOOK regression matrix
- **Risk:** High — most risky sprint; every breakpoint must be tested
- **Estimated Impact:** Eliminates all media query conflicts; single source of truth per platform

---

## SPRINT 3 — CSS Components Split

> Prerequisite: Sprint 2 complete.

---

### S3-01

- **ID:** S3-01
- **Title:** Split `components.css` (1170 lines) into component files
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Split `web/static/css/components.css` (1170 lines confirmed) into: `queue.css`, `search.css`, `settings-sheet.css`, `lyrics.css`, `cards.css`, `toasts.css`. Each file contains only mobile-first default styles for that component. No `@media` queries (moved to Sprint 2 platform files).
- **Evidence:** `wc -l web/static/css/components.css` → 1170 lines confirmed
- **Affected Files:** `web/static/css/components.css`, new component files, `web/static/index.html`
- **Dependencies:** S2-01
- **Acceptance Criteria:**
  - 8 component CSS files created
  - `components.css` empty or deleted
  - `index.html` references updated
  - `grep -rn "components.css" web/static/index.html` → 0 results
  - Full visual regression
- **Verification Steps:** Full regression matrix per AI_PLAYBOOK
- **Risk:** Medium
- **Estimated Impact:** Maintainable CSS; each feature owned by one file

---

### S3-02

- **ID:** S3-02
- **Title:** Split `player.css` (556 lines) into `player-bar.css` and `player-controls.css`
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Split `web/static/css/player.css` (556 lines confirmed) into `components/player-bar.css` (player bar container, progress, seek) and `components/player-controls.css` (btn-prev, btn-next, btn-shuffle, btn-repeat, btn-play).
- **Evidence:** `wc -l web/static/css/player.css` → 556 lines confirmed
- **Affected Files:** `web/static/css/player.css`, new files, `web/static/index.html`
- **Dependencies:** S2-01, S3-01
- **Acceptance Criteria:**
  - `player.css` empty or deleted; `grep -rn "player.css" web/static/index.html` → 0 results
  - Player bar and all controls render correctly
- **Verification Steps:** Visual check of player bar at all breakpoints
- **Risk:** Medium
- **Estimated Impact:** Player concerns cleanly separated

---

### S3-03

- **ID:** S3-03
- **Title:** Split `layout.css` into `layout/app-shell.css` + `layout/nav.css` + `layout/grid.css`; merge `tabs.css` into `layout/nav.css`
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Split `layout.css` into three layout files. Merge `tabs.css` into `layout/nav.css` per MASTER_PLAN. Delete `base.css`, `layout.css`, `components.css`, `player.css`, `tabs.css` after confirming all content is migrated.
- **Evidence:** Layout and tabs files confirmed; content verified in Sprint 1–2 work
- **Affected Files:** All legacy CSS files, `web/static/index.html`
- **Dependencies:** S3-01, S3-02
- **Acceptance Criteria:**
  - `grep -rn "base.css\|layout.css\|components.css\|player.css\|tabs.css" web/static/index.html` → 0 results
  - Full regression matrix passes
- **Verification Steps:** Run every check in AI_PLAYBOOK regression matrix
- **Risk:** High — final deletion step; ensure all content migrated first
- **Estimated Impact:** Legacy CSS files fully replaced; clean modular structure

---

## SPRINT 4 — JS Services & Platform Split

> Prerequisite: Sprint 3 complete.

---

### S4-01

- **ID:** S4-01
- **Title:** Extract auth logic from `events.js` into `services/auth.js`
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Move login, logout, and `applyRoleUI` logic from `events.js` and `portal.js` into a new `web/static/js/services/auth.js` file. `portal.js` may remain as the UI layer calling auth service.
- **Evidence:** `grep -n "login\|logout\|applyRoleUI" web/static/js/events.js` — auth logic confirmed in events.js
- **Affected Files:** `web/static/js/events.js`, `web/static/js/portal.js`, new `web/static/js/services/auth.js`, `web/static/index.html`
- **Dependencies:** S0-07 (safeStorage must exist before refactoring localStorage-using auth code)
- **Acceptance Criteria:**
  - Auth logic in `services/auth.js`
  - Login/logout cycle works correctly
  - `applyRoleUI()` applies correct role-based UI
- **Verification Steps:** Login as admin → full controls visible; login as client → view-only; logout → portal shown
- **Risk:** Medium
- **Estimated Impact:** Separation of auth concerns

---

### S4-02

- **ID:** S4-02
- **Title:** Extract swipe gesture + audio unlock to `platform/touch.js` with vertical-scroll guard
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Move `touchstart`/`touchend` swipe handler from `main.js` and audio unlock `touchstart` listener from `audio.js` into `web/static/js/platform/touch.js`. Simultaneously apply the S0-22 deltaY guard in the new file. This consolidates all touch-platform logic.
- **Evidence:**
  - Swipe handler at `main.js` lines 72–87 (touchStartX, touchEnd handler)
  - Audio unlock: `grep -n "touchstart" web/static/js/audio.js` — confirms mobile audio unlock listener
- **Affected Files:** `web/static/js/main.js`, `web/static/js/audio.js`, new `web/static/js/platform/touch.js`, `web/static/index.html`
- **Dependencies:** S0-22 (guard logic defined), S4-01
- **Acceptance Criteria:**
  - `platform/touch.js` contains all touch event listeners
  - `main.js` and `audio.js` have no `touchstart`/`touchend` listeners
  - Swipe navigation works; vertical scroll does not trigger tab switch
  - Audio unlocks on mobile on first touch
- **Verification Steps:**
  1. Swipe left/right → tabs switch
  2. Scroll down in queue → no tab switch
  3. Open on mobile → audio plays without requiring extra tap
- **Risk:** Medium
- **Estimated Impact:** All mobile touch handling in one place

---

### S4-03

- **ID:** S4-03
- **Title:** Extract keyboard shortcuts + `pointer: fine` guard to `platform/keyboard.js`
- **Type:** Refactor
- **Priority:** Medium
- **Status:** Done
- **Description:** Move keyboard shortcut event listeners from `events.js` (around line 700, inside `if (window.matchMedia('(pointer: fine)').matches)` block) into `web/static/js/platform/keyboard.js`.
- **Evidence:**
  - `grep -n "pointer.*fine\|matchMedia" web/static/js/events.js` → lines 699–700
- **Affected Files:** `web/static/js/events.js`, new `web/static/js/platform/keyboard.js`, `web/static/index.html`
- **Dependencies:** S4-01
- **Acceptance Criteria:**
  - Keyboard shortcuts work on desktop (pointer: fine)
  - Keyboard shortcuts do not fire on touch devices
  - `events.js` has no `matchMedia('pointer: fine')` block
- **Verification Steps:**
  1. Desktop: keyboard shortcuts functional
  2. Mobile: keyboard shortcuts do not fire accidentally
- **Risk:** Low
- **Estimated Impact:** Platform-specific code isolated

---

### S4-04

- **ID:** S4-04
- **Title:** Extract `visualViewport` resize handler to `platform/viewport.js`
- **Type:** Refactor
- **Priority:** Low
- **Status:** Done
- **Description:** Move `visualViewport` resize listener (for virtual keyboard handling on mobile) from `main.js` into `web/static/js/platform/viewport.js`.
- **Evidence:** `grep -n "visualViewport" web/static/js/main.js` — handler confirmed
- **Affected Files:** `web/static/js/main.js`, new `web/static/js/platform/viewport.js`, `web/static/index.html`
- **Dependencies:** S4-02
- **Acceptance Criteria:**
  - Virtual keyboard on mobile does not break layout
  - `main.js` has no `visualViewport` reference
- **Verification Steps:** Focus search input on mobile → layout adjusts correctly around keyboard
- **Risk:** Low
- **Estimated Impact:** Clean main.js entry point

---

### S4-05

- **ID:** S4-05
- **Title:** Update `index.html` JS `<script>` load order for platform/ and services/ structure
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Update `index.html` script load order to match the new structure defined in `REFACTOR_PLAN.md` section 2.2. Current load order (confirmed lines 615–627) does not include `services/` or `platform/` paths.
- **Evidence:** `grep -n "<script" web/static/index.html` → lines 615–627: current order without new paths
- **Affected Files:** `web/static/index.html`
- **Dependencies:** S4-01, S4-02, S4-03, S4-04
- **Acceptance Criteria:**
  - Load order: config → store → dom → utils → services/* → render/* → events/* → platform/* → main
  - All features functional after reorder
- **Verification Steps:** Full regression matrix from AI_PLAYBOOK
- **Risk:** Medium — wrong script order breaks initialization
- **Estimated Impact:** Correct dependency resolution

---

## SPRINT 5 — JS Events Split

> Prerequisite: Sprint 4 complete.

---

### S5-01

- **ID:** S5-01
- **Title:** Split `events.js` (720 lines) into `events/` folder
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Split `web/static/js/events.js` (720 lines confirmed) into: `events/player-events.js`, `events/queue-events.js`, `events/lyrics-events.js`, `events/settings-events.js`, `events/index.js`. `events/index.js` exports `initEvents()` calling all sub-modules. Ensure S0-06 mini player tap-to-home listener is present in `player-events.js`.
- **Evidence:** `wc -l web/static/js/events.js` → 720 lines confirmed
- **Affected Files:** `web/static/js/events.js`, new `events/` folder, `web/static/index.html`
- **Dependencies:** S4-01 (auth logic already removed), S4-02 (touch logic removed), S4-03 (keyboard logic removed), S0-06 must be done
- **Acceptance Criteria:**
  - `events.js` deleted; `grep -rn "events.js" web/static/index.html` → 0 results
  - All player controls, queue drag, lyrics offset, settings, favorite interactions work
  - Mini player tap-to-home present in `player-events.js`
- **Verification Steps:** Full interactive test of every button and gesture
- **Risk:** High — all event binding being reorganized; test every interaction
- **Estimated Impact:** events.js concern split; each event domain independently maintainable

---

## SPRINT 6 — JS Render Split

> Prerequisite: Sprint 5 complete.

---

### S6-01

- **ID:** S6-01
- **Title:** Split `render/tabs.js` (455 lines) into render sub-modules
- **Type:** Refactor
- **Priority:** High
- **Status:** Done
- **Description:** Split `web/static/js/render/tabs.js` (455 lines confirmed) into: `render/now-playing.js` (renderNowPlaying, cover art, ambient color), `render/queue.js` (renderQueue, renderRadioQueue — using new `radio-queue-item` class from S0-24), `render/discover.js` (renderDiscoverTab, renderRadio), `render/favorites.js` (renderFavorites). Verify S0-16/S0-17 mood card and see-all fixes are present in `render/discover.js`.
- **Evidence:** `wc -l web/static/js/render/tabs.js` → 455 lines confirmed
- **Affected Files:** `web/static/js/render/tabs.js`, new render files, `web/static/index.html`
- **Dependencies:** S5-01, S0-16, S0-17, S0-24
- **Acceptance Criteria:**
  - `render/tabs.js` deleted; `grep -rn "render/tabs.js" web/static/index.html` → 0 results
  - All four tabs render correctly
  - `radio-queue-item` class used in `render/queue.js` (not `home-recent-item`)
- **Verification Steps:** Open every tab; trigger full state render; verify all content appears correctly
- **Risk:** High — all render logic reorganized; all tabs must be tested
- **Estimated Impact:** Render modules independently maintainable per feature

---

## SPRINT 7 — Backend Cleanup

> Prerequisite: Sprint 6 complete. Run `pytest tests/` before and after every step.

---

### S7-01

- **ID:** S7-01
- **Title:** Extract inline event listeners from `server/app.py` to `server/handlers/event_listeners.py`
- **Type:** Refactor
- **Priority:** Medium
- **Status:** Done
- **Description:** `server/app.py` (172 lines) contains `_on_track_started` and related event bus subscriber closures defined inline (line 46: `async def _on_track_started(event: TrackStartedEvent)`). These belong in `server/handlers/event_listeners.py` (new file). `app.py` should only contain `create_app()`, route setup, and dependency injection.
- **Evidence:**
  - `grep -n "_on_track_started\|_on_progress" server/app.py` → line 46 and 136
  - `wc -l server/app.py` → 172 lines
- **Affected Files:** `server/app.py`, new `server/handlers/event_listeners.py`
- **Dependencies:** None; run `pytest tests/` before and after
- **Acceptance Criteria:**
  - `server/handlers/event_listeners.py` contains all event subscriber functions
  - `app.py` has no inline `def _on_*` closures
  - `pytest tests/` passes before and after
  - Playback events (TrackStarted, Progress) still broadcast correctly over WS
- **Verification Steps:**
  1. `pytest tests/` before change
  2. Move functions, update `app.py` imports and subscriptions
  3. `pytest tests/` after change
  4. Manual: play a track → progress messages arrive in client
- **Risk:** Medium — event bus subscriptions must be correctly re-wired
- **Estimated Impact:** `app.py` becomes pure routing; event handling separated

---

### S7-02

- **ID:** S7-02
- **Title:** Extract stream prefetch and broadcast logic from `app.py` to `services/`
- **Type:** Refactor
- **Priority:** Low
- **Status:** Done
- **Description:** Create `services/stream_prefetch.py` and `services/broadcast_service.py` to hold any stream pre-fetch logic and WebSocket broadcast helpers extracted from `app.py`. `app.py` must contain no business logic.
- **Evidence:** `server/app.py` line count 172; inline logic confirmed per MASTER_PLAN Sprint 7
- **Affected Files:** `server/app.py`, new `services/stream_prefetch.py`, new `services/broadcast_service.py`
- **Dependencies:** S7-01; `pytest tests/` required
- **Acceptance Criteria:**
  - `app.py` < 80 lines (routing + DI only)
  - `pytest tests/` passes
  - WS broadcast still works
- **Verification Steps:**
  1. `pytest tests/` before/after
  2. Connect client → receive state messages → broadcast functional
- **Risk:** Medium
- **Estimated Impact:** `app.py` pure routing; services layer expanded

---

### S7-03

- **ID:** S7-03
- **Title:** Split `engine/playback_controller.py` (352 lines) into `engine/playback/` subpackage
- **Type:** Refactor
- **Priority:** Medium
- **Status:** Done
- **Description:** Split `engine/playback_controller.py` (352 lines confirmed) into `engine/playback/controller.py` (orchestrator/state machine), `engine/playback/track_loader.py` (URL resolution, cache check). Note: `engine/command_router.py` already exists at `engine/` level (not in a subdir) — verify actual location with `ls engine/` before deciding whether to move it into `engine/playback/`.
- **Evidence:**
  - `wc -l engine/playback_controller.py` → 352 lines confirmed
  - `ls engine/` confirms `command_router.py` at engine/ root (not in subdir)
- **Affected Files:** `engine/playback_controller.py`, new `engine/playback/` package, all files importing `playback_controller`
- **Dependencies:** S7-01, S7-02; `pytest tests/` required at every step
- **Acceptance Criteria:**
  - `engine/playback_controller.py` removed or empty
  - `pytest tests/` passes before and after each split
  - Playback state machine works: IDLE → LOADING → PLAYING → PAUSED → IDLE
- **Verification Steps:**
  1. `pytest tests/` before
  2. Create `engine/playback/__init__.py`
  3. Split file, update all imports
  4. `pytest tests/` after each sub-step
  5. Manual playback test: play, pause, next, prev all work
- **Risk:** High — core playback state machine; `pytest` is the safety net
- **Estimated Impact:** Playback controller maintainable; state machine isolated from I/O

---

## SPRINT 8 — Feature Gap Fixes

> Prerequisite: All Sprint 0 bugs resolved. Sprint 7 not required to start Sprint 8.  
> These are new features or broken features requiring product decisions.

---

### S8-01

- **ID:** S8-01
- **Title:** Implement `seed_artist` filtering in `db.py::get_random_songs()` and `radio_engine.py`
- **Type:** Feature
- **Priority:** High
- **Status:** Done
- **Description:** `get_random_songs()` in `cache/db.py` (line 199) has no artist parameter. `radio_engine.py::_gather_batch()` accepts `prioritized_artist` but explicitly ignores it (line 311 comment). Implement artist filtering: add `artist` parameter to `get_random_songs()`, apply `WHERE artist = ?` (or weighted selection), and pass `seed_artist` from `_gather_batch()`. Frontend must also send `seed_artist` payload in `wsSend("radio_randomize")` call in `events.js` line 186.
- **Evidence:**
  - `grep -n "def get_random_songs" cache/db.py` → line 199: no artist param
  - `sed -n '308,318p' engine/radio_engine.py` → comment confirms intentional ignore
  - `grep -n "radioRandomizeBtn" web/static/js/events.js` → line 176-186: no seed_artist in payload
- **Affected Files:** `cache/db.py`, `engine/radio_engine.py`, `web/static/js/events.js`
- **Dependencies:** S0-09 (if button retained), `pytest tests/` required
- **Acceptance Criteria:**
  - `get_random_songs(limit, exclude_ids, artist=None)` signature in `db.py`
  - When `artist` provided, query returns tracks matching that artist preferentially
  - Frontend sends `{ seed_artist: selectedArtist }` in `radio_randomize` payload
  - `pytest tests/` passes
- **Verification Steps:**
  1. `pytest tests/` before
  2. Select an artist, trigger radio randomize → queue contains tracks from that artist
  3. `pytest tests/` after
- **Risk:** High — DB query change; requires careful SQL
- **Estimated Impact:** "Acak Artis" feature becomes functional end-to-end

---

### S8-02

- **ID:** S8-02
- **Title:** Implement artist distribution guarantee in radio batch (`PARTITION BY artist_id`)
- **Type:** Feature
- **Priority:** High
- **Status:** Done
- **Description:** `get_random_songs()` returns fully random tracks with no artist distribution guarantee. A single batch of 12 songs may contain 12 tracks from the same artist. Implement SQL `ROW_NUMBER() OVER (PARTITION BY artist ...)` to ensure no more than N tracks per artist per batch.
- **Evidence:**
  - `grep -n "def get_random_songs" cache/db.py` → line 199: pure `ORDER BY RANDOM()`, no partition
  - Known limitation documented in AI_PLAYBOOK "Known Limitations": "`get_random_songs()` has no artist filter; `PARTITION BY artist_id` not implemented"
- **Affected Files:** `cache/db.py`
- **Dependencies:** S8-01
- **Acceptance Criteria:**
  - No single artist appears more than `TRACKS_PER_ARTIST_TARGET` times per radio batch
  - `pytest tests/` passes
- **Verification Steps:**
  1. Trigger radio with 100+ tracks in DB → inspect `radio_queue` — no artist repeated >N times
  2. `pytest tests/` passes
- **Risk:** Medium — SQLite window function support requires SQLite ≥3.25.0 (2018); verify runtime version
- **Estimated Impact:** Radio variety improves significantly; avoids repetitive playback

---

### S8-03

- **ID:** S8-03
- **Title:** Add stream URL pre-fetch for radio track transitions
- **Type:** Feature
- **Priority:** Medium
- **Status:** Done
- **Description:** Radio track transitions currently have no pre-fetched stream URL for the next track. Only the current track's URL is resolved. Before a track ends, the next radio queue track's stream URL should be resolved and cached, reducing transition latency.
- **Evidence:**
  - AI_PLAYBOOK "Known Limitations": "No `stream_url` pre-fetch for radio track transitions (only next-queue item prefetched)"
  - `grep -n "prefetch\|pre_fetch\|_standby" engine/radio_engine.py` — verify current standby pattern
- **Affected Files:** `engine/radio_engine.py`, `cache/resolver.py`
- **Dependencies:** S8-01
- **Acceptance Criteria:**
  - When a radio track is 30s from ending, next track's stream URL is pre-fetched and cached
  - Track transitions have noticeably lower latency (no buffering gap > 2s)
- **Verification Steps:**
  1. Play radio, approach end of track
  2. Transition to next track — gap < 2 seconds
  3. `pytest tests/` passes
- **Risk:** Medium — async timing; must not interfere with manual playback
- **Estimated Impact:** Smooth radio transitions; eliminates dead air between tracks

---

### S8-04

- **ID:** S8-04
- **Title:** Add double-tap guard on radio toggle button
- **Type:** Bug
- **Priority:** Medium
- **Status:** Done
- **Description:** Rapidly tapping the radio toggle button can trigger two `wsSend("set_mode", ...)` calls in quick succession, causing a race condition where mode toggles twice and returns to original state (or causes undefined behavior). The current handler at `events.js` line 164 has no guard.
- **Evidence:**
  - `sed -n '162,175p' web/static/js/events.js` → no `store.status === 'LOADING'` or debounce guard
- **Affected Files:** `web/static/js/events.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - Second tap within 500ms of first is ignored
  - Or: guard `if (store.status === 'LOADING') return;` prevents double-send
  - Manual double-tap test: mode toggles once, not twice
- **Verification Steps:**
  1. Rapidly double-tap radio toggle
  2. Mode changes once and stabilizes
- **Risk:** Low
- **Estimated Impact:** Eliminates race condition on radio toggle

---

### S8-05

- **ID:** S8-05
- **Title:** Implement `DiscoverService.get_featured_artists()` using `artists` table data
- **Type:** Feature
- **Priority:** High
- **Status:** Done
- **Description:** `data/artists.json` / `data/artists_enriched.json` contain 2500+ artist records. The `artists` table exists in the DB (per `cache/schema.sql`). Neither the `discover_service.py` nor any query uses this data. New cold-start users see three empty sections. Add `get_featured_artists()` to `DiscoverService` querying the `artists` table; render as a new "Artis Indonesia" section in the Discover tab to provide content even on cold start.
- **Evidence:**
  - AI_PLAYBOOK "Known Limitations": "`artists.json` / `artists_enriched.json` (2500+ records) not used in any live query"
  - `cat services/discover_service.py` → only `get_recent`, `get_favorites`, `get_cached` — no artist query
  - MASTER_PLAN S8.5 confirms this approach
- **Affected Files:** `services/discover_service.py`, `web/static/js/render/tabs.js` (or post-S6 `render/discover.js`)
- **Dependencies:** S8-05 requires `artists` table populated; verify `data/export_to_sqlite.py` populates it
- **Acceptance Criteria:**
  - `DiscoverService.get_featured_artists(n)` returns list of artist records from DB
  - Discover tab shows "Artis Indonesia" section with ≥10 artists on cold start (no play history)
  - Section includes artist name and optionally thumbnail/genre
- **Verification Steps:**
  1. Clear `tracks` table → open Discover tab
  2. "Artis Indonesia" section visible with artists from `artists` table
  3. `pytest tests/` passes
- **Risk:** Medium — requires `artists` table to be populated; verify import script
- **Estimated Impact:** Eliminates cold-start empty state; Discover tab useful from day one

---

### S8-06

- **ID:** S8-06
- **Title:** Add skeleton loading placeholders to Discover tab
- **Type:** Feature
- **Priority:** Medium
- **Status:** Done
- **Description:** The Discover tab shows empty state for 0.5–2 seconds while waiting for the `discover_data` WebSocket response. This appears as a bug (broken empty page) rather than a loading state. Add skeleton placeholder cards that render immediately while data loads.
- **Evidence:**
  - AI_PLAYBOOK Feature Inventory: Discover tab — "no skeleton loading; cold-start empty state" (high risk)
  - MASTER_PLAN S8.6 confirms this issue
- **Affected Files:** `web/static/js/render/tabs.js` (or `render/discover.js` post-S6), `web/static/css/components.css` (skeleton animation)
- **Dependencies:** S0-21 (reduced-motion must already handle skeleton animation)
- **Acceptance Criteria:**
  - Skeleton cards visible immediately on Discover tab open, before WS response
  - Skeletons replaced by real content when `discover_data` message arrives
  - With "Reduce Motion" on: skeleton uses static placeholder (no animation)
- **Verification Steps:**
  1. Throttle WS to introduce 1s delay
  2. Open Discover tab → skeleton visible for 1s
  3. Data arrives → skeletons replaced by content
- **Risk:** Low
- **Estimated Impact:** Eliminates empty-state-looks-like-a-bug UX issue

---

### S0-17

- **ID:** S0-17
- **Title:** Implement/remove "See All" links in Discover tab
- **Type:** Polish
- **Priority:** Low
- **Status:** Done
- **Description:** Discover sections (Recent, Favorites, Cached) show a limited number of items with no "load more" or "see all" functionality. Implement either a "Lihat Semua" button that expands the list, or infinite scroll.
- **Evidence:**
  - AI_PLAYBOOK "Known Limitations": "No pagination or 'load more' in Discover"
  - S0-17 (see-all links dead) is the immediate bugfix; this is the full implementation
- **Affected Files:** `services/discover_service.py`, `web/static/js/render/tabs.js`, `web/static/js/events.js`
- **Dependencies:** S0-17
- **Acceptance Criteria:**
  - User can view all recent/favorite/cached tracks beyond initial limit
  - Expand happens without full page reload (in-place list expansion or tab-based)
- **Verification Steps:** Add 20+ tracks to play history → Discover shows initial N → expand shows all
- **Risk:** Low
- **Estimated Impact:** Full library browseable from Discover

---

### S8-08

- **ID:** S8-08
- **Title:** Add progress bar to mini player (non-home tabs)
- **Type:** Feature
- **Priority:** Medium
- **Status:** Done
- **Description:** When on a non-home tab, `#player-bar` shows as a mini player with track info but no progress bar. Users cannot see playback position. Add a thin (2px) progress bar using `::before` pseudo-element on `#player-bar`, width proportional to `store.position / store.duration`.
- **Evidence:**
  - AI_PLAYBOOK "Known Limitations": "No progress bar in mini player (non-home tabs)"
  - MASTER_PLAN S8.8 confirms this
  - `grep -n "pb-progress" web/static/css/player.css` → progress bar exists for home tab; mini player version absent
- **Affected Files:** `web/static/css/player.css` (or `components/player-bar.css` post-S3), `web/static/js/render/player.js`
- **Dependencies:** None
- **Acceptance Criteria:**
  - Thin progress bar visible at top or bottom of mini player
  - Width updates as `store.position` changes (on each `progress` WS message)
  - Progress bar not visible when `store.status === 'IDLE'` or no track
- **Verification Steps:**
  1. Play a track, switch to Search tab
  2. Progress bar visible in mini player
  3. Bar width increases as track plays
- **Risk:** Low
- **Estimated Impact:** UX improvement; playback awareness without switching to Home

---

### S8-09

- **ID:** S8-09
- **Title:** Add TTL/expiry to `localStorage` cover art cache
- **Type:** Technical Debt
- **Priority:** Medium
- **Status:** Done
- **Description:** `utils.js` caches cover art URLs in `localStorage` indefinitely (no TTL or expiry). Over time, the cache grows without bound, which can fill `localStorage` quota and cause issues (especially with the 5–10MB limit on mobile Safari).
- **Evidence:**
  - `grep -n "TTL\|expir\|ttl\|timestamp" web/static/js/utils.js` → 0 results
  - `grep -n "localStorage" web/static/js/utils.js` → lines 48, 68, 76 (set/get with no expiry)
- **Affected Files:** `web/static/js/utils.js`
- **Dependencies:** S0-07 (safeStorage must be implemented first)
- **Acceptance Criteria:**
  - Each cached cover art entry stores a timestamp alongside the URL
  - Entries older than TTL (e.g., 7 days) are evicted on next access
  - `safeStorage` is used for all operations
- **Verification Steps:**
  1. Set TTL to 1 second for testing
  2. Cache a cover art URL
  3. Wait 1 second
  4. Access cover art → entry evicted, re-fetched
- **Risk:** Low
- **Estimated Impact:** Prevents localStorage bloat; avoids quota errors on long-term users

---

### S8-10

- **ID:** S8-10
- **Title:** Improve ambient color extraction to use most-saturated pixel instead of average
- **Type:** Feature
- **Priority:** Low
- **Status:** Done
- **Description:** `extractDominantColor()` (referenced at `render/tabs.js` line 14 via `window.extractDominantColor`) uses pixel averaging. Dark album covers produce a near-black average, resulting in no visible ambient glow. Replacing with most-saturated-pixel detection would produce vibrant glows even for dark covers.
- **Evidence:**
  - `grep -n "extractDominantColor" web/static/js/render/tabs.js web/static/js/audio.js` → lines 13–14 in tabs.js; implementation location unknown from grep
  - `grep -n "getImageData\|extractDominantColor" web/static/js/audio.js` → implementation likely in audio.js; confirm with `grep -rn "extractDominantColor" web/static/js/`
- **Affected Files:** `web/static/js/audio.js` (or wherever `window.extractDominantColor` is defined)
- **Dependencies:** None
- **Acceptance Criteria:**
  - Dark album covers produce a visible ambient glow using the most saturated color
  - Bright album covers: no regression in glow color quality
- **Verification Steps:**
  1. Play a track with a very dark album cover (e.g., black background)
  2. Home tab ambient glow shows a color (not black/invisible)
- **Risk:** Low
- **Estimated Impact:** Visual polish; Home tab ambient effect works for all album cover types

---

## UNVERIFIED

> Tasks listed here could not be confirmed against source code.  
> Status = UNVERIFIED. Do NOT implement without first verifying.

---

### UV-01

- **ID:** UV-01
- **Title:** `_vizRafId` visualizer loop may also leak when not PLAYING
- **Type:** Bug
- **Priority:** Medium
- **Status:** UNVERIFIED
- **Description:** `audio.js` line 98 shows `_vizRafId = requestAnimationFrame(startVisualizerLoop)`. The `startVisualizerLoop` function checks `store.status !== "PLAYING"` — if it exits, verify whether `_vizRafId` is cancelled or continues to reschedule. Evidence from `sed -n '78,110p' web/static/js/audio.js` not fully examined.
- **Evidence:** `grep -n "_vizRafId" web/static/js/audio.js` → line 98; cancellation not confirmed
- **Affected Files:** `web/static/js/audio.js`
- **Dependencies:** S0-08
- **Verification Steps:** Read full `startVisualizerLoop` implementation; confirm whether it exits cleanly or reschedules when not PLAYING
- **Risk:** UNVERIFIED — may be a duplicate of S0-08 or a separate leak

---

### UV-02

- **ID:** UV-02
- **Title:** `artists` table may not be populated from `artists.json` in production DB
- **Type:** Technical Debt
- **Priority:** High
- **Status:** UNVERIFIED
- **Description:** S8-05 assumes `artists` table is populated. `data/export_to_sqlite.py` and `data/import_artists.py` exist but it is unconfirmed whether the production `data/ytgui.db` has artist records loaded.
- **Evidence:** `data/export_to_sqlite.py` and `data/archive/import_artists.py` exist; DB not inspected
- **Affected Files:** `data/ytgui.db`, `data/export_to_sqlite.py`
- **Verification Steps:** `sqlite3 data/ytgui.db "SELECT COUNT(*) FROM artists;"` — if 0, run import script before S8-05
- **Risk:** S8-05 fails silently if table is empty
- **Estimated Impact:** Blocks S8-05 if not populated

---

### UV-03

- **ID:** UV-03
- **Title:** SQLite version on target device may not support `ROW_NUMBER() OVER (PARTITION BY ...)`
- **Type:** Technical Debt
- **Priority:** High
- **Status:** UNVERIFIED
- **Description:** S8-02 requires SQLite window functions (`ROW_NUMBER() OVER (PARTITION BY artist ...)`). Window functions require SQLite ≥3.25.0 (released 2018). Termux on older Android devices may have older SQLite.
- **Evidence:** Not verified; target platform is Termux/Android
- **Verification Steps:** On target device: `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`; must be ≥3.25.0
- **Risk:** Blocks S8-02 on older devices if SQLite version insufficient
- **Estimated Impact:** May require fallback implementation using Python-side grouping instead of SQL window function

---

### UV-04

- **ID:** UV-04
- **Title:** `tests/integration/test_e2e.py` scope and coverage unknown
- **Type:** Technical Debt
- **Priority:** Medium
- **Status:** UNVERIFIED
- **Description:** `tests/integration/test_e2e.py` exists (confirmed by `ls tests/integration/`) but its content and coverage are not reviewed. Existing tests `test_fase0.py` and `test_fase1.py` cover security/performance (different scope). The e2e test scope is unknown.
- **Evidence:** `ls tests/integration/` → `test_e2e.py`, `test_fase0.py`, `test_fase1.py`
- **Affected Files:** `tests/integration/test_e2e.py`
- **Verification Steps:** `cat tests/integration/test_e2e.py` — review scope before relying on it as regression safety net
- **Risk:** Sprint 7 backend changes may break untested paths if e2e coverage is insufficient
- **Estimated Impact:** Determines whether pytest is adequate safety net for Sprint 7

---

*Last verified: 2026-06-29 against `ytgui-main__1_.zip` (commit hash prefix: 568e8d21)*  
*Primary reference: `AI_PLAYBOOK.md`*  
*Do not rename WS action/response strings. Do not rename `store` keys. Do not start Sprint N+1 before Sprint N is verified stable.*
