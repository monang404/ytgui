# Walkthrough: Sprint 4 — JS Services & Platform Split

Sprint 4 has been successfully completed. This sprint focused on modularizing the frontend JavaScript by extracting specific functionalities into dedicated service and platform files. This architectural improvement makes the codebase cleaner, easier to maintain, and prepares it for further feature development.

## 1. Auth Service Extraction (S4-01)
- **Goal:** Isolate authentication logic from UI and event handling files.
- **Changes:**
  - Created a new file: `web/static/js/services/auth.js`.
  - Moved `applyRoleUI()` and `logout()` functions from `portal.js` to `auth.js`.
  - Moved the `login(user, pass)` logic from `events.js` to `auth.js`.
  - Updated `events.js` to call the abstracted `login()` function when the submit button is clicked.
  - Replaced direct `localStorage` calls with `safeStorage` in `portal.js` and `events.js` for role management, ensuring consistency with previous sprints.

## 2. Platform Touch Module (S4-02)
- **Goal:** Consolidate mobile touch and swipe gesture logic into one platform-specific module.
- **Changes:**
  - Created a new file: `web/static/js/platform/touch.js`.
  - Moved the mobile swipe logic (`touchstart` and `touchend`) for navigating tabs (Next/Prev) from `main.js` to `touch.js`.
  - Moved the audio auto-unlock logic (triggered by `touchstart`) from `audio.js` into the centralized touch event listener in `touch.js`.

## 3. Platform Keyboard Module (S4-03)
- **Goal:** Isolate desktop keyboard shortcuts.
- **Changes:**
  - Created a new file: `web/static/js/platform/keyboard.js`.
  - Moved the `keydown` event listener for desktop keyboard shortcuts (Space, ArrowRight, ArrowLeft) from `events.js`. This logic remains guarded by `window.matchMedia('(pointer: fine)')` to ensure it only runs on desktop environments.

## 4. Platform Viewport Module (S4-04)
- **Goal:** Handle visual viewport resizing efficiently, primarily for mobile virtual keyboards.
- **Changes:**
  - Created a new file: `web/static/js/platform/viewport.js`.
  - Moved the `visualViewport` resize listener from `main.js` to this new dedicated module. This ensures the layout adjusts correctly when the mobile virtual keyboard appears, without cluttering the main initialization file.

## 5. Script Load Order Update (S4-05)
- **Goal:** Ensure all new modular scripts are loaded correctly in the application's HTML.
- **Changes:**
  - Updated `web/static/index.html` to include the newly created scripts (`services/auth.js`, `platform/viewport.js`, `platform/touch.js`, `platform/keyboard.js`).
  - Adjusted the `<script>` load order to resolve dependencies accurately (e.g., loading services and platform scripts before `audio.js`, `ws.js`, and `main.js`).

## Validation
- The `CURRENT_TASK.md` document has been updated, marking tasks S4-01 through S4-05 as **Done**.
- The `Current Sprint` has been incremented to **SPRINT 5**.
