# BAGAS.FM — AI AGENT REDESIGN PLAYBOOK v2
## Berdasarkan Mockup Visual Resmi + Analisis Codebase Aktual

> **Untuk AI Agent:** Ini adalah instruksi operasional, bukan spec desain. Setiap task menyebut file, baris, dan konten spesifik. Ikuti urutan phase. Jangan modifikasi backend Python atau logika JS.

---

## PETA VISUAL (dari mockup)

```
┌─────────────────────────────────────────────────────────┐
│  HOME                  SEARCH              RADIO        │
│  ─────                 ──────              ─────        │
│  Header:               Header "Search"     Header       │
│  "Good Evening"        Search Bar          "Radio"      │
│  "Bagas FM"   [Device] Recent Pill Tags    Hero Banner  │
│                        Results List        Station List │
│  Album Art (80%)                                        │
│  Ada Yang Hilang  ♥                                     │
│  Peterpan                                               │
│  ──────────────────                        DISCOVER     │
│  1:23  [═══●═══]  3:45                     ────────     │
│  ✗  ⏮  ▶  ⏭  ↺                           Browse Mood  │
│                        QUEUE               New Release  │
│  Recently Played       ─────               Top Artists  │
│  [thumb] Title  Artist ···  Now Playing               │
│  [thumb] Title  Artist ···  Next In Queue             │
│  [thumb] Title  Artist ···  1. Track                  │
│                        2. Track                        │
│  ──────────────────                                    │
│  [Home] [Search] [Radio] [Queue] [Discover]            │
└─────────────────────────────────────────────────────────┘
```

---

## ATURAN WAJIB

1. **JANGAN ubah** file Python, file JS logic (ws.js, store.js, events.js, main.js, audio.js, portal.js, utils.js, config.js)
2. **JANGAN ubah** semua DOM `id=""` yang ada — hanya ubah class, struktur HTML, dan CSS
3. **BOLEH ubah** semua `web/static/css/*.css` dan `web/static/index.html` (struktur + class)
4. **BOLEH ubah** `web/static/js/render/*.js` — hanya template HTML string dan class name, bukan logika kondisi
5. Setiap phase harus bisa di-render di browser tanpa JS error sebelum lanjut

---

## DOM IDs YANG WAJIB DIPERTAHANKAN

Semua id ini dipakai oleh js/dom.js dan tidak boleh diganti namanya:

```
portal-screen, portal-client-btn, portal-admin-btn, portal-login-form,
admin-username, admin-password, admin-submit-btn, login-error-msg,
app, app-header, content-area,
tab-home, tab-search, tab-radio, tab-queue, tab-discover,
np-title, np-artist, np-thumbnail, np-dur-meta, np-thumb-icon, np-eq-anim,
vinyl-wrap, vinyl-record, vinyl-cover, vinyl-icon,
lyrics-wrap, lyrics-prev, lyrics-current, lyrics-next,
search-input, search-msg, search-results, search-clear-btn,
radio-toggle-wrap, radio-toggle-btn, rt-sub, rt-icon,
radio-randomize-btn, radio-queue-list,
queue-list, queue-footer,
discover-favorites, discover-recent, discover-cached,
player-bar, pb-track-info, pb-mode-badge, pb-time-pos, pb-time-dur,
pb-progress-track, pb-progress-fill, pb-vol-label, vol-slider,
btn-prev, btn-play, btn-next, btn-settings, btn-download, btn-help,
btn-shuffle, btn-repeat, btn-lyrics,
pb-cache-badge, pb-sb-badge, pb-dl-badge,
main-overlay, settings-sheet, sb-toggle, ss-out-btn, ss-out-sub,
ss-stop-btn, ss-dl-row, ss-dl-track, ss-dl-pct, ss-dl-fill,
ss-history-sub, ss-history-btn,
action-sheet, action-sheet-title, action-play-now, action-enqueue, action-cancel,
help-sheet, help-close-btn, lyrics-sheet, lyrics-close-btn,
connection-toast, log-toast,
output-toggle-btn, output-btn-text, status-dot, status-text, logout-btn,
nav-home, nav-search, nav-radio, nav-queue, nav-discover, nav-bar
```

---

## PHASE 0 — BACKUP

```bash
cd ytgui-main/web/static/
for f in css/tokens.css css/base.css css/layout.css css/player.css css/tabs.css css/components.css css/portal.css index.html; do
  cp "$f" "$f.bak"
done
```

---

## PHASE 1 — DESIGN TOKENS (File: `web/static/css/tokens.css`)

**Hapus seluruh isi tokens.css dan ganti dengan:**

```css
/* ═══════════════════════════════════════════
   BAGAS.FM — Design System v2
   Midnight Audio Experience
   ═══════════════════════════════════════════ */

:root {
  /* ── Backgrounds ── */
  --bg-primary:   #090A0D;
  --bg-surface:   #12151C;
  --bg-elevated:  #171B23;

  /* ── Accent: Amber Gold ── */
  --accent:       #F2B544;
  --accent-hover: #FFC857;
  --accent-dark:  #3B2B10;
  --accent-alpha: rgba(242, 181, 68, 0.12);

  /* ── Text ── */
  --text-1: #FFFFFF;
  --text-2: #9AA0AA;
  --text-3: #60656F;

  /* ── Border ── */
  --border-1: rgba(255,255,255,0.04);
  --border-2: rgba(255,255,255,0.08);
  --border-3: rgba(255,255,255,0.14);

  /* ── Typography ── */
  --font: 'Inter', 'SF Pro Display', system-ui, sans-serif;

  /* ── Type Scale ── */
  --t-xs:  11px;
  --t-sm:  12px;
  --t-md:  14px;
  --t-lg:  16px;
  --t-xl:  18px;
  --t-2xl: 24px;

  /* ── Weights ── */
  --w-regular:  400;
  --w-medium:   500;
  --w-semibold: 600;
  --w-bold:     700;

  /* ── Spacing (8pt grid) ── */
  --s1:  4px;   --s2:  8px;   --s3: 12px;
  --s4:  16px;  --s5:  20px;  --s6: 24px;
  --s8:  32px;  --s10: 40px;  --s12: 48px;

  /* ── Radius ── */
  --r-sm:   12px;
  --r-md:   16px;
  --r-lg:   20px;
  --r-full: 999px;

  /* ── Shadow ── */
  --shadow-sm: 0 4px 12px rgba(0,0,0,0.30);
  --shadow-md: 0 8px 24px rgba(0,0,0,0.35);
  --shadow-lg: 0 16px 40px rgba(0,0,0,0.50);

  /* ── Motion ── */
  --dur-fast:   120ms;
  --dur-normal: 180ms;
  --ease:       cubic-bezier(0.0, 0.0, 0.2, 1);

  /* ── Status ── */
  --green: #22C55E;
  --red:   #EF4444;

  /* ════════════════════════════════════════
     ALIASES — Kompatibilitas dengan kode lama
     Jangan hapus — dipakai render functions
     ════════════════════════════════════════ */
  --fm-bg-deep:      var(--bg-primary);
  --fm-bg-card:      var(--bg-surface);
  --fm-bg-elevated:  var(--bg-elevated);
  --fm-bg-overlay:   rgba(9,10,13,0.85);
  --fm-accent:       var(--accent);
  --fm-accent-dim:   var(--accent-hover);
  --fm-accent-bg:    var(--accent-dark);
  --fm-cyan:         var(--accent-hover);
  --fm-teal:         var(--accent-hover);
  --fm-green:        var(--green);
  --fm-warn:         #F59E0B;
  --fm-err:          var(--red);
  --fm-blue:         #60a5fa;
  --fm-text-1:       var(--text-1);
  --fm-text-2:       #e8e8f5;
  --fm-text-3:       var(--text-2);
  --fm-text-4:       var(--text-3);
  --fm-text-5:       #4A5060;
  --fm-border:       var(--border-1);
  --fm-border-2:     var(--border-2);
  --fm-font:         var(--font);
  --fm-radius-xs:    4px;
  --fm-radius-sm:    8px;
  --fm-radius-md:    var(--r-sm);
  --fm-radius-lg:    var(--r-md);
  --fm-radius-xl:    var(--r-lg);
  --fm-radius-pill:  var(--r-full);
  --fm-radius-app:   36px;
  --fm-shadow-sm:    var(--shadow-sm);
  --fm-shadow-md:    var(--shadow-md);
  --fm-transition-fast:   var(--dur-fast) var(--ease);
  --fm-transition-normal: var(--dur-normal) var(--ease);
  --fm-primary:      var(--accent);
  --fm-color-hover:  rgba(255,255,255,0.05);
  --fm-color-active: rgba(255,255,255,0.09);
  --fm-color-disabled: rgba(255,255,255,0.30);
  --fm-color-success: var(--green);
  --fm-color-warning: #F59E0B;
  --fm-color-error:   var(--red);
  /* spacing aliases lama */
  --space-1: var(--s1); --space-2: var(--s2); --space-3: var(--s3);
  --space-4: var(--s4); --space-5: var(--s5); --space-6: var(--s6);
  --space-8: var(--s8); --space-10: var(--s10);
  /* type aliases lama */
  --text-xs: 10px; --text-sm: 12px; --text-md: 14px;
  --text-lg: 16px; --text-xl: 20px; --text-2xl: 24px;
  --weight-regular: 400; --weight-medium: 500;
  --weight-semibold: 600; --weight-bold: 700;
  /* motion aliases lama */
  --duration-fast: 100ms; --duration-normal: 200ms; --duration-slow: 350ms;
  --ease-out: cubic-bezier(0.0, 0.0, 0.2, 1);
  --ease-in:  cubic-bezier(0.4, 0.0, 1, 1);
  --ease-both:cubic-bezier(0.4, 0.0, 0.2, 1);
}
```

