# AUDIT LAPORAN V2 — bagas.fm
### Target: Spotify-Class Mobile-First Application
*Auditor: Claude Sonnet 4.6 — Full Stack + UX + Security + Performance*
*Tanggal: 24 Juni 2026 — Revisi V2 berdasarkan Meta-Review*

> **Catatan V2:** Dokumen ini adalah revisi dari V1 berdasarkan meta-review yang menemukan gap signifikan di area product architecture, design system, desktop blueprint, accessibility strategy, dan component architecture. Chapter baru (A–H) ditambahkan untuk menutup gap tersebut.

---

## Executive Summary

bagas.fm adalah pemutar musik YouTube yang dibangun di atas Python/aiohttp backend + vanilla JS frontend. Arsitektur backend sudah solid — ada event bus, command routing, room manager, dan clean separation of concerns. **Masalah utamanya ada di frontend**: aplikasi ini secara fundamental dirancang sebagai *phone mockup di dalam browser*, bukan sebagai *real responsive web application*.

Gap terbesar menuju Spotify-class: `#app { max-width: 375px; height: 690px }` — satu baris CSS yang mengunci seluruh aplikasi menjadi kotak iPhone 8 statis, tidak peduli apakah dibuka di tablet, laptop, atau Smart TV.

**Definisi "Spotify-class" untuk bagas.fm:**
Mengingat bagas.fm adalah personal music player yang berjalan di Termux dan diakses via browser lokal (bukan streaming service skala global), "Spotify-class" dalam konteks ini berarti:
1. **Layout responsif nyata** — bukan phone-in-browser, tapi full-viewport adaptive layout di semua ukuran layar
2. **Touch gesture yang bekerja** — queue reorder, swipe navigasi, progress drag di mobile
3. **Visual polish** — micro-animation, spacing sistematis, tipografi konsisten
4. **Aksesibilitas dasar** — keyboard navigasi, screen reader minimal, contrast adequate

---

## Scorecard

| Dimensi | Skor | Status |
|---------|------|--------|
| UI Score | 38/100 | ❌ |
| UX Score | 45/100 | ⚠️ |
| Code Quality Score | 55/100 | ⚠️ |
| Architecture Score (Backend) | 72/100 | ✅ |
| Architecture Score (Frontend) | 40/100 | ❌ |
| Performance Score | 48/100 | ⚠️ |
| Security Score | 62/100 | ⚠️ |
| Scalability Score | 25/100 | ❌ |

**Production Ready? → NO**

Alasan: Phone-shell layout tidak bisa digunakan di tablet/desktop. `--fm-primary` undefined menyebabkan fitur drag-and-drop dan current track indicator rusak visual. Queue drag-drop tidak bekerja di mobile touch.

---

## CHAPTER A — PRODUCT & INFORMATION ARCHITECTURE AUDIT *(BARU)*

> **Mengapa chapter ini ada:** Tanpa pemahaman IA, layout yang dibangun di Phase 1–4 tidak punya arah konten yang jelas. Desktop Phase 5 khususnya tidak bisa didesain tanpa tahu konten apa yang tampil di sidebar.

### A.1 User Journey Map

```
Entry
  └─► Portal Screen (pilih role: Client / Admin)
         │
         ▼
      Tab: Home (Now Playing)
         ├── Vinyl art + track info
         ├── Progress bar + seek
         ├── Play/Pause/Skip controls
         └── Volume control
         │
    ┌────┴────┐
    ▼         ▼
Tab: Search  Tab: Queue
(discovery)  (reorder)
    │             │
    └──── Tab: Lyrics ────┐
                           │
                      Tab: Settings
                      (server controls,
                       sponsorblock, etc.)
```

**Gap yang ditemukan:**
- Tidak ada "mini player" yang persisten saat berpindah tab → user kehilangan konteks lagu saat di Search
- Tab Lyrics memerlukan lagu aktif — tidak ada empty state yang mengarahkan
- Tidak ada back-navigation dari Search hasil ke Home

### A.2 Tab IA Audit

| Tab | Icon | Label | Konten | Validasi |
|-----|------|--------|--------|----------|
| Home | ♪ | Home | Now Playing, vinyl, controls | ✅ Tepat sebagai landing |
| Search | 🔍 | Search | Input + hasil YouTube | ✅ Discover discovery flow |
| Queue | ☰ | Queue | Daftar antrean + reorder | ✅ Core feature |
| Lyrics | 📄 | Lyrics | Synchronized lyrics | ⚠️ Jarang dipakai — pertimbangkan merge ke Home |
| Settings | ⚙️ | Settings | Server, audio, visual settings | ✅ Appropriate |

**Rekomendasi:** 5 tab masih reasonable. Jika ingin lebih Spotify-like, Lyrics bisa di-promote ke bagian Now Playing screen (swipe up), bukan tab terpisah.

### A.3 Screen Inventory

