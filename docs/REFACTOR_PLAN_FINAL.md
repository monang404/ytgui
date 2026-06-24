# REFACTOR_PLAN_FINAL.md — bagas.fm
> **Single Source of Truth** untuk AI Agent  
> **Versi:** 2.1 Final  
> **Dibuat dari:** REFACTOR_PLAN.md v2.0 + verifikasi langsung codebase  
> **Target Agent:** baca dokumen ini saja, tidak perlu baca dokumen lain

---

## Daftar Isi
1. [Konteks & Kondisi Awal Terverifikasi](#1-konteks--kondisi-awal-terverifikasi)
2. [Arsitektur Target](#2-arsitektur-target)
3. [Design Token System](#3-design-token-system-wajib-sesuai-mockup)
4. [Struktur Folder Target](#4-struktur-folder-target)
5. [Peta Migrasi Exhaustive](#5-peta-migrasi-exhaustive)
6. [Urutan Fase Eksekusi](#6-urutan-fase-eksekusi)
7. [Laws of This Codebase](#7-laws-of-this-codebase)
8. [Konvensi Penamaan](#8-konvensi-penamaan)
9. [Checklist Contributor](#9-checklist-contributor)

---

## 1. Konteks & Kondisi Awal Terverifikasi

### 1.1 Ringkasan Proyek

`bagas.fm` adalah web-based music player yang ditenagai YouTube. Stack:
- **Backend:** Python 3 + aiohttp + asyncio + SQLite (cache)
- **Audio engine:** MPV via IPC socket
- **Fetch:** yt-dlp
- **Frontend:** HTML/CSS/JS (tanpa framework, vanilla)
- **Target platform:** Termux (Android), Linux, Windows
- **UI paradigm:** Mobile-first (375px frame, 5-tab nav)

### 1.2 God Files yang Harus Dipecah

| File | Baris | Masalah |
|---|---|---|
| `web/static/app.js` | 1624 | WS + state + DOM + render + EQ + portal + audio + events semuanya satu file |
| `web/static/style.css` | 992 | Token, layout, komponen, animasi, portal — satu file + 21 CSS var tak terdefinisi |
| `web/static/index.html` | 339 | Inline styles, struktur tidak modular |
| `web/server.py` | 700 | HTTP handler + WebSocket + auth + serializer + room manager |
| `main.py` | 187 | Wiring + startup + connectivity check seharusnya terpisah |

### 1.3 Status "Sudah Benar" (Jangan Diubah)

| Item | Lokasi | Keterangan |
|---|---|---|
| Tabler Icons CDN | `index.html` baris 11 | ✅ Sudah dimuat: `@tabler/icons-webfont@latest` |
| Container shape | `style.css` baris 28 | ✅ `#app { border-radius:36px; background:#0d0d1c; border:3px solid #1e1e32 }` |
| Player bar flex-shrink | `style.css` baris ~34 | ✅ `#player-bar { flex-shrink:0 }` sudah ada |
| Badge colors | `style.css` baris ~53 | ✅ `.pb-badge` dan `.pb-badge.queue` hardcoded dengan warna benar |
| Seek bar + thumb | `style.css` | ✅ `.pb-fill { background:#e040fb }`, `.pb-thumb` sudah ada |
| Config.py | `config.py` | ✅ Sudah clean — ENV var, paths, security |
| Per-room EventBus | `core/room_manager.py` | ✅ Sudah diimplementasi |
| SSRF guard | `core/security.py` | ✅ Sudah ada |
| Password hashing | `config.py` + `core/security.py` | ✅ PBKDF2 sudah diimplementasi |

### 1.4 Bug Aktif yang Harus Diperbaiki

| Bug | Penyebab Terverifikasi | Lokasi |
|---|---|---|
| Semua `var()` resolves ke `unset` | **TIDAK ADA `:root {}` block** — style.css dimulai langsung dari `@import`, bukan `:root` | `style.css` baris 1 |
| 21 jenis CSS variable tak terdefinisi | `var(--accent-fire)`, `var(--bg-panel)`, dll. dipakai tapi tak punya nilai | `style.css` (104 kemunculan) |
| Warna accent merah, bukan ungu | `--accent-fire` seharusnya `#e040fb` tapi nilainya belum dideklarasi sama sekali | `style.css` |
| File sampah ter-commit | `web/static/switchTab.txt` | `web/static/` |
| Typo folder | `docs/archive/audit_arsitktur/` | `docs/archive/` |
| PNG nama uppercase | `docs/discover.PNG`, `docs/player.PNG`, dll. | `docs/` |
| Import path lama | `main.py` baris 16 import dari `integrations.termux_notification` | `main.py` |
| engine rename belum dilakukan | `queue_mode.py`, `radio_mode.py` masih nama lama | `engine/` |
| integrations/ belum di-rename | Folder masih `integrations/`, bukan `plugins/` | root |
| `playback_controller.py` import langsung dari `integrations/` | Melanggar architecture lock (engine → plugins dilarang) | `engine/playback_controller.py` |
| Tests flat tanpa struktur domain | 20+ file `test_patch_*_*.py` di root `tests/` | `tests/` |
| `tui/` dead code | Tidak diimport oleh siapapun, `textual` tidak ada di `requirements.txt` | `tui/` |

### 1.5 Catatan: tui/ adalah Dead Code

`tui/` (10 file, ~47KB, berbasis `textual`) tidak diimport oleh `main.py`, `server.py`, atau test manapun. `textual` tidak ada di `requirements.txt` maupun `requirements-dev.txt`. Folder ini harus dihapus. Lihat Fase 0 untuk prosedur safe delete.

README.md menyebut TUI — update wajib dilakukan bersamaan dengan delete.

---

## 2. Arsitektur Target

### 2.1 Backend: Clean Layered Architecture

```
[main.py]    ← HANYA: setup logging, load config, panggil bootstrap
    ↓
[server/]    ← HTTP + WebSocket layer (aiohttp)
    ↓
[engine/]    ← Playback domain (mpv, yt-dlp, queue, radio)
    ↓
[core/]      ← Shared infrastructure (bus, state, ports, security)
    ↓
[cache/]     ← Persistence (SQLite, file resolver)
    ↓
[plugins/]   ← External integrations (lyrics, sponsorblock, notifications)
```

**Aturan besi import:**
```
core    ← tidak import siapapun dari domain ini
engine  ← boleh import core dan plugins (via port/interface, bukan direct)
server  ← boleh import core, engine
main    ← boleh import semua (hanya untuk wiring)
plugins ← boleh import core saja
```

> ⚠️ CATATAN: `engine/playback_controller.py` saat ini import langsung dari `integrations/` (lyrics, sponsorblock). Ini violation. Fase 3 wajib memperbaiki ini — akses plugins dari engine harus melalui port yang didefinisikan di `core/ports.py`, bukan direct import.

### 2.2 Frontend: Unidirectional Data Flow

```
WebSocket ──→ ws.js ──→ store.js ──→ render/*.js ──→ DOM
                                           ↑
                                      events.js ──→ wsSend() ──→ Server
```

**Aturan besi frontend:**
- `render/*.js` hanya boleh: baca `store` → update DOM. Tidak boleh call `wsSend()`.
- `events.js` satu-satunya tempat semua `addEventListener()`.
- `store.js` satu-satunya tempat state disimpan.
- `dom.js` satu-satunya tempat `document.getElementById()` dipanggil.
- `tokens.css` satu-satunya tempat nilai warna/spacing ditulis.

---

## 3. Design Token System (WAJIB SESUAI MOCKUP)

> ⚠️ KRITIS: Ini root cause dari UI yang hancur. Tambahkan blok ini sebagai **baris pertama** `style.css` (sebelum `@import`).

### 3.1 Blok `:root {}` yang Benar

```css
/* ============================================================
   bagas.fm Design Tokens — SINGLE SOURCE OF TRUTH
   Dibuat dari: bagas_fm_ui_mockup.html + 5 PNG mockup
   JANGAN EDIT nilai di sini tanpa update mockup juga.
   ============================================================ */
:root {
  /* --- Background System --- */
  --fm-bg-deep:     #0d0d1c;
  --fm-bg-card:     #141426;
  --fm-bg-elevated: #1e1e38;
  --fm-bg-overlay:  #0f0f20;

  /* --- Accent Colors --- */
  --fm-accent:      #e040fb;
  --fm-accent-dim:  #c020d0;
  --fm-accent-bg:   #2a1540;
  --fm-cyan:        #00e5ff;
  --fm-teal:        #00e5b0;
  --fm-green:       #00c870;
  --fm-warn:        #f0b429;
  --fm-err:         #ef4444;
  --fm-blue:        #60a5fa;

  /* --- Text Hierarchy --- */
  --fm-text-1:      #f0f0ff;
  --fm-text-2:      #e8e8f5;
  --fm-text-3:      #9a9abc;
  --fm-text-4:      #6a6a8c;
  --fm-text-5:      #5a5a7a;

  /* --- Borders --- */
  --fm-border:      #1e1e32;
  --fm-border-2:    #2e2e48;

  /* --- Typography --- */
  --fm-font:        -apple-system, system-ui, sans-serif;

  /* --- Spacing --- */
  --fm-radius-xs:   4px;
  --fm-radius-sm:   8px;
  --fm-radius-md:   12px;
  --fm-radius-lg:   16px;
  --fm-radius-xl:   20px;
  --fm-radius-pill: 20px;
  --fm-radius-app:  36px;

  /* --- Shadows --- */
  --fm-shadow-sm:   0 2px 8px rgba(0,0,0,0.4);
  --fm-shadow-md:   0 4px 16px rgba(0,0,0,0.5);

  /* --- Transitions --- */
  --fm-transition-fast:   0.15s ease;
  --fm-transition-normal: 0.25s ease;

  /* ============================================================
     LEGACY ALIASES — bridge untuk style.css yang masih pakai nama lama.
     Hapus bagian ini setelah Phase 1 CSS split selesai.
     ============================================================ */
  --accent-fire:      #e040fb;
  --bg-panel:         #141426;
  --bg-elevated:      #1e1e38;
  --bg-void:          #0d0d1c;
  --bg-glass:         rgba(20,20,38,0.92);
  --accent-gold:      #f0b429;
  --accent-blue:      #60a5fa;
  --status-err:       #ef4444;
  --text-primary:     #f0f0ff;
  --text-muted:       #6a6a8c;
  --text-dim:         #5a5a7a;
  --border:           #1e1e32;
  --font-family:      -apple-system, system-ui, sans-serif;
  --radius-sm:        8px;
  --radius-md:        12px;
  --radius-lg:        16px;
  --radius-xl:        20px;
  --radius-full:      9999px;
  --shadow-md:        0 2px 8px rgba(0,0,0,0.4);
  --shadow-lg:        0 4px 16px rgba(0,0,0,0.5);
  --transition-fast:  0.15s ease;
  --transition-normal:0.25s ease;
}
```

### 3.2 Mapping Lama → Baru (untuk Phase 1 CSS Split)

Saat membuat `css/tokens.css`, gunakan nama `--fm-*` saja. Hapus Legacy Aliases. Lakukan search-replace di semua CSS file:

| Variable Lama | Variable Baru | Nilai |
|---|---|---|
| `var(--accent-fire)` | `var(--fm-accent)` | `#e040fb` |
| `var(--bg-panel)` | `var(--fm-bg-card)` | `#141426` |
| `var(--bg-elevated)` | `var(--fm-bg-elevated)` | `#1e1e38` |
| `var(--bg-void)` | `var(--fm-bg-deep)` | `#0d0d1c` |
| `var(--bg-glass)` | `rgba(20,20,38,0.92)` (inline ok) | — |
| `var(--accent-gold)` | `var(--fm-warn)` | `#f0b429` |
| `var(--accent-blue)` | `var(--fm-blue)` | `#60a5fa` |
| `var(--status-err)` | `var(--fm-err)` | `#ef4444` |
| `var(--text-primary)` | `var(--fm-text-1)` | `#f0f0ff` |
| `var(--text-muted)` | `var(--fm-text-4)` | `#6a6a8c` |
| `var(--text-dim)` | `var(--fm-text-5)` | `#5a5a7a` |
| `var(--border)` | `var(--fm-border)` | `#1e1e32` |
| `var(--font-family)` | `var(--fm-font)` | system-ui |
| `var(--radius-sm)` | `var(--fm-radius-sm)` | `8px` |
| `var(--radius-md)` | `var(--fm-radius-md)` | `12px` |
| `var(--radius-lg)` | `var(--fm-radius-lg)` | `16px` |
| `var(--radius-xl)` | `var(--fm-radius-xl)` | `20px` |
| `var(--radius-full)` | `var(--fm-radius-pill)` | `9999px` |
| `var(--shadow-md)` | `var(--fm-shadow-sm)` | — |
| `var(--shadow-lg)` | `var(--fm-shadow-md)` | — |
| `var(--transition-fast)` | `var(--fm-transition-fast)` | `0.15s ease` |
| `var(--transition-normal)` | `var(--fm-transition-normal)` | `0.25s ease` |

### 3.3 Badge Color System

```css
.pb-badge          { background: #2a1540; color: #e040fb; }
.pb-badge.queue    { background: #1a2240; color: #60a5fa; }
.pb-badge.cache    { background: #122212; color: #00c870; }
.pb-badge.stream   { background: #1a1a2e; color: #9a9abc; }
```

### 3.4 Komponen Kritis

**Container App:**
```css
#app {
  max-width: 375px;
  width: 100%;
  margin: 0 auto;
  background: var(--fm-bg-deep);
  border-radius: var(--fm-radius-app);
  border: 3px solid var(--fm-border);
  height: 690px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}
```

**Flex structure wajib:**
```
#app                    (flex column, height: 690px)
├── #app-header         (flex-shrink: 0)
├── #content-area       (flex: 1, overflow-y: auto)
├── #player-bar         (flex-shrink: 0)
└── .nav-row            (flex-shrink: 0)
```

---

## 4. Struktur Folder Target

```
bagas.fm/
│
├── main.py                          # Entry point — HANYA wiring & startup (<100 baris)
├── config.py                        # ENV vars, konstanta, password bootstrap
├── requirements.txt
├── requirements-dev.txt
├── start.sh
├── start.bat
├── .gitignore
│
├── core/
│   ├── __init__.py
│   ├── command_bus.py
│   ├── event_bus.py
│   ├── events.py
│   ├── exceptions.py
│   ├── log_config.py
│   ├── observability.py
│   ├── ports.py
│   ├── room_manager.py
│   ├── security.py
│   ├── state.py
│   └── task_utils.py
│
├── engine/
│   ├── __init__.py
│   ├── command_router.py
│   ├── download_manager.py
│   ├── mpv_controller.py
│   ├── playback_controller.py
│   ├── queue_manager.py             # ← RENAME dari queue_mode.py
│   ├── radio_engine.py              # ← RENAME dari radio_mode.py
│   ├── volume_service.py
│   └── ytdlp_client.py
│
├── cache/
│   ├── __init__.py
│   ├── db.py
│   ├── resolver.py
│   └── schema.sql
│
├── plugins/                         # ← RENAME dari integrations/
│   ├── __init__.py
│   ├── lyrics.py
│   ├── sponsorblock.py
│   └── notifications.py             # ← RENAME dari termux_notification.py
│
├── services/
│   ├── __init__.py
│   └── discover_service.py          # KEEP — tidak diubah
│
├── server/                          # ← PECAHAN dari web/server.py
│   ├── __init__.py
│   ├── app.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── http.py
│   │   ├── websocket.py
│   │   └── auth.py
│   ├── serializers.py
│   └── middleware.py
│
├── web/
│   └── static/
│       ├── index.html
│       │
│       ├── css/
│       │   ├── tokens.css
│       │   ├── base.css
│       │   ├── layout.css
│       │   ├── player.css
│       │   ├── tabs.css
│       │   ├── components.css
│       │   └── portal.css
│       │
│       └── js/
│           ├── config.js
│           ├── store.js
│           ├── dom.js
│           ├── ws.js
│           ├── portal.js
│           ├── eq.js
│           ├── audio.js
│           ├── utils.js
│           ├── events.js
│           ├── main.js
│           └── render/
│               ├── player.js
│               ├── tabs.js
│               ├── lyrics.js
│               └── search.js
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── core/
│   │   ├── engine/
│   │   ├── cache/
│   │   ├── server/
│   │   └── plugins/
│   ├── integration/
│   │   └── test_e2e.py
│   └── fixtures/
│       └── sample_track.json
│
├── scripts/                         # ← RENAME dari widgets/
│   └── shortcuts/
│       ├── next_track.sh
│       ├── play_pause.sh
│       └── volume_up.sh
│
└── docs/
    ├── README.md
    ├── MANUAL_BOOK.md
    ├── CONTRIBUTING.md
    ├── ARCHITECTURE.md
    ├── mockups/
    │   ├── bagas_fm_ui_mockup.html
    │   ├── discover.png
    │   ├── player.png
    │   ├── queue.png
    │   ├── radio.png
    │   └── search.png
    └── archive/
        └── (semua file audit lama, tidak diubah)
```

**Catatan:** `tui/` tidak ada di target struktur — dihapus di Fase 0.

---

## 5. Peta Migrasi Exhaustive

### 5.1 Backend Python

| File Saat Ini | File Target | Aksi |
|---|---|---|
| `main.py` | `main.py` | TRIM → < 100 baris, hanya wiring |
| `config.py` | `config.py` | KEEP |
| `core/*.py` | `core/*.py` | KEEP |
| `engine/queue_mode.py` | `engine/queue_manager.py` | RENAME |
| `engine/radio_mode.py` | `engine/radio_engine.py` | RENAME |
| `engine/playback_controller.py` | `engine/playback_controller.py` | REFACTOR import (lihat catatan Fase 3) |
| `integrations/` (folder) | `plugins/` (folder) | RENAME FOLDER |
| `integrations/termux_notification.py` | `plugins/notifications.py` | RENAME |
| `integrations/lyrics.py` | `plugins/lyrics.py` | PINDAH |
| `integrations/sponsorblock.py` | `plugins/sponsorblock.py` | PINDAH |
| `services/discover_service.py` | `services/discover_service.py` | KEEP |
| `web/server.py` (700 baris) | `server/app.py` + `server/handlers/*.py` + `server/serializers.py` + `server/middleware.py` | PECAH |
| `web/__init__.py` | (dihapus) | DELETE |
| `tui/` (seluruh folder) | (dihapus) | DELETE — lihat Fase 0 |

**Import yang harus diupdate setelah rename:**

```python
# main.py baris 16:
from integrations.termux_notification import TermuxNowPlaying
# → ganti ke:
from plugins.notifications import TermuxNowPlaying

# engine/playback_controller.py:
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher
from engine.queue_mode import QueueMode
from engine.radio_mode import RadioMode
# → ganti ke (Fase 4):
from plugins.sponsorblock import SponsorBlockHandler
from plugins.lyrics import LyricsFetcher
from engine.queue_manager import QueueManager
from engine.radio_engine import RadioEngine

# main.py (Fase 3) — ganti import server:
# from web.server import ... → from server.app import ...
```

### 5.2 Frontend CSS

Gunakan anchor komentar berikut (terverifikasi dari codebase) untuk menentukan batas split:

| File Target | Anchor Mulai | Anchor Selesai | Konten |
|---|---|---|---|
| `css/tokens.css` | (baru — tidak ada di style.css saat ini) | — | **HANYA** blok `:root {}` dari Bagian 3.1 |
| `css/base.css` | baris 1 (`@import url(...)`) | sebelum baris 175 | `@import`, `html/body`, `* {box-sizing}`, scrollbar, media query mobile |
| `css/layout.css` | `/* ══ ... Player Bar ... ══ */` (baris 175) | sebelum baris 253 | `#app`, `#app-header`, `#content-area`, `#player-bar`, `.nav-row` |
| `css/player.css` | `/* ══ ... Controls ... ══ */` (baris 253) | sebelum baris 341 | seek bar, controls, vol slider, badges, EQ canvas, log toast |
| `css/portal.css` | `/* ══ ... Portal ... ══ */` (baris 341) | sebelum baris 547 | `#portal-screen`, `.portal-card`, `.portal-login-form`, error state |
| `css/components.css` | `/* ══ ... Player Extras ... ══ */` (baris 547) | sebelum baris 791 | volume slider, queue drag, lyrics header, settings sheet, toggle, btn |
| `css/tabs.css` | `/* ── Tab Discover ── */` (baris 791) | sebelum baris 982 | tab discover, radio tab, seed chips |
| (sisa baris 982–992) | `/* ══ ... Animations ... ══ */` (baris 982) | EOF | animasi — masukkan ke `css/components.css` |

**Load order wajib di `index.html`:**
```html
<link rel="stylesheet" href="/static/css/tokens.css">     <!-- 1st: WAJIB PERTAMA -->
<link rel="stylesheet" href="/static/css/base.css">
<link rel="stylesheet" href="/static/css/layout.css">
<link rel="stylesheet" href="/static/css/player.css">
<link rel="stylesheet" href="/static/css/tabs.css">
<link rel="stylesheet" href="/static/css/components.css">
<link rel="stylesheet" href="/static/css/portal.css">     <!-- last -->
```

### 5.3 Frontend JS

| Fungsi di app.js | File Target |
|---|---|
| `const SEED_ARTISTS`, constants, `TAB_IDS` | `js/config.js` |
| `const store`, `updateStore()` | `js/store.js` |
| `const dom = { ... }` | `js/dom.js` |
| `wsConnect()`, `wsSend()`, `handleServerMessage()` | `js/ws.js` |
| `renderPlayerBar()`, `renderProgress()`, `renderPlayBtn()` | `js/render/player.js` |
| `renderNowPlaying()`, `renderQueue()`, `renderRadio()`, `renderDiscoverTab()`, `renderRecentRow()` | `js/render/tabs.js` |
| `renderLyrics()`, `updateOffsetDisplay()` | `js/render/lyrics.js` |
| `renderSearchResults()`, `showActionModal()`, `hideActionModal()` | `js/render/search.js` |
| `formatTime()`, `escapeHtml()` | `js/utils.js` |
| `tickEQ()`, `startEQ()`, canvas logic | `js/eq.js` |
| `unlockBrowserAudio()`, `syncBrowserAudio()`, `getOrInitAudio()` | `js/audio.js` |
| `logout()`, portal logic, session check | `js/portal.js` |
| Semua `addEventListener()` calls | `js/events.js` |
| `switchTab()`, init sequence | `js/main.js` |

> ⚠️ PERHATIAN: Saat ini `app.js` memiliki `addEventListener()` dan `wsSend()` di dalam fungsi render (baris 378, 410, 438, 466, 600, 609, 696, 715, 722, 734, dll). Ini violation Laws 6 & 7. Saat ekstraksi ke `render/*.js`, semua listener harus dipindahkan ke `events.js` dan semua `wsSend()` calls harus direfactor ke pattern event/callback yang dipanggil dari `events.js`.

**Load order wajib di `index.html`:**
```html
<script src="/static/js/config.js"></script>
<script src="/static/js/store.js"></script>
<script src="/static/js/dom.js"></script>
<script src="/static/js/utils.js"></script>
<script src="/static/js/render/player.js"></script>
<script src="/static/js/render/tabs.js"></script>
<script src="/static/js/render/lyrics.js"></script>
<script src="/static/js/render/search.js"></script>
<script src="/static/js/eq.js"></script>
<script src="/static/js/audio.js"></script>
<script src="/static/js/ws.js"></script>
<script src="/static/js/portal.js"></script>
<script src="/static/js/events.js"></script>
<script src="/static/js/main.js"></script>  <!-- TERAKHIR, selalu -->
```

### 5.4 Server Split

`web/server.py` (700 baris) dipecah:

```
server/app.py           ← create_app(), setup_routes(), run_server()
server/handlers/http.py ← serve_index(), serve_static(), health_check()
server/handlers/websocket.py ← ws_handler(), _handle_ws_message(), ConnectionManager
server/handlers/auth.py ← login_handler(), logout_handler(), require_auth decorator
server/serializers.py   ← _track_to_dict(), _state_to_dict(), _dict_to_track()
server/middleware.py    ← logging_middleware(), rate_limit_middleware()
```

> ⚠️ URUTAN PENTING: Update `main.py` untuk import dari `server.app` **sebelum** menghapus `web/server.py`. Jangan hapus file lama sebelum import baru sudah berjalan dan `pytest` pass.

### 5.5 Tests Reorganization

| File Lama | File Target |
|---|---|
| `test_patch_0_01_appstate_duration.py` | `unit/core/test_app_state.py` |
| `test_patch_0_02_lyrics_session.py` | `unit/cache/test_lyrics_cache.py` |
| `test_patch_0_03_upsert_temp.py` | `unit/cache/test_db_upsert.py` |
| `test_patch_0_04_ttl_mismatch.py` | `unit/cache/test_db_ttl.py` |
| `test_patch_0_09_10_11_server_perf.py` | `unit/server/test_ws_performance.py` |
| `test_patch_1_01_02_safe_create_task.py` | `unit/core/test_task_utils.py` |
| `test_patch_1_03_eventbus_concurrent.py` | `unit/core/test_event_bus_concurrent.py` |
| `test_patch_1_04_queue_remove_lock.py` | `unit/engine/test_queue_locking.py` |
| `test_patch_1_05_lyrics_generation.py` | `unit/plugins/test_lyrics.py` |
| `test_patch_1_06_radio_circuit_breaker.py` | `unit/engine/test_radio_circuit_breaker.py` |
| `test_patch_1_07_server_timestamp.py` | `unit/server/test_serializers.py` |
| `test_patch_1_08_12_ssrf_path.py` | `unit/server/test_ssrf_guard.py` |
| `test_patch_1_09_password_hashing.py` | `unit/server/test_auth.py` |
| `test_patch_1_10_cleanup.py` | `unit/core/test_cleanup.py` |
| `test_patch_1_11_session_persistence.py` | `unit/server/test_session.py` |
| `test_patch_2_02_command_bus.py` | `unit/core/test_command_bus.py` |
| `test_patch_2_04_audio_output_enum.py` | `unit/core/test_audio_output_enum.py` |
| `test_patch_3_01_07_per_room_eventbus.py` | `unit/core/test_room_event_bus.py` |
| `test_patch_fase0_quick_wins.py` | `unit/test_smoke.py` |
| `test_patch_fase1_security.py` | `unit/server/test_security.py` |
| `test_domain_events.py` | `unit/core/test_domain_events.py` |
| `test_event_bus.py` | `unit/core/test_event_bus.py` |

### 5.6 Docs & Misc

| Lama | Baru | Aksi |
|---|---|---|
| `docs/bagas_fm_ui_mockup.html` | `docs/mockups/bagas_fm_ui_mockup.html` | PINDAH |
| `docs/discover.PNG` | `docs/mockups/discover.png` | PINDAH + lowercase |
| `docs/player.PNG` | `docs/mockups/player.png` | PINDAH + lowercase |
| `docs/queue.PNG` | `docs/mockups/queue.png` | PINDAH + lowercase |
| `docs/radio.PNG` | `docs/mockups/radio.png` | PINDAH + lowercase |
| `docs/search.PNG` | `docs/mockups/search.png` | PINDAH + lowercase |
| `web/static/switchTab.txt` | (hapus) | DELETE |
| `docs/archive/audit_arsitktur/` | `docs/archive/audit_arsitektur/` | FIX TYPO |
| `widgets/shortcuts/` | `scripts/shortcuts/` | RENAME folder |
| `tui/` | (hapus) | DELETE — lihat Fase 0 |
| `README.md` | `README.md` | UPDATE — hapus section TUI |

---

## 6. Urutan Fase Eksekusi

### ⚡ Fase 0 — Critical Fixes & Safe Delete (< 2 jam, LAKUKAN PERTAMA)

#### 0A. Fix CSS (bug utama)
- [ ] **0A.1** Tambahkan blok `:root {}` dari **Bagian 3.1** sebagai **BARIS PERTAMA** `web/static/style.css`, sebelum `@import`
- [ ] **0A.2** Verifikasi dengan `grep -n ":root" web/static/style.css` — harus muncul di baris 1
- [ ] **0A.3** Verifikasi dengan `grep -c "var(--accent-fire)" web/static/style.css` — harus > 0 (ada yang pakai token)

#### 0B. Safe Delete tui/
> Prosedur ini aman karena `tui/` sudah diverifikasi tidak diimport oleh siapapun.

- [ ] **0B.1** Verifikasi tidak ada yang import tui:
  ```bash
  grep -r "from tui\|import tui" --include="*.py" . | grep -v "tui/"
  ```
  Output harus kosong. Jika ada hasil → STOP, laporkan.
- [ ] **0B.2** Verifikasi `textual` tidak ada di requirements:
  ```bash
  grep -i textual requirements.txt requirements-dev.txt
  ```
  Output harus kosong. Jika ada → STOP, laporkan.
- [ ] **0B.3** Hapus folder:
  ```bash
  rm -rf tui/
  ```
- [ ] **0B.4** Verifikasi `pytest tests/` masih PASS setelah delete.
- [ ] **0B.5** Update `README.md` — hapus bullet point tentang "TUI Interaktif & Clickable".

#### 0C. Cleanup minor
- [ ] **0C.1** Hapus `web/static/switchTab.txt`
- [ ] **0C.2** Rename `docs/archive/audit_arsitktur/` → `audit_arsitektur/` (fix typo)
- [ ] **0C.3** Lowercase semua `.PNG` → `.png` di `docs/`
- [ ] **0C.4** Jalankan `pytest tests/` — harus PASS

- [ ] **0.COMMIT** `fix(css): add :root design tokens; chore: remove dead tui/ code`

**Checklist visual setelah Fase 0A:**
- Background hitam (`#0d0d1c`) ✓
- Play button ungu (`#e040fb`) ✓
- Progress bar fill ungu ✓
- Status dot teal-green (`#00e5b0`) ✓

---

### 🎨 Fase 1 — CSS Split (Hari 1–2)

- [ ] **1.1** Buat folder `web/static/css/`
- [ ] **1.2** Buat `css/tokens.css` — **HANYA** blok `:root {}` dengan `--fm-*` (tanpa legacy aliases)
- [ ] **1.3** Split `style.css` ke 6 file menggunakan anchor dari **Bagian 5.2**
- [ ] **1.4** Jalankan mapping **Bagian 3.2** — replace semua `var(--old-*)` ke `var(--fm-*)` di semua file CSS baru
- [ ] **1.5** Update `index.html`: ganti `<link href="style.css">` dengan 7 link berurutan (lihat Bagian 5.2)
- [ ] **1.6** Hapus `style.css` lama
- [ ] **1.7** Verifikasi: `grep -r "var(--accent-fire\|var(--bg-panel\|var(--bg-elevated" web/static/css/` — harus kosong (semua sudah di-replace)
- [ ] **1.8** Verifikasi visual — identik dengan sebelum split
- [ ] **1.COMMIT** `refactor(css): split style.css into 7 focused files with fm-* tokens`

---

### 🔧 Fase 2 — JS Split (Hari 2–4)

- [ ] **2.1** Buat folder `web/static/js/` dan `web/static/js/render/`
- [ ] **2.2** Ekstrak file-file JS sesuai peta di **Bagian 5.3**
- [ ] **2.3** Saat ekstraksi `render/*.js`: pindahkan semua `addEventListener()` ke `events.js`, refactor `wsSend()` calls agar dipanggil dari `events.js` (bukan dari dalam render function)
- [ ] **2.4** Buat `js/main.js`:
  ```javascript
  (function () {
    "use strict";
    initDOM();
    initPortal();
    initEvents();
    initEQ();
    wsConnect();
  })();
  ```
- [ ] **2.5** Update `index.html`: ganti 1 `<script>` → 14 `<script>` berurutan (lihat Bagian 5.3)
- [ ] **2.6** Hapus `app.js` lama
- [ ] **2.7** Verifikasi: `grep -r "addEventListener" web/static/js/render/` — harus kosong
- [ ] **2.8** Verifikasi: `grep -r "wsSend" web/static/js/render/` — harus kosong
- [ ] **2.9** Verifikasi fungsional: semua 5 tab berfungsi, WS connect, EQ animasi, search/play/queue
- [ ] **2.COMMIT** `refactor(js): split app.js into 14 focused modules`

---

### 🏗️ Fase 3 — Backend Split (Hari 4–6)

- [ ] **3.1** Buat folder `server/` dengan `__init__.py` dan `handlers/`
- [ ] **3.2** Ekstrak `server/serializers.py` terlebih dahulu (tidak ada dependency ke file server lain)
- [ ] **3.3** Ekstrak `server/handlers/auth.py`
- [ ] **3.4** Ekstrak `server/handlers/http.py`
- [ ] **3.5** Ekstrak `server/handlers/websocket.py`
- [ ] **3.6** Ekstrak `server/middleware.py`
- [ ] **3.7** Buat `server/app.py`
- [ ] **3.8** Update `main.py`: ganti import `from web.server import ...` → `from server.app import ...` **sebelum** menghapus file lama
- [ ] **3.9** Jalankan `pytest tests/` — harus PASS sebelum lanjut
- [ ] **3.10** Hapus `web/server.py` dan `web/__init__.py`
- [ ] **3.11** Fix architecture violation di `engine/playback_controller.py`: akses `plugins/lyrics` dan `plugins/sponsorblock` harus melalui port yang didefinisikan di `core/ports.py`, bukan direct import. Tambahkan port baru jika belum ada.
- [ ] **3.12** Jalankan `pytest tests/` — harus PASS
- [ ] **3.COMMIT** `refactor(server): split server.py into handler modules; fix engine→plugins violation`

---

### 📁 Fase 4 — Rename & Reorganize (Hari 6–7)

- [ ] **4.1** Rename `engine/queue_mode.py` → `engine/queue_manager.py`
- [ ] **4.2** Rename `engine/radio_mode.py` → `engine/radio_engine.py`
- [ ] **4.3** Rename folder `integrations/` → `plugins/`
- [ ] **4.4** Rename `plugins/termux_notification.py` → `plugins/notifications.py`
- [ ] **4.5** Rename folder `widgets/` → `scripts/`
- [ ] **4.6** Buat `docs/mockups/` dan pindahkan HTML mockup + PNG (lowercase)
- [ ] **4.7** Update **SEMUA** import yang terpengaruh rename (lihat Bagian 5.1)
- [ ] **4.8** Jalankan `pytest tests/` — harus PASS
- [ ] **4.COMMIT** `refactor: rename files and folders for clarity`

---

### 🧪 Fase 5 — Tests Reorganize (Hari 7–8)

- [ ] **5.1** Buat `tests/unit/` dengan subfolder: `core/`, `engine/`, `cache/`, `server/`, `plugins/`
- [ ] **5.2** Buat `tests/fixtures/sample_track.json`
- [ ] **5.3** Rename dan pindahkan semua `test_patch_*` sesuai peta di **Bagian 5.5**
- [ ] **5.4** Update `conftest.py` jika ada path-sensitive fixture
- [ ] **5.5** Verifikasi: `pytest tests/` harus PASS semua
- [ ] **5.COMMIT** `refactor(tests): reorganize into domain-based folders`

---

### 📝 Fase 6 — Documentation (Hari 8–9)

- [ ] **6.1** Buat `docs/CONTRIBUTING.md` — panduan kontributor + Laws of Codebase
- [ ] **6.2** Buat `docs/ARCHITECTURE.md` — diagram arsitektur + keputusan desain
- [ ] **6.3** Update `README.md` — struktur folder baru, cara setup, cara run (TUI sudah dihapus di Fase 0)
- [ ] **6.COMMIT** `docs: add CONTRIBUTING and ARCHITECTURE guides`

---

## 7. Laws of This Codebase

```
╔══════════════════════════════════════════════════════════════╗
║                  LAWS OF THIS CODEBASE                       ║
╠══════════════════════════════════════════════════════════════╣
║  BACKEND                                                     ║
║                                                              ║
║  LAW 1 — IMPORT DIRECTION                                    ║
║    core ← engine ← server ← main  (satu arah)               ║
║    core TIDAK BOLEH import dari engine atau server           ║
║    engine TIDAK BOLEH import dari server                     ║
║    engine boleh akses plugins HANYA via port di core/ports   ║
║                                                              ║
║  LAW 2 — COMMANDS go DOWN                                    ║
║    main dispatch ke engine via command_bus                   ║
║    engine TIDAK BOLEH tahu tentang WebSocket atau HTTP       ║
║                                                              ║
║  LAW 3 — EVENTS go UP                                        ║
║    engine publish events, server subscribe                   ║
║    Tidak ada direct call dari engine ke server               ║
║                                                              ║
║  LAW 4 — main.py = wiring only                               ║
║    Tidak ada business logic di main.py                       ║
║    Target: < 100 baris                                       ║
║                                                              ║
║  FRONTEND                                                    ║
║                                                              ║
║  LAW 5 — TOKENS ONLY di tokens.css                           ║
║    Tidak ada hex color (#xxxxx) di file CSS lain. EVER.      ║
║                                                              ║
║  LAW 6 — RENDER FUNCTIONS = pure I/O                         ║
║    Input: baca store.* → Output: update DOM                  ║
║    Render functions TIDAK BOLEH call wsSend()                ║
║    Render functions TIDAK BOLEH call addEventListener()      ║
║                                                              ║
║  LAW 7 — EVENTS ONLY di events.js                            ║
║    Tidak ada inline onclick di HTML                          ║
║    Tidak ada addEventListener() di luar events.js            ║
║                                                              ║
║  LAW 8 — STORE = satu-satunya state                          ║
║    Tidak ada state di DOM (jangan pakai dataset)             ║
║                                                              ║
║  LAW 9 — DOM CACHE di dom.js                                 ║
║    Tidak ada document.getElementById() di luar dom.js        ║
║                                                              ║
║  LAW 10 — TAB CONTENT = JS-driven                            ║
║    Setiap tab adalah fungsi yang return HTML string          ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 8. Konvensi Penamaan

### Python Files
```
engine/queue_manager.py   ✅
engine/radio_engine.py    ✅
plugins/notifications.py  ✅
server/handlers/auth.py   ✅
tests/unit/core/test_event_bus.py  ✅

test_patch_1_03_eventbus.py  ❌
```

### CSS Class Naming (BEM-lite)
```css
.player-bar { }
.player-bar__seek { }
.nav-btn--active { }
.is-loading { }
```

### Git Commits (Conventional Commits)
```
feat(engine): add gapless playback support
fix(css): add missing :root token block
refactor(server): extract auth handler from server.py
chore: remove dead tui/ code
```

---

## 9. Checklist Contributor

**CSS:**
- [ ] Tidak ada hex color literal di luar `tokens.css`
- [ ] Pakai `var(--fm-*)` untuk semua nilai visual
- [ ] `tokens.css` adalah file pertama yang di-load

**JavaScript:**
- [ ] `store.js` diupdate jika ada state baru
- [ ] `dom.js` diupdate jika ada elemen HTML baru
- [ ] `events.js` untuk setiap event listener baru
- [ ] `render/*.js` untuk render logic baru
- [ ] Tidak ada inline `onclick` di HTML
- [ ] Tidak ada `wsSend()` di `render/*.js`

**Python:**
- [ ] Import sesuai arah: `core` tidak import dari `engine`/`server`
- [ ] `engine` akses `plugins` hanya via port
- [ ] `main.py` hanya wiring (< 100 baris)
- [ ] Tidak ada logic bisnis di handler WebSocket

**Tests:**
- [ ] Test baru di `tests/unit/{domain}/`
- [ ] Nama file: `test_{concern}.py`
- [ ] `pytest tests/` pass sebelum push

**Git:**
- [ ] Format: `type(scope): description`

---

## Appendix A — File Kritis (Tidak Boleh Diubah Tanpa Diskusi)

| File | Mengapa Kritis |
|---|---|
| `core/ports.py` | Interface contract untuk semua layer |
| `core/events.py` | Event type definitions |
| `core/state.py` | AppState, enum — digunakan di seluruh codebase |
| `cache/schema.sql` | Database schema — perubahan perlu migration |
| `config.py` | Password bootstrap — security sensitive |

## Appendix B — File yang Dihapus Setelah Refactor

| File | Kapan Dihapus |
|---|---|
| `tui/` (seluruh folder) | Fase 0 |
| `web/static/style.css` | Setelah Fase 1 verified |
| `web/static/app.js` | Setelah Fase 2 verified |
| `web/server.py` | Setelah Fase 3 step 3.9 pass |
| `web/__init__.py` | Setelah Fase 3 |
| `web/static/switchTab.txt` | Fase 0 |
| `engine/queue_mode.py` | Setelah Fase 4 + import diupdate |
| `engine/radio_mode.py` | Setelah Fase 4 + import diupdate |

---

*Dokumen ini adalah sumber kebenaran tunggal. Jika ada keputusan arsitektur baru, update dokumen ini terlebih dahulu sebelum menulis kode.*