✅ **Selesai jika:** Tidak ada lagi `#e040fb`, `#0d0d1c`, `#141426`, atau `#1e1e38` di tokens.css

---

## PHASE 2 — BASE CSS (File: `web/static/css/base.css`)

**Ganti isi base.css dengan berikut. Ini mencakup: global reset, typography, app shell, header, player bar, controls, toast, overlay.**

```css
/* ══ BAGAS.FM base.css v2 ══ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body {
  background: var(--bg-primary);
  min-height: 100dvh;
  min-height: 100vh;
  margin: 0; padding: 0;
  font-family: var(--font);
  color: var(--text-1);
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── App Shell ── */
#app {
  width: 100%; height: 100dvh; height: 100vh;
  background: var(--bg-primary);
  display: flex; flex-direction: column; overflow: hidden;
  color: var(--text-1); font-family: var(--font);
  font-size: var(--t-md); position: relative;
}

/* ── Header ── */
#app-header {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: var(--s4) var(--s5) var(--s2);
  flex-shrink: 0;
  background: var(--bg-primary);
}

.fm-header-left { display: flex; flex-direction: column; gap: 1px; }

.fm-greeting {
  font-size: var(--t-xs);
  color: var(--text-2);
  font-weight: var(--w-regular);
  letter-spacing: 0.2px;
}

.fm-title {
  font-size: var(--t-xl);
  font-weight: var(--w-bold);
  color: var(--text-1);
  letter-spacing: -0.4px;
  line-height: 1.1;
}

.fm-hright { display: flex; align-items: center; gap: var(--s2); }

.out-btn {
  background: transparent;
  border: 1px solid var(--border-2);
  border-radius: var(--r-full);
  padding: 5px 12px;
  color: var(--text-2);
  font-size: var(--t-xs);
  font-family: var(--font);
  font-weight: var(--w-medium);
  cursor: pointer;
  letter-spacing: 0.3px;
  display: flex; align-items: center; gap: 4px;
  transition: color var(--dur-fast) var(--ease),
              border-color var(--dur-fast) var(--ease);
}
.out-btn:hover { color: var(--text-1); border-color: var(--border-3); }
.out-btn.browser { color: var(--accent); border-color: var(--accent); }

.status-dot {
  width: 6px; height: 6px;
  background: var(--green); border-radius: 50%; flex-shrink: 0;
}
.status-dot.offline { background: var(--red); }

/* ── Content Area ── */
#content-area { flex: 1; overflow-y: scroll; overflow-x: hidden; scrollbar-width: none; }
#content-area::-webkit-scrollbar { display: none; }

/* ── PLAYER BAR ── */
#player-bar {
  background: var(--bg-surface);
  border-top: 1px solid var(--border-1);
  padding: var(--s3) var(--s5) var(--s4);
  flex-shrink: 0;
}

.pb-row1 {
  display: none;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--s2);
}

.pb-title {
  font-size: var(--t-sm); font-weight: var(--w-medium);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 200px; color: var(--text-1);
}

.pb-badge {
  font-size: 10px; padding: 2px 8px;
  border-radius: var(--r-full); flex-shrink: 0;
  font-weight: var(--w-medium);
  background: var(--accent-dark); color: var(--accent);
}
.pb-badge.queue { background: rgba(96,165,250,0.12); color: #60a5fa; }

/* Progress bar */
.pb-seek {
  display: flex; align-items: center; gap: var(--s2);
  margin-bottom: var(--s3);
}

.pb-time {
  font-size: var(--t-xs); color: var(--text-3);
  min-width: 32px; font-weight: var(--w-medium);
  font-variant-numeric: tabular-nums;
}

.pb-track {
  flex: 1; height: 3px;
  background: rgba(255,255,255,0.10);
  border-radius: var(--r-full); cursor: pointer;
  position: relative; touch-action: none;
}

.pb-fill {
  height: 100%; background: var(--accent);
  border-radius: var(--r-full);
}

.pb-thumb {
  position: absolute; top: 50%;
  transform: translate(-50%, -50%);
  width: 13px; height: 13px;
  background: var(--accent); border-radius: 50%;
  cursor: grab; opacity: 0;
  transition: opacity var(--dur-fast) var(--ease);
}
.pb-track:hover .pb-thumb { opacity: 1; }

/* Controls */
.pb-ctrl {
  display: flex; flex-wrap: wrap;
  align-items: center; justify-content: center;
  gap: var(--s4) var(--s2);
  padding-top: var(--s1); position: relative;
}

.pb-ctrl .vol-grp {
  display: none; width: 100%; order: 3;
  justify-content: center; align-items: center; gap: var(--s2);
}

.pb-ctrl .main-ctrl {
  order: 1; display: flex;
  justify-content: space-between;
  width: 100%; max-width: 300px;
  align-items: center;
}

.pb-ctrl .pb-sec {
  order: 2; display: flex;
  justify-content: space-evenly;
  width: 100%; max-width: 300px;
  padding-top: var(--s2);
}

.pb-badges { order: 4; display: flex; gap: var(--s1); align-items: center; }

.btn-prev, .btn-next {
  background: none; border: none;
  color: var(--text-2); font-size: 22px;
  cursor: pointer; width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm);
  transition: color var(--dur-fast) var(--ease);
}
.btn-prev:hover, .btn-next:hover { color: var(--text-1); }

.btn-shuffle, .btn-repeat {
  background: none; border: none;
  color: var(--text-3); font-size: 18px;
  cursor: pointer; width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm);
  transition: color var(--dur-fast) var(--ease);
}
.btn-shuffle:hover, .btn-repeat:hover { color: var(--text-2); }
.btn-shuffle.active, .btn-repeat.active { color: var(--accent); }

.btn-play {
  background: var(--accent); border: none;
  color: #090A0D;
  width: 56px; height: 56px; border-radius: 50%;
  font-size: 20px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 20px rgba(242,181,68,0.30);
  transition: background var(--dur-fast) var(--ease),
              transform var(--dur-fast) var(--ease);
}
.btn-play:hover  { background: var(--accent-hover); }
.btn-play:active { transform: scale(0.96); }

.pb-sec button {
  background: none; border: none;
  color: var(--text-3); font-size: 18px;
  cursor: pointer; width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm);
  transition: color var(--dur-fast) var(--ease);
}
.pb-sec button:hover { color: var(--text-2); }

/* Volume */
.vol-label { font-size: var(--t-xs); color: var(--text-3); min-width: 30px; font-variant-numeric: tabular-nums; }

.vol-slider {
  -webkit-appearance: none; width: 100px; height: 3px;
  background: var(--border-2); border-radius: var(--r-full); outline: none;
}
.vol-slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 14px; height: 14px;
  background: var(--accent); border-radius: 50%; cursor: pointer;
}

/* Badges SM */
.pb-badge-sm {
  font-size: 10px; padding: 2px 6px;
  border-radius: var(--r-full); font-weight: var(--w-medium);
}
.pb-badge-sm.cached { background: rgba(34,197,94,0.12); color: var(--green); }
.pb-badge-sm.stream { background: rgba(96,165,250,0.12); color: #60a5fa; }
.pb-badge-sm.sb     { background: var(--accent-dark); color: var(--accent); }
.pb-badge-sm.dl     { background: rgba(96,165,250,0.12); color: #60a5fa; }

/* ── Responsive Helpers ── */
@media (max-width: 1023px) { .desktop-only { display: none !important; } }
@media (min-width: 1024px) { .mobile-only { display: none !important; } }

/* ── Mini player (non-home tabs) ── */
@media (max-width: 1023px) {
  body[data-active-tab="search"] #app-header { display: none !important; }

  body:not([data-active-tab="home"])[data-player-state="IDLE"] #player-bar { display: none !important; }

  body:not([data-active-tab="home"]) #player-bar {
    position: absolute;
    bottom: calc(60px + env(safe-area-inset-bottom));
    left: var(--s3); right: var(--s3);
    background: var(--bg-elevated);
    border-radius: var(--r-md);
    padding: var(--s2) var(--s4);
    border: 1px solid var(--border-2);
    box-shadow: var(--shadow-md);
    display: flex; align-items: center; gap: var(--s3);
    z-index: 100; min-height: 58px;
  }

  body:not([data-active-tab="home"]) #player-bar .pb-row1 { display: flex; flex: 1; }
  body:not([data-active-tab="home"]) #player-bar .pb-seek { display: none; }
  body:not([data-active-tab="home"]) #player-bar .pb-ctrl { display: none; }
  body:not([data-active-tab="home"]) #player-bar .pb-badges { display: none; }

  /* Mini play/pause button in mini player */
  body:not([data-active-tab="home"]) #player-bar .btn-play {
    width: 36px; height: 36px;
    font-size: 14px;
    box-shadow: none;
    flex-shrink: 0;
  }
}

/* ── Toasts ── */
#connection-toast {
  position: fixed; top: var(--s4); left: 50%;
  transform: translateX(-50%);
  background: var(--bg-elevated); border: 1px solid var(--border-2);
  color: var(--text-2); font-size: var(--t-sm);
  padding: 8px 16px; border-radius: var(--r-full);
  z-index: 9999; display: none;
  font-family: var(--font); box-shadow: var(--shadow-md);
}
#connection-toast.show { display: block; }

#log-toast {
  position: fixed; bottom: 80px; left: 50%;
  transform: translateX(-50%);
  background: var(--bg-elevated); border: 1px solid var(--border-2);
  color: var(--text-1); font-size: var(--t-sm);
  padding: 10px 18px; border-radius: var(--r-full);
  z-index: 9998; display: none;
  font-family: var(--font); box-shadow: var(--shadow-md);
  max-width: 280px; text-align: center;
}
#log-toast.show { display: block; }

/* ── Overlay ── */
#main-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(9,10,13,0.65);
  z-index: 200; backdrop-filter: blur(2px);
}
#main-overlay.open { display: block; }

/* ── Spinner ── */
.spinner {
  display: inline-block; width: 16px; height: 16px;
  border: 2px solid var(--border-2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: fm-spin 0.7s linear infinite;
}
@keyframes fm-spin { to { transform: rotate(360deg); } }

/* ── EQ Animation ── */
.eq-anim-icon {
  display: flex; align-items: flex-end;
  justify-content: center; gap: 3px;
  height: 16px; width: 24px;
}
.eq-anim-icon span {
  display: block; width: 4px;
  background: var(--accent); border-radius: 2px;
  animation: eq-bounce 1s ease-in-out infinite alternate;
}
.eq-anim-icon span:nth-child(1) { animation-delay: 0.1s; height: 100%; }
.eq-anim-icon span:nth-child(2) { animation-delay: 0.3s; height: 60%; }
.eq-anim-icon span:nth-child(3) { animation-delay: 0.0s; height: 80%; }
@keyframes eq-bounce {
  0%   { transform: scaleY(0.3); transform-origin: bottom; }
  100% { transform: scaleY(1);   transform-origin: bottom; }
}

/* ── Section Label ── */
.section-label {
  font-size: var(--t-xs); font-weight: var(--w-semibold);
  color: var(--text-2); letter-spacing: 0.6px;
  padding: var(--s5) var(--s5) var(--s2);
}

.section-label-row {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: var(--s5) var(--s5) var(--s2);
}
.section-label-row .label-text {
  font-size: var(--t-xs); font-weight: var(--w-semibold);
  color: var(--text-2); letter-spacing: 0.6px;
}
.section-label-row .label-link {
  font-size: var(--t-xs); color: var(--accent);
  font-weight: var(--w-medium); cursor: pointer;
  text-decoration: none;
}
```