| Screen | Ada? | Completeness |
|--------|------|-------------|
| Portal (login) | ✅ | Lengkap |
| Home / Now Playing | ✅ | Missing: mini player di tab lain |
| Search | ✅ | Missing: recent searches, empty state |
| Queue | ✅ | Missing: drag broken di mobile |
| Lyrics | ✅ | Missing: empty state, offset doc |
| Settings | ✅ | Terlalu penuh — candidate untuk scroll |
| Fullscreen Player | ❌ | Tidak ada |
| Desktop Layout | ❌ | Tidak ada (Phase 5) |

---

## CHAPTER B — DESIGN SYSTEM GAP ANALYSIS *(BARU)*

> **Mengapa chapter ini ada:** Phase 3 CSS cleanup tidak bisa dilakukan tanpa tahu sistem yang ingin dicapai. Ini adalah target state untuk design tokens.

### B.1 Spacing Scale

Saat ini spacing tidak sistematis — `14px`, `8px`, `12px` muncul sebagai magic numbers di seluruh CSS. Target:

```css
/* Target spacing scale (4px base grid) */
--space-1:  4px;   /* komponen dalam komponen: icon padding */
--space-2:  8px;   /* komponen: internal padding minimal */
--space-3: 12px;   /* komponen: internal padding normal */
--space-4: 16px;   /* komponen: internal padding besar */
--space-5: 20px;   /* layout: section gap kecil */
--space-6: 24px;   /* layout: section gap normal */
--space-8: 32px;   /* layout: section gap besar */
--space-10: 40px;  /* layout: page margin */
```

### B.2 Typography Scale

Inter sudah di-import tapi tidak dipakai. Target typography system:

```css
/* Font — adopsi Inter yang sudah ada */
--fm-font: 'Inter', -apple-system, system-ui, sans-serif;

/* Size scale */
--text-xs:  10px;  /* secondary labels, timestamps */
--text-sm:  12px;  /* captions, queue item secondary */
--text-md:  14px;  /* body default */
--text-lg:  16px;  /* titles, nav labels aktif */
--text-xl:  20px;  /* now playing title */
--text-2xl: 24px;  /* header display */

/* Weight */
--weight-regular: 400;
--weight-medium:  500;
--weight-semibold: 600;
--weight-bold:    700;

/* Line height */
--leading-tight:  1.2;
--leading-normal: 1.5;
--leading-loose:  1.8;
```

### B.3 Color System Extension — State Tokens

Token warna yang ada sudah mencakup palette, tapi belum mencakup semua interactive state:

```css
/* Interactive state tokens yang belum ada */
--fm-color-hover:    rgba(255, 255, 255, 0.08);
--fm-color-active:   rgba(255, 255, 255, 0.12);
--fm-color-disabled: rgba(255, 255, 255, 0.30);
--fm-color-focus:    var(--fm-accent);

/* Semantic state tokens yang belum ada */
--fm-color-success:  #1DB954;  /* Spotify green — untuk konfirmasi */
--fm-color-warning:  #F59E0B;  /* amber — untuk status ⚠️ */
--fm-color-error:    #EF4444;  /* red — untuk error state */
--fm-color-info:     #3B82F6;  /* blue — untuk informasi */
```

### B.4 Motion Tokens

Tidak ada satu pun motion token di `tokens.css`. Spotify sangat animation-heavy. Target:

```css
/* Duration */
--duration-instant:  0ms;
--duration-fast:    100ms;  /* micro-feedback: button press */
--duration-normal:  200ms;  /* tab switch, element appear */
--duration-slow:    350ms;  /* modal open, screen transition */
--duration-deliberate: 500ms; /* onboarding, major state change */

/* Easing */
--ease-out:  cubic-bezier(0.0, 0.0, 0.2, 1); /* decelerate */
--ease-in:   cubic-bezier(0.4, 0.0, 1, 1);   /* accelerate */
--ease-both: cubic-bezier(0.4, 0.0, 0.2, 1); /* standard */
--ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* spring (Spotify-like) */
```

### B.5 Icon System Decision

Saat ini ada campuran emoji dan text character sebagai icon (♪, ✕, ≡, ⚙). Tidak ada inventarisasi formal.

**Inventarisasi icon yang ada:**
- Play/Pause: emoji atau unicode character
- Navigation tabs: emoji
- Settings controls: text character
- Queue drag handle: ≡ atau ⠿

**Keputusan untuk V2:** Pertahankan emoji/unicode untuk saat ini (zero dependency), tapi standardisasi ukuran via font-size token. Migrasi ke SVG sprite bisa dijadikan Phase 5 task jika diinginkan.

### B.6 Dark Mode Strategy

Aplikasi ini hanya dark mode. Tidak perlu light mode untuk scope saat ini. `prefers-color-scheme` tidak perlu di-implement di Phase 0–4. Catat ini sebagai explicit decision.

---

## CHAPTER C — DESKTOP & TABLET BLUEPRINT *(BARU)*

> **Mengapa chapter ini ada:** Phase 5 tidak bisa diimplementasi tanpa blueprint. AI Agent di Phase 5 akan mulai dari nol tanpa referensi. Blueprint harus ada sekarang meski implementasi belum.

### C.1 Mobile Layout (≤ 600px) — Target State

```
┌─────────────────────────┐
│  [Status bar area]      │
├─────────────────────────┤
│                         │
│     [ Vinyl / Art ]     │
│                         │
│  Track Title            │
│  Artist Name            │
│                         │
│  ─────────●────────     │  ← progress bar
│  00:32          3:45    │
│                         │
│  ⏮  ⏯  ⏭  🔀  🔁     │  ← controls
│                         │
│  🔈 ───────── 🔊       │  ← volume
│                         │
├─────────────────────────┤
│  ♪ Home │ 🔍 │ ☰ │ 📄 │ ⚙  │  ← bottom nav
└─────────────────────────┘
```

### C.2 Tablet Portrait Layout (601px – 1023px)

```
┌──────────────────────────────────┐
│  bagas.fm                        │
├──────────────────────────────────┤
│                                  │
│        [ Vinyl / Art ]           │
│        (lebih besar)             │
│                                  │
│  Track Title (lebih besar)       │
│  Artist Name                     │
│                                  │
│  ────────────────●───────        │
│  controls + volume               │
│                                  │
├──────────────────────────────────┤
│  ♪ Home │ 🔍 │ ☰ │ 📄 │ ⚙      │
└──────────────────────────────────┘
```

**Tablet portrait:** Mirip mobile tapi komponen bisa lebih besar (max-width: 600px centered). Tidak perlu 2-column di portrait.

### C.3 Tablet Landscape Layout (601px – 1023px, landscape)

```
┌────────────────┬─────────────────┐
│                │                 │
│  [ Vinyl ]     │  Queue List     │
│                │  ─────────────  │
│  Track Title   │  ● Now Playing  │
│  Artist        │  ○ Next Track   │
│                │  ○ Track 3      │
│  ─────●────    │  ○ Track 4      │
│  ⏮ ⏯ ⏭ 🔀  │  ○ Track 5      │
│  volume        │                 │
│                │  (scrollable)   │
├────────────────┴─────────────────┤
│  ♪ Home │ 🔍 │ ☰ │ 📄 │ ⚙      │
└──────────────────────────────────┘
```

### C.4 Desktop Layout (≥ 1024px) — Target State

```
┌──────────┬─────────────────────────────┬────────────┐
│          │                             │            │
│ Sidebar  │       Main Content          │   Queue    │
│          │                             │   Panel    │
│ ♪ Home   │    [ Vinyl / Art ]          │ ─────────  │
│ 🔍 Search│    (large)                  │ ● Playing  │
│ ☰ Queue  │                             │ ○ Next     │
│ 📄 Lyrics│    Track Title (large)      │ ○ Track 3  │
│ ⚙ Settings    Artist Name             │ ○ Track 4  │
│          │                             │ ○ Track 5  │
│          │    ─────────────●──────     │ ─────────  │
│          │    00:32              3:45  │            │
│          │                             │            │
│──────────│    ⏮  ⏯  ⏭  🔀  🔁      │            │
│ [Art]    │    🔈 ────────────── 🔊    │            │
│ [Title]  │                             │            │
│ [Artist] │                             │            │
│ ⏮ ⏯ ⏭ │                             │            │
└──────────┴─────────────────────────────┴────────────┘
```

**Spesifikasi desktop:**
- Sidebar kiri: 200–240px, fixed, berisi navigasi
- Main content: flex-1, berisi now playing
- Queue panel kanan: 280px, bisa di-collapse
- Bottom bar (persistent now-playing bar): 72px height, ada di semua halaman

### C.5 Grid Specification per Breakpoint

| Breakpoint | Columns | Gutter | Margin |
|-----------|---------|--------|--------|
| ≤ 600px | 4 | 16px | 16px |
| 601–1023px | 8 | 20px | 24px |
| ≥ 1024px | 12 | 24px | 40px |

---

## CHAPTER D — COMPONENT ARCHITECTURE AUDIT *(BARU)*

> **Mengapa chapter ini ada:** Tanpa inventarisasi komponen, CSS cleanup di Phase 3 akan menciptakan duplikasi baru.

### D.1 Inventarisasi Komponen yang Ada