---

## PHASE 3 — HOME TAB HTML (`web/static/index.html`)

**Cari blok ini:**
```html
<section id="tab-home" class="tab-panel active full-player-view">
    <!-- Hidden DOM elements required by app.js -->
    ...
    <div class="lyrics-wrap" id="lyrics-wrap">
        ...
    </div>
</section>
```

**Ganti SELURUH blok section#tab-home dengan ini:**

```html
<section id="tab-home" class="tab-panel active full-player-view">

    <!-- ══ Hidden DOM — JANGAN HAPUS, dipakai renderNowPlaying() ══ -->
    <div id="np-thumbnail" style="display:none;">
        <i id="np-thumb-icon"></i>
        <div id="np-eq-anim"><span></span><span></span><span></span></div>
    </div>
    <div id="np-dur-meta" style="display:none;"></div>

    <!-- ══ Header: Good Evening / Bagas FM ══ -->
    <header class="home-header" id="home-header-inner">
        <div>
            <div class="home-greeting">Good Evening</div>
            <div class="home-brand">Bagas FM</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <button id="output-toggle-btn" class="out-btn" title="Ubah Output Suara">
                <i class="ti ti-device-mobile" style="font-size:11px" aria-hidden="true"></i>
                <span id="output-btn-text">Device</span>
            </button>
            <button id="logout-btn" class="out-btn mobile-only" title="Keluar">
                <i class="ti ti-logout" style="font-size:11px"></i>
            </button>
        </div>
    </header>

    <!-- ══ Album Art Hero ══ -->
    <div class="home-art-section" id="vinyl-wrap">
        <div class="home-art-frame" id="vinyl-record">
            <img id="vinyl-cover" src="" alt="Album Art" style="display:none; width:100%; height:100%; object-fit:cover; border-radius:inherit;">
            <i id="vinyl-icon" class="ti ti-music-note home-art-placeholder"></i>
        </div>
    </div>

    <!-- ══ Track Info + Favorite ══ -->
    <div class="home-track-row">
        <div class="home-track-info main-track-info">
            <div class="mti-title" id="np-title">Belum ada lagu</div>
            <div class="mti-artist" id="np-artist">Putar lagu untuk memulai</div>
        </div>
        <button class="home-fav-btn" id="btn-favorite" aria-label="Favorite">
            <i class="ti ti-heart"></i>
        </button>
    </div>

    <!-- ══ Lyrics inline (tersembunyi, dipakai JS sync) ══ -->
    <div class="lyrics-wrap" id="lyrics-wrap" style="display:none;">
        <div class="lyrics-line prev"    id="lyrics-prev"></div>
        <div class="lyrics-line current" id="lyrics-current"></div>
        <div class="lyrics-line next"    id="lyrics-next"></div>
    </div>

    <!-- ══ Recently Played ══ -->
    <div class="home-recent-section">
        <div class="section-label-row">
            <span class="label-text">Recently Played</span>
            <span class="label-link">See all</span>
        </div>
        <div id="home-recent-list" class="home-recent-list"></div>
    </div>

</section>
```