| Komponen | File CSS | Reusable? | Status |
|----------|----------|-----------|--------|
| `.card` | base.css | ✅ Ya | Solid |
| `.nav-btn` | tabs.css | ✅ Ya | Solid |
| `.queue-item` | base.css | ✅ Ya | Solid |
| `.vol-grp` | base.css, components.css | ❌ Duplikat | Butuh cleanup |
| `.toggle` / `.ss-toggle` | base.css, components.css | ❌ Duplikat | Butuh unifikasi |
| `.toggle-dot` | base.css (3x) | ❌ Triplication | Butuh cleanup |
| `.fav-card` | base.css | ⚠️ Partial | Hardcoded min-width |
| `.search-result-item` / `.sr-item` | base.css | ❌ Dua nama berbeda | Butuh unifikasi |
| `.sheet` (bottom sheet) | base.css | ✅ Reusable | Solid |
| `.portal-*` | portal.css | ✅ Terpisah | Solid |

### D.2 Naming Convention

Adopsi BEM-lite untuk konsistensi:
- Komponen: `.komponen-nama` (kebab-case)
- Modifier: `.komponen-nama--modifier` (double dash)
- Child: `.komponen-nama__child` (double underscore)

Contoh yang sudah ada dan perlu distandarisasi:
- `.queue-item` → `.queue-item--current`, `.queue-item--dragging` (sudah benar)
- `.nav-btn` → `.nav-btn--active` (belum ada — saat ini pakai `.active`)

### D.3 Komponen yang Perlu Dibuat

| Komponen | Kebutuhan | Phase |
|----------|-----------|-------|
| Mini Player Bar | Persistent player saat pindah tab | Phase 5 |
| Empty State | Reusable empty state pattern | Phase 4 |
| Toast Notification | Feedback sukses/error | Phase 5 |
| Skeleton Loader | Loading state untuk card | Phase 5 |
| Bottom Sheet | Sudah ada, perlu dokumen spec | Phase 3 |

---

## CHAPTER E — STATE MANAGEMENT ARCHITECTURE *(BARU)*

> **Mengapa chapter ini ada:** Global store tidak scalable; perlu rencana sebelum Phase 5 PWA.

### E.1 Inventory State Saat Ini

| State | Tipe | Sumber | Persist? |
|-------|------|--------|----------|
| `status` | `PLAYING / PAUSED / STOPPED / LOADING` | WebSocket | ❌ |
| `current_track` | Object | WebSocket | ❌ |
| `queue` | Array | WebSocket | ❌ |
| `volume` | Number (0–100) | WebSocket | ❌ |
| `lyrics` | Array | WebSocket | ❌ |
| `userRole` | `admin / client / portal` | Local | ❌ |
| `discover_cached` | Array | WebSocket | ❌ |
| `radio` | Object | WebSocket | ❌ |
| Admin token | String | WebSocket | ✅ localStorage |

### E.2 State untuk Offline / PWA (Phase 6)

Jika PWA diimplementasi, state berikut perlu persist di localStorage / IndexedDB:
- Last played track (untuk resume setelah offline)
- Queue snapshot
- Settings (volume, sponsorblock toggle)

### E.3 Keputusan Arsitektur

**Keputusan:** Pertahankan plain object store untuk Phase 0–4. Ini tidak perlu direfactor dulu.

**Untuk Phase 6 (PWA):** Evaluasi migrasi ke reactive pattern sederhana (custom EventEmitter atau Alpine.js) tanpa bundler. Vanilla JS cukup untuk scope ini.

---

## CHAPTER F — PERFORMANCE BASELINE & BUDGET *(BARU)*

> **Mengapa chapter ini ada:** Tidak ada baseline = tidak ada cara tahu apakah optimasi di Phase 4 berhasil.

### F.1 Baseline Metrics (Ukur Sebelum Transformasi)

Jalankan ini sebelum mulai Phase 0:

```bash
# CSS size
wc -c web/static/css/*.css
# JS size
wc -c web/static/js/*.js web/static/js/render/*.js
# Total request count (manual — buka Network tab di DevTools)
```

### F.2 Performance Budget Target

| Metric | Baseline (estimasi) | Target setelah Phase 4 |
|--------|-------------------|----------------------|
| CSS total | ~80KB | < 50KB (setelah dedup + cleanup) |
| JS total | ~100KB | < 90KB |
| Inter font | ~50KB | 0KB (hapus di P0-2) |
| Time to Interactive | ~2s (lokal) | < 1.5s |
| Progress update rate | Tidak throttled | 60fps (rAF) |

### F.3 Rendering Performance

`renderFullState()` memanggil 8 fungsi render sekaligus. Baseline: ukur waktu eksekusi sebelum Phase 4:

```javascript
// Tambahkan sementara di ws.js untuk profiling
console.time('renderFullState');
renderFullState();
console.timeEnd('renderFullState');
```

---

## CHAPTER G — ACCESSIBILITY STRATEGY *(BARU)*

> **Mengapa chapter ini ada:** Fixing aria-label satu per satu tidak cukup untuk accessibility yang sistematis.

### G.1 Target WCAG Level

**Target:** WCAG 2.1 Level AA

Untuk aplikasi musik personal, ini adalah target yang realistis dan meaningful.

### G.2 Keyboard Navigation Flow

Tab order yang harus bekerja secara logis:

```
Portal Screen:
[Client Btn] → [Admin Btn] → [Username Input] → [Password Input] → [Login Btn]

Main App:
[Nav: Home] → [Nav: Search] → [Nav: Queue] → [Nav: Lyrics] → [Nav: Settings]
  │
  └─ Home Tab:
     [Volume Slider] → [Prev] → [Play/Pause] → [Next] → [Shuffle] → [Repeat]
     [Progress Bar (dapat di-seek dengan arrow keys)]
```

### G.3 ARIA Patterns untuk Music Player

| Elemen | ARIA Pattern | Implementasi |
|--------|-------------|-------------|
| Progress bar | `role="slider"` + `aria-valuemin/max/now` | Belum ada |
| Volume | `role="slider"` + `aria-label="Volume"` | Belum ada |
| Play/Pause | `aria-label="Play"` / `aria-label="Pause"` (dynamic) | Belum ada |
| Tab navigation | `role="tablist"` + `role="tab"` | Belum ada |
| Queue list | `role="list"` + `role="listitem"` | Belum ada |
| Now playing | `aria-live="polite"` untuk track change announcement | Belum ada |

### G.4 Contrast Audit

| Token | Hex | Background | Ratio | WCAG AA? |
|-------|-----|------------|-------|----------|
| `--fm-text-5` | `#5a5a7a` | `--fm-bg-card` `#141426` | ~2.8:1 | ❌ FAIL |
| `--fm-text-3` | `#a0a0c0` | `--fm-bg-card` `#141426` | ~4.6:1 | ✅ PASS |
| `--fm-accent` | (tergantung nilai) | `--fm-bg-deep` | Perlu ukur | Ukur manual |

**Fix yang dibutuhkan:** `--fm-text-5` perlu di-lighten ke minimal `#7a7a9a` untuk mencapai 4.5:1.

### G.5 Screen Reader Test Checklist

- [ ] Buka dengan VoiceOver (macOS) atau TalkBack (Android)
- [ ] Navigasi ke Play button — apakah dibaca "Play" atau hanya "button"?
- [ ] Ganti lagu — apakah track title diumumkan?
- [ ] Navigasi queue — apakah urutan item terbaca?

---

## CHAPTER H — BROWSER & DEVICE SUPPORT MATRIX *(BARU)*

> **Mengapa chapter ini ada:** Tanpa ini, cross-browser bug ditemukan saat implementasi.

### H.1 Target Browser

Karena bagas.fm adalah personal app di Termux (diakses via browser lokal), target browser minimal:

| Browser | Version | Priority |
|---------|---------|----------|
| Chrome Android | Latest | P0 (primary) |
| Safari iOS | Latest | P1 |
| Chrome Desktop | Latest | P2 |
| Firefox Desktop | Latest | P3 |

### H.2 Feature Detection Strategy

| Feature | Fallback |
|---------|---------|
| `100dvh` | `100vh` (sudah ada di playbook) |
| `env(safe-area-inset-*)` | `@supports` guard (sudah direncanakan) |
| Pointer Events API | Touch Events (fallback di drag-drop baru) |
| `requestAnimationFrame` | `setTimeout` 16ms (hampir semua browser support rAF) |
| CSS Grid | Flexbox fallback |

### H.3 Polyfill Plan

Tidak ada polyfill yang dibutuhkan untuk target browser di atas. Semua feature yang digunakan (CSS Grid, Flexbox, Pointer Events, rAF, `dvh`) sudah didukung oleh Chrome Android latest.

---

## FASE 1 — UI/UX AUDIT

*(Konten dari V1 dipertahankan)*

### 1.1 Responsive Design Audit

#### 🔴 CRITICAL: Fake Phone Frame Shell

**File:** `web/static/css/base.css`, **Line 27**

```css
#app {
  width: 100%;
  max-width: 375px;   /* ← hardcoded iPhone 8 width */
  height: 690px;      /* ← hardcoded fixed height */
  border-radius: 36px; /* ← phone-rounded corners */
  border: 3px solid #1e1e32; /* ← phone outline */
}
```

Ini adalah root cause dari "mockup HP yang ditempel di browser". Seluruh aplikasi terkunci dalam kotak 375×690px. Di tablet 768px, ada area hitam kosong di kiri-kanan. Di desktop 1440px, ada hampir 500px dead space di setiap sisi.

**Media query saat ini (base.css:14-23) hanya "menghilangkan kotak" di ≤480px:**

```css
@media (max-width: 480px) {
  #app { border-radius: 0 !important; max-width: 100% !important; height: 100dvh !important; }
}
```

Tidak ada breakpoint untuk tablet (768px+) atau desktop (1024px+).

#### 🔴 Hardcoded Fixed Dimensions (Tidak Memakai Token)