**PENTING:** Header asli `#app-header` di luar section ini sekarang bisa di-hide untuk tab home (karena kita punya `home-header` sendiri di dalam tab). Tambahkan CSS:
```css
/* Di dalam base.css atau player.css */
body[data-active-tab="home"] #app-header { display: none !important; }
```

---

## PHASE 4 — HOME TAB CSS (`web/static/css/player.css`)

**Ganti seluruh isi player.css dengan:**

```css
/* ══ BAGAS.FM player.css v2 ══ */

/* ── Home Tab Layout ── */
.full-player-view {
  display: flex; flex-direction: column;
  overflow-y: auto; overflow-x: hidden;
  scrollbar-width: none;
  background: var(--bg-primary);
}
.full-player-view::-webkit-scrollbar { display: none; }

/* ── Home Header (inside tab) ── */
.home-header {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: var(--s4) var(--s5) var(--s3);
  flex-shrink: 0;
}

.home-greeting {
  font-size: var(--t-xs); color: var(--text-2);
  font-weight: var(--w-regular); letter-spacing: 0.2px;
}

.home-brand {
  font-size: var(--t-xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.4px;
  line-height: 1.2;
}

/* ── Album Art Hero ── */
.home-art-section {
  display: flex; justify-content: center;
  padding: var(--s2) var(--s5) var(--s5);
  flex-shrink: 0;
}

.home-art-frame {
  width: 80%;
  max-width: 300px;
  aspect-ratio: 1 / 1;
  border-radius: 18px;
  overflow: hidden;
  background: var(--bg-elevated);
  box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 6px 20px rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
  position: relative;
}

/* subtle gradient overlay di bawah artwork */
.home-art-frame::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(to bottom, transparent 55%, rgba(9,10,13,0.25) 100%);
  border-radius: inherit; pointer-events: none;
}

.home-art-placeholder {
  font-size: 72px; color: var(--text-3);
}

/* ── Track Info Row ── */
.home-track-row {
  display: flex; align-items: center;
  padding: var(--s3) var(--s5);
  gap: var(--s3);
}

.home-track-info { flex: 1; min-width: 0; }

.mti-title {
  font-size: var(--t-xl);
  font-weight: var(--w-semibold);
  color: var(--text-1);
  letter-spacing: -0.3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  line-height: 1.3;
  text-transform: capitalize;
}

.mti-artist {
  font-size: var(--t-md);
  color: var(--text-2);
  font-weight: var(--w-regular);
  margin-top: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ── Favorite Button ── */
.home-fav-btn {
  background: none; border: none;
  color: var(--text-3); font-size: 22px;
  cursor: pointer; width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm); flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease);
}
.home-fav-btn:hover { color: var(--accent); }
.home-fav-btn.active { color: var(--accent); }
.home-fav-btn.active i::before { content: "\ecd5"; } /* ti-heart-filled */

/* ── Recently Played Section ── */
.home-recent-section { flex: 1; }

.home-recent-list { display: flex; flex-direction: column; padding-bottom: var(--s8); }

.home-recent-item {
  display: flex; align-items: center;
  gap: var(--s3); padding: var(--s3) var(--s5);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
}
.home-recent-item:hover { background: var(--fm-color-hover); }
.home-recent-item.current { background: var(--accent-alpha); }

.home-recent-thumb {
  width: 46px; height: 46px;
  border-radius: 10px; overflow: hidden;
  background: var(--bg-elevated); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-3); font-size: 18px;
}
.home-recent-thumb img { width: 100%; height: 100%; object-fit: cover; }

.home-recent-info { flex: 1; min-width: 0; }

.home-recent-title {
  font-size: var(--t-md); font-weight: var(--w-medium); color: var(--text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.home-recent-item.current .home-recent-title { color: var(--accent); }

.home-recent-artist {
  font-size: var(--t-sm); color: var(--text-2); margin-top: 2px;
}

.home-recent-more {
  background: none; border: none; color: var(--text-3);
  font-size: 18px; cursor: pointer;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm); flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease);
}
.home-recent-more:hover { color: var(--text-2); }

/* ── Lyrics Inline ── */
.lyrics-wrap {
  width: 100%; text-align: center;
  padding: var(--s3) var(--s6);
}
.lyrics-line {
  font-size: var(--t-md); line-height: 1.6;
  transition: opacity var(--dur-normal) var(--ease);
}
.lyrics-line.current { color: var(--text-1); font-weight: var(--w-medium); font-size: var(--t-lg); }
.lyrics-line.prev, .lyrics-line.next { color: var(--text-3); font-size: var(--t-sm); }

/* ── Player Bar: Home mode ── */
body[data-active-tab="home"] #app-header { display: none !important; }

/* ── Seek thumb visible on home (full player) ── */
body[data-active-tab="home"] .pb-track { height: 3px; }
body[data-active-tab="home"] .pb-track:active .pb-thumb { opacity: 1; }
```

---

## PHASE 5 — RECENTLY PLAYED: RENDER FUNCTION

File: `web/static/js/render/tabs.js`

**Tambahkan fungsi ini di akhir file** (sebelum baris penutup file, atau setelah `renderDiscoverTab`):

```javascript
function renderRecentRow() {
    const container = document.getElementById('home-recent-list');
    if (!container) return;

    const items = store.discover_recent || [];
    if (items.length === 0) {
        container.innerHTML = '<div style="padding:24px 20px; color:var(--text-3); font-size:14px; text-align:center;">Belum ada riwayat putar</div>';
        return;
    }

    const currentId = store.current_track && store.current_track.video_id;
    container.innerHTML = items.slice(0, 8).map(track => {
        const title = typeof cleanTrackTitle === 'function' ? escapeHtml(cleanTrackTitle(track.title)) : escapeHtml(track.title);
        const thumb = track.thumbnail
            ? `<img src="${escapeHtml(track.thumbnail)}" alt="" loading="lazy">`
            : '<i class="ti ti-music-note"></i>';
        const isCurrent = track.video_id && track.video_id === currentId;
        return `
        <div class="home-recent-item${isCurrent ? ' current' : ''}" data-vid="${escapeHtml(track.video_id || '')}">
            <div class="home-recent-thumb">${thumb}</div>
            <div class="home-recent-info">
                <div class="home-recent-title">${title}</div>
                <div class="home-recent-artist">${escapeHtml(track.artist || '')}</div>
            </div>
            <button class="home-recent-more" data-track='${JSON.stringify(track)}' aria-label="More">
                <i class="ti ti-dots-vertical"></i>
            </button>
        </div>`;
    }).join('');

    /* Click handlers */
    container.querySelectorAll('.home-recent-item').forEach(el => {
        el.addEventListener('click', (e) => {
            if (e.target.closest('.home-recent-more')) return;
            if (store.userRole !== 'admin') return;
            const vid = el.dataset.vid;
            if (!vid) return;
            const track = (store.discover_recent || []).find(t => t.video_id === vid);
            if (track) wsSend('play_track', track);
        });
    });

    container.querySelectorAll('.home-recent-more').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            try {
                const track = JSON.parse(btn.dataset.track);
                if (typeof showActionModal === 'function') showActionModal(track);
            } catch(_) {}
        });
    });
}
```

---

## PHASE 6 — NAVIGATION BAR (`web/static/css/tabs.css`)

**Ganti seluruh isi tabs.css dengan:**