| File | Line | Rule | Masalah |
|------|------|------|---------|
| base.css | 27 | `height: 690px` | Fixed height app shell |
| base.css | 39 | `max-width: 200px` | `.pb-title` terpotong di layar lebar |
| base.css | 50 | `width: 65px` | Volume slider terlalu kecil |
| base.css | 82 | `width: 108px; height: 72px` | `.disc-thumb` hardcoded |
| base.css | 160 | `min-width: 130px` | `.fav-card` hardcoded |
| base.css | 207 | `max-width: 340px` | Help modal terlalu kecil di desktop |

#### 🔴 Tidak Ada Breakpoint Tablet / Desktop

Tidak ada satu pun media query untuk layar lebar (≥601px, ≥1024px). Desktop layout (Chapter C) harus diimplementasi di Phase 5.

#### 🟡 Orientation Issue

Tidak ada `@media (orientation: landscape)` handling. Di iPhone landscape (667×375), app container 375px lebar masih benar tapi tinggi 690px melebihi viewport 375px, menyebabkan layout overflow.

---

### 1.2 Spotify Benchmark Audit

| Kategori | Skor | Gap Utama |
|----------|------|-----------|
| Visual Hierarchy | 40/100 | Header terlalu kecil (16px title), tidak ada zona "hero" yang jelas |
| Spacing | 45/100 | Padding 14px konsisten tapi tidak ada spacing scale yang sistematis |
| Typography | 35/100 | Inter di-import tapi tidak digunakan; font-size minimum 10px (terlalu kecil di mobile) |
| Accessibility | 30/100 | Banyak tombol tanpa aria-label, fokus tidak terlihat |
| Navigation | 60/100 | 5 tab bottom nav — acceptable, tapi tidak ada active state animation |
| Player UX | 55/100 | Progress bar sudah bisa di-drag, tapi thumb 11×11px (terlalu kecil) |
| Search UX | 65/100 | Debounce 500ms bagus, spinner ada |
| Queue UX | 30/100 | Drag-drop **tidak bekerja di mobile touch** |
| Lyrics UX | 50/100 | Synchronized lyrics ada, tapi offset control tersembunyi di sheet |
| Onboarding | 20/100 | Tidak ada empty state yang mengarahkan user, tidak ada onboarding flow |

---

### 1.3 Design System Audit

#### 🔴 CSS Variable `--fm-primary` TIDAK TERDEFINISI

**File:** `base.css`, **Lines 137, 140**

`--fm-primary` tidak ada di `tokens.css`, tidak ada di seluruh codebase. **Fix:** `--fm-primary: var(--fm-accent)` di tokens.css.

#### 🟡 Duplikasi Definisi CSS (Triplication)

`.vol-grp` didefinisikan 3 kali (base.css:48, base.css:559, components.css:2). `.toggle-dot` didefinisikan 3 kali. Solusi ada di Chapter D dan Phase 3 Playbook.

#### 🟡 Inter Font: Loaded But Never Applied

~50KB download yang tidak dipakai. Fix di P0-2.

#### 🟡 Legacy Token Aliases Belum Dihapus

`tokens.css:46-73` masih punya 20+ legacy aliases. Perlu dimigrasikan ke `--fm-*` token sebelum legacy block dihapus.

---

### 1.4 Mobile UX Audit

#### 🔴 Drag-and-Drop Queue Tidak Bekerja di Mobile

HTML5 Drag API tidak didukung oleh touch event. Solusi ada di Phase 2 Playbook (Pointer Events API).

#### 🔴 Touch Target Terlalu Kecil

| Elemen | Ukuran Aktual | Minimum HIG/Material |
|--------|--------------|---------------------|
| `.pb-thumb` (seek thumb) | 11×11px | 44×44px |
| `.vol-grp input[type=range]` height | 3px | 44px touch area |
| `.lyric-offset button` | 22×22px | 44×44px |
| `.qi-drag` (drag handle) | ~20px | 44×44px |

#### 🟡 Safe Area Insets Tidak Ditangani

`env(safe-area-inset-*)` belum ada. Fix di Phase 1 Playbook.

---

### 1.5 Accessibility Audit (WCAG 2.2)

Detail ada di Chapter G. Summary:
- ❌ >10 button tanpa aria-label
- ❌ `outline: none` tanpa :focus-visible replacement
- ❌ Input tanpa `<label>` element
- ❌ Contrast ratio `--fm-text-5` di bawah AA minimum

---

## FASE 2 — FRONTEND ARCHITECTURE AUDIT

*(Konten dari V1 dipertahankan)*

### 2.1 State Management

*(Lihat Chapter E untuk analisis lengkap)*

State management menggunakan plain object global `store`. Tidak ada reactivity — render harus di-trigger manual. `renderFullState()` dipanggil pada setiap `state` WS message, me-render 8+ komponen sekaligus.

### 2.2 DOM Coupling

- `dom.lyricsToggleBtn` — element tidak ada di index.html (dead reference)
- `dom.btnStop` — element tidak ada di index.html (dead reference)