```css
/* ══ BAGAS.FM tabs.css v2 ══ */

/* ── Tab Panels ── */
.tab-panel { display: none; flex-direction: column; height: 100%; }
.tab-panel.active { display: flex; }

/* ── Bottom Navigation ── */
.navrow {
  display: flex; align-items: stretch;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-1);
  padding-bottom: env(safe-area-inset-bottom);
  flex-shrink: 0; position: relative; z-index: 50;
}

.nav-btn {
  flex: 1; display: flex;
  flex-direction: column; align-items: center; justify-content: center;
  gap: 4px; padding: 10px 0 8px;
  background: none; border: none;
  color: var(--text-3);
  font-size: 9px; font-family: var(--font);
  font-weight: var(--w-medium);
  letter-spacing: 0.4px;
  text-transform: uppercase;
  cursor: pointer;
  position: relative;
  transition: color var(--dur-fast) var(--ease);
  -webkit-tap-highlight-color: transparent;
}

.nav-btn i {
  font-size: 22px; line-height: 1;
  transition: transform var(--dur-fast) var(--ease);
}

.nav-btn span { display: block; line-height: 1; }

.nav-btn:hover { color: var(--text-2); }
.nav-btn:active i { transform: scale(0.92); }
.nav-btn.active { color: var(--accent); }

/* Active dot */
.nav-btn.active::after {
  content: '';
  position: absolute; bottom: 3px; left: 50%;
  transform: translateX(-50%);
  width: 4px; height: 4px;
  background: var(--accent); border-radius: 50%;
}
```

**Update nav HTML di index.html** — cari blok `<nav class="navrow"` dan ganti isinya:

```html
<nav class="navrow" id="nav-bar">
    <button class="nav-btn active" data-tab="home" id="nav-home">
        <i class="ti ti-home" aria-hidden="true"></i><span>Home</span>
    </button>
    <button class="nav-btn" data-tab="search" id="nav-search">
        <i class="ti ti-search" aria-hidden="true"></i><span>Search</span>
    </button>
    <button class="nav-btn" data-tab="radio" id="nav-radio">
        <i class="ti ti-radio" aria-hidden="true"></i><span>Radio</span>
    </button>
    <button class="nav-btn" data-tab="queue" id="nav-queue">
        <i class="ti ti-list-numbers" aria-hidden="true"></i><span>Queue</span>
    </button>
    <button class="nav-btn" data-tab="discover" id="nav-discover">
        <i class="ti ti-compass" aria-hidden="true"></i><span>Discover</span>
    </button>
</nav>
```

---

## PHASE 7 — SEARCH TAB HTML + CSS

### 7.1 — Update Search Tab HTML

**Cari** `<section id="tab-search" class="tab-panel">` dan ganti isinya:

```html
<section id="tab-search" class="tab-panel">
    <div class="search-header">
        <h1 class="search-title">Search</h1>
    </div>

    <div class="search-wrap" id="search-input-wrap" style="position:relative;">
        <i class="ti ti-search search-icon" aria-hidden="true"></i>
        <input type="text" id="search-input"
               placeholder="Search songs, artists, albums..."
               autocomplete="off">
        <button id="search-clear-btn" aria-label="Clear Search"
                style="display:none; position:absolute; right:14px; background:none; border:none; color:var(--text-3); font-size:16px; cursor:pointer;">
            <i class="ti ti-x"></i>
        </button>
    </div>

    <div id="search-msg" style="padding:4px 20px 8px; font-size:12px; color:var(--text-3);">Search songs, artists, albums...</div>
    <div id="search-results"></div>
</section>
```

### 7.2 — Search CSS (tambahkan ke components.css)

```css
/* ══ SEARCH TAB ══ */

.search-header {
  padding: var(--s5) var(--s5) var(--s3);
  background: var(--bg-primary);
  flex-shrink: 0;
}

.search-title {
  font-size: var(--t-2xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.5px;
}

.search-wrap {
  margin: 0 var(--s5) var(--s3);
  display: flex; align-items: center;
  background: var(--bg-surface);
  border: 1px solid var(--border-2);
  border-radius: 14px;
  padding: 0 var(--s4); gap: var(--s2);
  transition: border-color var(--dur-fast) var(--ease);
  flex-shrink: 0;
}
.search-wrap:focus-within { border-color: var(--border-3); }

.search-icon { color: var(--text-3); font-size: 18px; flex-shrink: 0; }

#search-input {
  flex: 1; background: none; border: none; outline: none;
  color: var(--text-1); font-size: var(--t-md);
  font-family: var(--font); padding: 13px 0;
  caret-color: var(--accent);
}
#search-input::placeholder { color: var(--text-3); }

/* Results */
#search-results {
  display: flex; flex-direction: column;
  padding-bottom: var(--s12); overflow-y: auto;
}

.sr-item {
  display: flex; align-items: center;
  gap: var(--s3); padding: var(--s3) var(--s5);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
  -webkit-tap-highlight-color: transparent;
}
.sr-item:hover { background: var(--fm-color-hover); }
.sr-item.current { background: var(--accent-alpha); }
.sr-item.current .sr-title { color: var(--accent); }

.sr-thumb {
  width: 46px; height: 46px;
  border-radius: 10px; background: var(--bg-elevated);
  flex-shrink: 0; display: flex;
  align-items: center; justify-content: center;
  overflow: hidden; color: var(--text-3); font-size: 18px; position: relative;
}
.sr-thumb img { width: 100%; height: 100%; object-fit: cover; }
.sr-thumb.playing { background: var(--accent-dark); }
.sr-eq { color: var(--accent); }

.sr-info { flex: 1; min-width: 0; }

.sr-title {
  font-size: var(--t-md); font-weight: var(--w-medium); color: var(--text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.sr-meta { font-size: var(--t-sm); color: var(--text-2); margin-top: 3px; }

.sr-more-btn {
  background: none; border: none;
  color: var(--text-3); font-size: 18px; cursor: pointer;
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm); flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease);
}
.sr-more-btn:hover { color: var(--text-2); }
```

---

## PHASE 8 — RADIO TAB

### 8.1 — Update Radio Tab HTML

**Cari** `<section id="tab-radio" class="tab-panel">` dan ganti isinya:

```html
<section id="tab-radio" class="tab-panel">
    <!-- Header -->
    <div class="radio-page-header">
        <h1 class="radio-page-title">Radio</h1>
        <p class="radio-page-sub">Your music, nonstop</p>
    </div>

    <!-- Featured Station Hero -->
    <div class="radio-featured">
        <div class="radio-featured-inner">
            <div class="radio-featured-icon">
                <i class="ti ti-radio-active" style="font-size:28px; color:var(--accent);"></i>
            </div>
            <div class="radio-featured-name">Bagas FM</div>
            <div class="radio-featured-sub">24/7 Nonstop Music</div>
        </div>
    </div>

    <!-- Radio Toggle (id wajib dijaga) -->
    <div class="radio-toggle" id="radio-toggle-wrap">
        <div class="rt-left">
            <div class="rt-icon" id="rt-icon">
                <i class="ti ti-antenna" aria-hidden="true"></i>
            </div>
            <div>
                <div class="rt-title">Radio Mode</div>
                <div class="rt-sub" id="rt-sub">Aktifkan untuk putar otomatis</div>
            </div>
        </div>
        <button class="fm-toggle off" id="radio-toggle-btn"
                data-on="false" aria-label="Toggle Radio">
            <div class="toggle-dot"></div>
        </button>
    </div>

    <!-- Shuffle Button -->
    <div style="padding: var(--s3) var(--s5);">
        <button id="radio-randomize-btn" class="radio-shuffle-btn" aria-label="Acak Queue">
            <i class="ti ti-dice" aria-hidden="true"></i>
            Acak Artis
        </button>
    </div>

    <!-- All Stations label -->
    <div class="section-label">All Stations</div>

    <!-- Station List (rendered from radio_queue) -->
    <div id="radio-queue-list" style="display:flex; flex-direction:column; padding-bottom:80px;"></div>
</section>
```

### 8.2 — Radio CSS (tambahkan ke components.css)

```css
/* ══ RADIO TAB ══ */

.radio-page-header {
  padding: var(--s5) var(--s5) var(--s3);
  background: var(--bg-primary);
}

.radio-page-title {
  font-size: var(--t-2xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.5px;
}

.radio-page-sub { font-size: var(--t-sm); color: var(--text-2); margin-top: 3px; }

/* Featured Hero */
.radio-featured {
  margin: 0 var(--s5) var(--s4);
  border-radius: var(--r-md);
  background: linear-gradient(135deg, #1C1508 0%, #2A1E08 40%, #151A22 100%);
  padding: var(--s8) var(--s6);
  display: flex; align-items: center; justify-content: center;
  position: relative; overflow: hidden;
  min-height: 160px;
}

.radio-featured::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at 25% 50%, rgba(242,181,68,0.10) 0%, transparent 65%);
  pointer-events: none;
}

.radio-featured-inner {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center; gap: var(--s3);
  text-align: center;
}

.radio-featured-icon {
  width: 56px; height: 56px;
  border-radius: 50%;
  background: var(--accent-dark);
  border: 1px solid rgba(242,181,68,0.3);
  display: flex; align-items: center; justify-content: center;
}

.radio-featured-name {
  font-size: var(--t-xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.3px;
}

.radio-featured-sub { font-size: var(--t-sm); color: var(--text-2); }

/* Toggle Row */
.radio-toggle {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--s4) var(--s5);
  background: var(--bg-surface);
  border-top: 1px solid var(--border-1);
  border-bottom: 1px solid var(--border-1);
}

.rt-left { display: flex; align-items: center; gap: var(--s3); }

.rt-icon {
  width: 36px; height: 36px;
  background: var(--accent-dark);
  border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center;
  color: var(--accent); font-size: 18px;
}

.rt-title { font-size: var(--t-md); font-weight: var(--w-medium); color: var(--text-1); }
#rt-sub    { font-size: var(--t-xs); color: var(--text-3); margin-top: 2px; }

/* Toggle switch */
.fm-toggle {
  width: 44px; height: 26px; border-radius: var(--r-full);
  border: none; background: var(--border-2);
  cursor: pointer; position: relative;
  transition: background var(--dur-normal) var(--ease);
  flex-shrink: 0;
}
.fm-toggle.on { background: var(--accent); }
.toggle-dot {
  position: absolute; width: 20px; height: 20px;
  background: white; border-radius: 50%;
  top: 3px; left: 3px;
  transition: transform var(--dur-normal) var(--ease);
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}
.fm-toggle.on .toggle-dot { transform: translateX(18px); }

/* Shuffle Button */
.radio-shuffle-btn {
  width: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border-2);
  border-radius: var(--r-sm);
  padding: var(--s3) var(--s4);
  color: var(--text-2);
  font-size: var(--t-md); font-weight: var(--w-medium);
  font-family: var(--font); cursor: pointer;
  display: flex; align-items: center; justify-content: center; gap: var(--s2);
  transition: border-color var(--dur-fast) var(--ease),
              color var(--dur-fast) var(--ease);
}
.radio-shuffle-btn:hover { border-color: var(--border-3); color: var(--text-1); }
.radio-shuffle-btn i { font-size: 18px; }
```

---

## PHASE 9 — QUEUE TAB

### 9.1 — Queue CSS (tambahkan ke components.css)

```css
/* ══ QUEUE TAB ══ */

#tab-queue { background: var(--bg-primary); }

.queue-item {
  display: flex; align-items: center;
  gap: var(--s3); padding: var(--s3) var(--s5);
  transition: background var(--dur-fast) var(--ease);
  cursor: default;
  -webkit-tap-highlight-color: transparent;
}
.queue-item:hover { background: var(--fm-color-hover); }
.queue-item.current { background: var(--accent-alpha); }

.qi-drag {
  color: var(--text-3); font-size: 18px;
  cursor: grab; flex-shrink: 0; opacity: 0.4;
  user-select: none;
}

.qi-index {
  width: 22px; font-size: var(--t-sm);
  color: var(--text-3); text-align: center;
  flex-shrink: 0; font-variant-numeric: tabular-nums;
}
.queue-item.current .qi-index { color: var(--accent); }

.qi-info { flex: 1; min-width: 0; }

.qi-title {
  font-size: var(--t-md); font-weight: var(--w-medium);
  color: var(--text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.queue-item.current .qi-title { color: var(--accent); }

.qi-dur { font-size: var(--t-xs); color: var(--text-2); margin-top: 3px; }

.qi-remove {
  background: none; border: none; color: var(--text-3);
  font-size: 14px; cursor: pointer;
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border-radius: var(--r-sm); flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease);
}
.qi-remove:hover { color: var(--red); }

.queue-empty {
  text-align: center; color: var(--text-3);
  font-size: var(--t-md); padding: var(--s10) var(--s5);
  line-height: 1.6; display: flex; flex-direction: column;
  align-items: center; gap: var(--s3);
}

#queue-footer {
  text-align: center; padding: var(--s3) 0;
  font-size: var(--t-xs); color: var(--text-3);
  font-weight: var(--w-medium); letter-spacing: 0.3px;
}
```

---

## PHASE 10 — DISCOVER TAB

### 10.1 — Update Discover Tab HTML

**Cari** `<section id="tab-discover" class="tab-panel">` dan ganti isinya:

```html
<section id="tab-discover" class="tab-panel">
    <!-- Header -->
    <div class="discover-header">
        <h1 class="discover-title">Discover</h1>
        <p class="discover-sub">Find your next favorite song</p>
    </div>

    <!-- Browse By Mood -->
    <div class="section-label-row">
        <span class="label-text">Browse By Mood</span>
        <span class="label-link">See all</span>
    </div>
    <div class="mood-row">
        <div class="mood-card" data-mood="chill">
            <i class="ti ti-coffee mood-icon"></i>
            <span>Chill</span>
        </div>
        <div class="mood-card mood-romantic" data-mood="romantic">
            <i class="ti ti-heart mood-icon"></i>
            <span>Romantic</span>
        </div>
        <div class="mood-card mood-energetic" data-mood="energetic">
            <i class="ti ti-bolt mood-icon"></i>
            <span>Energetic</span>
        </div>
    </div>

    <!-- New Release (dari discover_cached / recent) -->
    <div class="section-label-row">
        <span class="label-text">New Release</span>
        <span class="label-link">See all</span>
    </div>
    <div id="discover-recent" style="display:flex; flex-direction:column;"></div>

    <!-- Top Artists / Most Played -->
    <div class="section-label-row">
        <span class="label-text">Paling Sering Diputar</span>
        <span class="label-link">See all</span>
    </div>
    <div class="disc-row2" id="discover-favorites"></div>

    <!-- Cache -->
    <div class="section-label">Tersimpan Lokal</div>
    <div id="discover-cached" style="display:flex; flex-direction:column; padding-bottom:80px;"></div>
</section>
```

### 10.2 — Discover CSS (tambahkan ke components.css)