### 2.3 Dependency Map

```
main.js
  ├── initDOM()         → dom.js
  ├── initPortal()      → portal.js → store, dom
  ├── initAudio()       → audio.js → store, dom, ws
  ├── initEvents()      → events.js → store, dom, ws, render/*
  └── wsConnect()       → ws.js → store, dom, render/*
                              └── handleServerMessage()
                                    ├── renderFullState() → ALL render files
                                    └── syncBrowserAudio() → audio.js
```

---

## FASE 3 — HIDDEN BUG HUNTING

### BUG-001: `--fm-primary` Undefined
**Severity: High | Probability: Very High (selalu terjadi)**

`base.css:137,140` — queue drag-over dan current track indicator tidak punya warna.

**Fix:** `--fm-primary: var(--fm-accent)` di tokens.css.

### BUG-002: Queue Drag-Drop Broken di Mobile
**Severity: Critical | Probability: Very High**

HTML5 Drag Events API. Touch device tidak support event ini.

**Fix:** Reimplement dengan Pointer Events API (Phase 2 Playbook).

### BUG-003: WS Reconnect — Multiple Connection Risk
**Severity: Medium | Probability: Medium**

`ws.js:10` — saat `wsConnect()` dipanggil ulang, koneksi lama tidak di-close dulu.

**Fix:** Tambahkan `ws.close()` guard sebelum `new WebSocket(url)` (Phase 2 Playbook).

### BUG-004: `lastToggleTime` State Desync
**Severity: Medium | Probability: High**

Window 1 detik setelah toggle play/pause mengabaikan server status. Jika server berhenti dalam 1 detik, UI tetap menunjukkan PLAYING.

### BUG-005: `portal.js` DOM Manipulation yang Fragile
**Severity: Medium | Probability: High**

`applyRoleUI()` memindahkan DOM element fisik — jika dipanggil berkali-kali, DOM bisa korup.

### BUG-006: Audio Event Listeners Leak
**Severity: Low | Probability: Medium**

`timeupdate` event listener di `audio.js:24` tidak pernah di-remove.

### BUG-007: `syncBrowserAudio` Dipanggil di Semua Role
**Severity: Low | Probability: Very High**

Dijalankan bahkan saat user masih di portal screen.

**Fix:** Guard dengan `if (store.userRole !== 'portal')` (Phase 4 Playbook).

### BUG-008: Search Result Click Dual Delegation
**Severity: Low | Probability: Medium**

Dua event listener berbeda untuk click di search results (`.sr-item` vs `.search-result-item`).

---

## FASE 4 — SECURITY AUDIT

### SEC-001: Session Token di localStorage
**Severity: Low (acceptable untuk use case)**

Di lingkungan personal/lokal ini acceptable. Catat sebagai known risk.

### SEC-002: Password Cleanup Reference
**Severity: Medium | Status: Sudah di-handle, artifact tersisa**

`ws.js:68` dan `portal.js:39` masih punya `localStorage.removeItem("ytgui_admin_password")`. Bersihkan untuk clarity.

### SEC-003: XSS — `innerHTML` dengan Data Server
**Severity: Medium | Probability: Low (mitigated)**

Mayoritas sudah pakai `escapeHtml()`. Thumbnail URL tidak divalidasi scheme-nya tapi risikonya rendah di konteks lokal.

### SEC-004: WebSocket Tidak Ada Origin Check
**Severity: Low**

Auth dilakukan via pesan `auth` pertama. Acceptable untuk personal use.

---

## FASE 5 — PERFORMANCE AUDIT

### PERF-001: `renderFullState()` — Over-Rendering
**Severity: High** — 8 render functions dipanggil sekaligus bahkan untuk perubahan kecil.

### PERF-002: Progress Update tanpa `requestAnimationFrame`
**Severity: Medium** — DOM manipulation langsung tanpa rAF.

### PERF-003: Inter Font — Unused 50KB Download
**Severity: Low** — Fix di P0-2.

### PERF-004: `updateSearchPlayingState()` — DOM Loop
**Severity: Medium** — Loop seluruh `.sr-item` setiap status change.

### PERF-005: CSS Architecture — 30KB Monolith
**Severity: Medium** — `base.css` 30KB dengan triplication.

---

## FASE 6 — SCALABILITY AUDIT

**Backend: YA** — Event bus, command routing, room manager sudah solid.

**Frontend: TIDAK, perlu transformasi fundamental.**

1. Phone shell harus dihapus total
2. CSS architecture perlu refactor (triplication, dead code, undefined tokens)
3. No responsive breakpoints — tablet dan desktop perlu dirancang dari nol (lihat Chapter C)
4. Touch event handling — perlu reimplementasi dengan Pointer Events API
5. State management — acceptable untuk Phase 0–4, perlu review untuk Phase 6 PWA

---

## FASE 7 — TRANSFORMATION ROADMAP