```css
/* ══ DISCOVER TAB ══ */

.discover-header { padding: var(--s5) var(--s5) var(--s2); }
.discover-title {
  font-size: var(--t-2xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.5px;
}
.discover-sub { font-size: var(--t-sm); color: var(--text-2); margin-top: 3px; }

/* Mood Cards */
.mood-row {
  display: flex; gap: var(--s3);
  padding: 0 var(--s5) var(--s3);
  overflow-x: auto; scrollbar-width: none;
}
.mood-row::-webkit-scrollbar { display: none; }

.mood-card {
  flex: 1; min-width: 96px;
  background: var(--bg-elevated);
  border-radius: var(--r-sm);
  padding: var(--s4) var(--s3);
  display: flex; flex-direction: column;
  align-items: center; gap: var(--s2);
  cursor: pointer; position: relative; overflow: hidden;
  transition: opacity var(--dur-fast) var(--ease);
  border: 1px solid var(--border-1);
}
.mood-card:hover { opacity: 0.85; }

.mood-icon {
  font-size: 22px; color: var(--accent);
  display: block;
}

.mood-card span {
  font-size: var(--t-sm); font-weight: var(--w-medium);
  color: var(--text-1); text-align: center;
}

.mood-romantic  .mood-icon { color: #f43f5e; }
.mood-energetic .mood-icon { color: #f59e0b; }

/* Discover List Items */
.fav-card, .sr-item {
  display: flex; align-items: center;
  gap: var(--s3); padding: var(--s3) var(--s5);
  cursor: pointer; transition: background var(--dur-fast) var(--ease);
}
.fav-card:hover { background: var(--fm-color-hover); }

.fav-num {
  width: 20px; font-size: var(--t-sm);
  color: var(--text-3); text-align: center; flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.fav-thumb {
  width: 44px; height: 44px;
  border-radius: 10px; background: var(--bg-elevated);
  flex-shrink: 0; display: flex;
  align-items: center; justify-content: center;
  overflow: hidden; color: var(--text-3);
}
.fav-thumb img { width: 100%; height: 100%; object-fit: cover; }

.fav-info { flex: 1; min-width: 0; }
.fav-title {
  font-size: var(--t-md); font-weight: var(--w-medium); color: var(--text-1);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fav-cnt { font-size: var(--t-xs); color: var(--text-2); margin-top: 3px; }

.discover-empty {
  text-align: center; color: var(--text-3);
  font-size: var(--t-md);
  padding: var(--s8) var(--s5);
  display: flex; flex-direction: column;
  align-items: center; gap: var(--s2);
}
```

---

## PHASE 11 — SHEETS & PORTAL (`web/static/css/portal.css` + `components.css`)

### 11.1 — Portal CSS (ganti seluruh portal.css)

```css
/* ══ BAGAS.FM portal.css v2 ══ */

#portal-screen {
  position: fixed; inset: 0;
  background: var(--bg-primary);
  display: flex; align-items: center; justify-content: center;
  z-index: 9000; padding: var(--s6);
}
#portal-screen.portal-hidden { display: none; }

.portal-card {
  width: 100%; max-width: 340px;
  background: var(--bg-surface);
  border: 1px solid var(--border-1);
  border-radius: var(--r-lg);
  padding: var(--s8);
  box-shadow: var(--shadow-lg);
}

.portal-title {
  font-size: var(--t-2xl); font-weight: var(--w-bold);
  color: var(--text-1); letter-spacing: -0.5px;
  margin-bottom: 4px;
}
.portal-subtitle { font-size: var(--t-sm); color: var(--text-2); margin-bottom: var(--s6); }

.portal-options { display: flex; flex-direction: column; gap: var(--s3); }

.portal-btn {
  width: 100%; background: var(--bg-elevated);
  border: 1px solid var(--border-1);
  border-radius: var(--r-sm); padding: var(--s4);
  color: var(--text-1); cursor: pointer; text-align: left;
  font-family: var(--font);
  display: flex; align-items: flex-start; gap: var(--s3);
  transition: border-color var(--dur-fast) var(--ease),
              background var(--dur-fast) var(--ease);
}
.portal-btn:hover { border-color: var(--border-2); background: rgba(255,255,255,0.03); }
.portal-btn.admin { border-color: var(--accent-dark); }
.portal-btn.admin:hover { border-color: rgba(242,181,68,0.4); }

.portal-icon {
  width: 36px; height: 36px;
  background: var(--accent-dark); border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center;
  color: var(--accent); font-size: 18px; flex-shrink: 0;
}
.portal-btn.client .portal-icon { background: rgba(96,165,250,0.12); color: #60a5fa; }

.portal-btn-title {
  display: block; font-size: var(--t-md);
  font-weight: var(--w-semibold); color: var(--text-1); margin-bottom: 3px;
}
.portal-btn-desc { display: block; font-size: var(--t-xs); color: var(--text-2); line-height: 1.5; }

.portal-admin-wrapper { display: flex; flex-direction: column; gap: var(--s2); }

.portal-login-form {
  background: var(--bg-elevated);
  border: 1px solid var(--border-2);
  border-radius: var(--r-sm); padding: var(--s4);
  display: flex; flex-direction: column; gap: var(--s3);
}
.portal-login-form.hidden { display: none; }

.login-input-group input {
  width: 100%; background: var(--bg-surface);
  border: 1px solid var(--border-2);
  border-radius: 10px; padding: 12px var(--s4);
  color: var(--text-1); font-size: var(--t-md);
  font-family: var(--font); outline: none;
  caret-color: var(--accent);
  transition: border-color var(--dur-fast) var(--ease);
}
.login-input-group input:focus { border-color: var(--accent); }
.login-input-group input::placeholder { color: var(--text-3); }

#admin-submit-btn {
  width: 100%; background: var(--accent); border: none;
  border-radius: 10px; padding: 12px;
  color: #090A0D; font-size: var(--t-md);
  font-weight: var(--w-semibold); font-family: var(--font);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease);
}
#admin-submit-btn:hover { background: var(--accent-hover); }

.login-error { font-size: var(--t-xs); color: var(--red); text-align: center; min-height: 16px; }
```

### 11.2 — Sheets CSS (tambahkan ke components.css)

```css
/* ══ BOTTOM SHEETS ══ */

.settings-sheet {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: var(--bg-surface);
  border-radius: var(--r-lg) var(--r-lg) 0 0;
  border-top: 1px solid var(--border-2);
  padding: var(--s3) 0 calc(var(--s8) + env(safe-area-inset-bottom));
  transform: translateY(100%);
  transition: transform var(--dur-normal) var(--ease);
  z-index: 300; max-height: 82vh; overflow-y: auto; scrollbar-width: none;
}
.settings-sheet::-webkit-scrollbar { display: none; }
.settings-sheet.open { transform: translateY(0); }

.ss-handle {
  width: 36px; height: 4px;
  background: var(--border-3); border-radius: var(--r-full);
  margin: 0 auto var(--s4);
}

.ss-title {
  font-size: var(--t-xs); font-weight: var(--w-semibold);
  color: var(--text-3); text-transform: uppercase;
  letter-spacing: 0.6px; padding: 0 var(--s5) var(--s3);
}

.ss-row {
  display: flex; align-items: center;
  justify-content: space-between;
  padding: var(--s4) var(--s5);
  transition: background var(--dur-fast) var(--ease);
}
.ss-row:hover { background: var(--fm-color-hover); }

.ss-label {
  display: flex; align-items: center; gap: var(--s3);
  color: var(--text-2); font-size: 18px;
}
.ss-label > div { display: flex; flex-direction: column; gap: 2px; }
.ss-label-text { font-size: var(--t-md); font-weight: var(--w-medium); color: var(--text-1); }
.ss-label-sub  { font-size: var(--t-xs); color: var(--text-2); }

.ss-toggle {
  width: 44px; height: 26px; border-radius: var(--r-full);
  border: none; background: var(--border-2);
  cursor: pointer; position: relative;
  transition: background var(--dur-normal) var(--ease); flex-shrink: 0;
}
.ss-toggle[data-on="true"] { background: var(--accent); }
.ss-toggle .toggle-dot {
  position: absolute; width: 20px; height: 20px;
  background: white; border-radius: 50%; top: 3px; left: 3px;
  transition: transform var(--dur-normal) var(--ease);
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}
.ss-toggle[data-on="true"] .toggle-dot { transform: translateX(18px); }

.ss-action-btn {
  background: var(--accent-dark); border: none;
  border-radius: var(--r-sm); padding: 8px 14px;
  color: var(--accent); font-size: var(--t-sm);
  font-weight: var(--w-medium); font-family: var(--font);
  cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
  transition: background var(--dur-fast) var(--ease);
}
.ss-action-btn:hover { background: rgba(242,181,68,0.2); }

/* Download bar */
.dl-bar-wrap { width: 100%; }
.dl-label { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: var(--t-xs); color: var(--text-3); }
.dl-bar { height: 3px; background: var(--border-2); border-radius: var(--r-full); overflow: hidden; }
.dl-fill { height: 100%; background: var(--accent); border-radius: var(--r-full); transition: width 0.3s; }

/* Action Sheet */
#action-sheet-title {
  font-size: var(--t-sm); color: var(--text-2);
  padding: 0 var(--s5) var(--s4);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
```