*(Detail eksekusi ada di AI_AGENT_PLAYBOOK_SPOTIFY_V2.md)*

### Phase -1 — Design Blueprint Sign-off *(BARU)*
**Effort: XS | Output: Dokumen, bukan kode**
- [ ] Review dan setujui breakpoints di Chapter C
- [ ] Review dan setujui design tokens di Chapter B
- [ ] Review dan setujui component inventory di Chapter D
- [ ] Exit criteria: blueprint disetujui sebelum lanjut ke Phase 0

### Phase 0 — Critical Fixes (< 1 jam)
- Fix BUG-001 (`--fm-primary`)
- Hapus Inter font import
- Tambah aria-label ke tombol kritis
- Tambah :focus-visible replacement
- Hapus dead DOM reference

### Phase 1 — Mobile-First Shell (3–5 hari)
- Hapus phone shell
- Implementasi layout responsif
- Tablet + desktop breakpoints awal
- Safe area + landscape handling

### Phase 2 — Touch & Interaction (3–4 hari)
- Queue drag-drop via Pointer Events
- Touch target sizes ≥44px
- Keyboard behavior mobile
- WS reconnect fix

### Phase 3 — CSS Architecture Cleanup (2–3 hari)
- Deduplicate vol-grp, toggle-dot
- Legacy token migration
- Dead CSS removal
- Toggle system unification

### Phase 4 — Performance & UX Polish (3–5 hari)
- Dirty-flag rendering
- rAF progress update
- Empty states
- syncBrowserAudio guard

### Phase 5 — Desktop & Tablet Layout (1–2 minggu)
*(Lihat Chapter C untuk blueprint)*
- Desktop 2-column layout
- Persistent now-playing bar di desktop
- Sidebar navigation
- Keyboard shortcuts
- Tablet landscape queue panel

### Phase 6 — PWA & Offline (1–2 minggu)
- manifest.json
- Service worker + cache strategy
- Install prompt
- Offline fallback UI

---

## Priority Matrix

| Priority | Masalah | Severity | Effort | Impact |
|----------|---------|----------|--------|--------|
| P0 | `--fm-primary` undefined | High | XS | Queue drag visual broken |
| P0 | Tambah aria-labels | High | XS | Accessibility |
| P1 | Hapus phone shell | Critical | L | Real responsive app |
| P1 | Queue touch drag-drop | Critical | M | Core feature di mobile |
| P1 | Touch target sizes | High | M | Mobile usability |
| P2 | CSS deduplication | Medium | M | Maintainability |
| P2 | Inter font removal | Low | XS | 50KB load time |
| P2 | rAF progress update | Medium | S | Performance |
| P3 | Tablet/desktop layout | High | XL | Spotify-class parity |

---

## Spotify-Class Gap Analysis

### Mobile (≤ 600px)
| Area | Status | Plan |
|------|--------|------|
| Full-viewport layout | ❌ Phone shell | Phase 1 |
| Touch gestures | ❌ Drag broken | Phase 2 |
| Now Playing screen | ⚠️ Ada tapi kecil | Phase 5: fullscreen player |
| Bottom navigation | ✅ 5 tabs | — |
| Search | ⚠️ Debounce ada | Phase 5: recent searches |
| Mini player persistence | ❌ Tidak ada | Phase 5 |

### Tablet (601px – 1023px)
| Area | Status | Plan |
|------|--------|------|
| Responsive layout | ❌ Tidak ada | Phase 1 (max-width only) |
| Landscape 2-panel | ❌ Tidak ada | Phase 5 (lihat Chapter C.3) |
| Safe area | ❌ Tidak ada | Phase 1 |

### Desktop (≥ 1024px)
| Area | Status | Plan |
|------|--------|------|
| Sidebar navigation | ❌ Tidak ada | Phase 5 |
| Persistent now-playing bar | ❌ Tidak ada | Phase 5 |
| Queue panel | ❌ Tidak ada | Phase 5 |
| Keyboard shortcuts | ❌ Tidak ada | Phase 5 |

---

## Final Verdict

**Production Ready? → NO**

bagas.fm adalah proyek yang sangat solid secara backend. Untuk mencapai Spotify-class experience yang stated goal, semua pekerjaan yang tersisa adalah frontend dan terukur melalui roadmap Phase -1 s/d Phase 6.

Dengan blueprint di Chapter A–H dan eksekusi di Playbook V2, target "Spotify-class" untuk konteks bagas.fm dapat dicapai secara inkremental tanpa rework antar phase.

---

*End of Report V2 — bagas.fm Spotify-Class Audit*
*V2 menambahkan Chapter A (Product IA), B (Design System), C (Desktop Blueprint), D (Component Architecture), E (State Management), F (Performance Baseline), G (Accessibility), H (Browser Support)*
*Total CSS analyzed: ~50KB across 7 files*
*Total JS analyzed: ~100KB across 13 files*
*Total Python analyzed: ~80KB across 20+ files*