---

## PHASE 12 — HTML HEAD UPDATE

**Cari** `<meta name="theme-color" content="#0d0d1c">` dan ganti dengan:

```html
<meta name="theme-color" content="#090A0D">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

**Ganti** `<title>bagas.fm — Music Player</title>` dengan:
```html
<title>Bagas.FM — Midnight Audio Experience</title>
```

---

## PHASE 13 — BERSIHKAN SISA HARDCODE WARNA

Setelah semua phase selesai, jalankan:

```bash
cd ytgui-main/web/static/css/
grep -rn "#e040fb\|#c020d0\|#2a1540\|#0d0d1c\|#141426\|#1e1e38\|#0f0f20" .
```

Setiap temuan ganti dengan token yang tepat:

| Warna Lama | Ganti Dengan |
|------------|-------------|
| `#e040fb`  | `var(--accent)` |
| `#c020d0`  | `var(--accent-hover)` |
| `#2a1540`  | `var(--accent-dark)` |
| `#0d0d1c`  | `var(--bg-primary)` |
| `#141426`  | `var(--bg-surface)` |
| `#1e1e38`  | `var(--bg-elevated)` |
| `#0f0f20`  | `var(--bg-primary)` |
| `#2e2e48`  | `var(--border-2)` |
| `#1e1e32`  | `var(--border-1)` |
| `#9a9abc`  | `var(--text-2)` |
| `#6a6a8c`  | `var(--text-3)` |

---

## PHASE 14 — FIX: JS RENDER COMPATIBILITY

### radio-toggle-btn class mismatch

Di `js/events.js` atau `js/render/tabs.js`, toggle radio dicek via class `on`/`off`. Pastikan class toggle di HTML adalah `fm-toggle off` (bukan `toggle off` lama). Jika JS mencari `.toggle.on`, tambahkan alias di CSS:

```css
/* Alias untuk backward-compat */
.toggle { /* sama dengan .fm-toggle */ }
.toggle.on { background: var(--accent); }
.toggle.off { background: var(--border-2); }
.toggle .toggle-dot { /* sama */ }
.toggle.on .toggle-dot { transform: translateX(18px); }
```

### sb-toggle class

Di HTML, `id="sb-toggle"` memakai class `ss-toggle`. JS membaca `data-on` attribute. Tidak perlu perubahan — sudah handle di CSS via `[data-on="true"]`.

---

## PHASE 15 — VERIFIKASI VISUAL (Checklist)

Buka browser, buka DevTools mobile viewport (375px), lakukan semua item berikut:

### Visual
```
[ ] Background: hitam midnight #090A0D, bukan ungu
[ ] Play button: amber #F2B544, icon hitam #090A0D
[ ] Progress bar fill: amber
[ ] Volume slider: amber thumb
[ ] Active nav: amber, dengan dot di bawah
[ ] Font: Inter (DevTools Network → filter "inter")
[ ] Home: header "Good Evening / Bagas FM" + Device button
[ ] Home: album art hero 80% lebar, rounded 18px, shadow dalam
[ ] Home: track title 18px semibold, artis 14px secondary
[ ] Home: heart button di kanan track info
[ ] Home: "Recently Played" list muncul di bawah controls
[ ] Home: recently played items punya thumb, title, artis, ··· button
[ ] Search: header "Search" 24px bold
[ ] Search: search bar rounded dark surface
[ ] Radio: header "Radio / Your music, nonstop"
[ ] Radio: featured hero card dengan icon amber dan "Bagas FM"
[ ] Radio: toggle switch dengan amber saat aktif
[ ] Radio: "All Stations" section label
[ ] Queue: section "Now Playing" + "Next In Queue" nomor urut
[ ] Discover: mood cards (Chill / Romantic / Energetic) horizontal
[ ] Discover: "New Release" list
[ ] Discover: "Paling Sering Diputar" list
[ ] Portal: card dark, button amber submit
[ ] Settings sheet: dark surface, slide up dari bawah
```

### Fungsional (tidak boleh rusak)
```
[ ] WebSocket connect (status dot hijau)
[ ] Login admin berhasil
[ ] Search + tampil hasil
[ ] Tap hasil → action sheet muncul
[ ] Tap "Putar" → lagu main, album art muncul di Home
[ ] Progress bar bergerak saat lagu main
[ ] Next / Prev button OK
[ ] Play / Pause button OK
[ ] Tap recently played item → lagu main
[ ] Radio toggle ON → rt-sub berubah teks
[ ] Discover data muncul (jika pernah putar lagu)
[ ] Mini player muncul di tab selain Home (saat ada lagu)
[ ] Settings sheet terbuka dari ··· button
[ ] SponsorBlock toggle ON/OFF visual berubah
[ ] Download progress bar tampil saat download
[ ] Lyrics sheet terbuka
[ ] Drag reorder di Queue masih bisa
```

---

## TROUBLESHOOTING

### Album art tidak muncul setelah redesign

`renderNowPlaying()` di `js/render/tabs.js` menggunakan:
- `dom.vinylCover` → `document.getElementById("vinyl-cover")`
- `dom.vinylRecord` → `document.getElementById("vinyl-record")`
- `dom.vinylIcon`  → `document.getElementById("vinyl-icon")`

Pastikan semua id ini ada di HTML baru. Jika sudah ada tapi tetap gagal, buka DevTools Console cek error.

### Recently Played tidak muncul

`renderRecentRow()` dipanggil dari `js/ws.js` saat menerima `discover_data`. Fungsi ini hanya ada setelah Phase 5 diimplementasi. Cek: (1) fungsi sudah ditambahkan ke `tabs.js`, (2) `document.getElementById('home-recent-list')` ada di DOM, (3) `store.discover_recent` tidak kosong (putar beberapa lagu dulu).

### Warna masih ungu

```bash
grep -rn "#e040fb\|var(--fm-accent)" web/static/css/ web/static/js/render/
```
Sering ada di inline style di JS render functions. Cari dan ganti dengan `var(--accent)`.

### Toggle Radio tidak berubah visual

JS mencari class `on`/`off` di button `radio-toggle-btn`. Pastikan Phase 14 alias CSS sudah ditambahkan, atau ganti class di HTML dari `fm-toggle` kembali ke `toggle` sesuai ekspektasi JS.

### Font tidak muncul (offline/Termux)

Hapus `@import url(...)` dari base.css dan tambahkan fallback:
```css
--font: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
```
Inter tidak kritis — system-ui sudah memberikan hasil yang sangat mirip.

---

## RINGKASAN FILE & PRIORITAS

| File | Action | Priority |
|------|--------|----------|
| `css/tokens.css` | REPLACE FULL | 🔴 CRITICAL |
| `css/base.css` | REPLACE FULL | 🔴 CRITICAL |
| `css/player.css` | REPLACE FULL | 🔴 CRITICAL |
| `css/tabs.css` | REPLACE FULL | 🟠 HIGH |
| `css/components.css` | ADD sections | 🟠 HIGH |
| `css/portal.css` | REPLACE FULL | 🟠 HIGH |
| `index.html` — tab-home | REPLACE section | 🔴 CRITICAL |
| `index.html` — tab-search | UPDATE isi | 🟠 HIGH |
| `index.html` — tab-radio | REPLACE section | 🟠 HIGH |
| `index.html` — tab-discover | REPLACE section | 🟡 MEDIUM |
| `index.html` — nav | UPDATE icons/labels | 🟡 MEDIUM |
| `index.html` — head | ADD Inter font | 🟡 MEDIUM |
| `js/render/tabs.js` | ADD renderRecentRow() | 🟠 HIGH |
| `css/layout.css` | GREP & CLEAN hardcode | 🟡 MEDIUM |
| Semua file backend | ❌ JANGAN DISENTUH | — |

---

*Playbook ini dibuat berdasarkan: (1) analisis langsung source code ytgui-main, (2) mockup visual Bagas.FM Juni 2026. Versi ini menggantikan playbook v1.*
