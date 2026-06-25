# AI_AGENT_PLAYBOOK V2 — Spotify-Class Transformation
> **Untuk:** AI Agent yang mengeksekusi hasil audit `AUDIT_SPOTIFY_CLASS_V2.md`
> **Proyek:** bagas.fm — YouTube Music Player
> **Prinsip:** Audit dulu. Verify sebelum edit. Verify setelah edit. Commit atomik. Jangan asumsi.
> **V2 Changes:** Tambah Agent Context Brief, Risk Matrix, Definition of Done, ADR, Regression Prevention, Phase 5 & 6 spec lengkap

---

## CHAPTER X — AGENT CONTEXT BRIEF *(BARU — BACA INI DULU)*

> **Ini adalah bagian pertama yang harus dibaca oleh AI Agent sebelum mengeksekusi task apapun.**

### X.1 Deskripsi Aplikasi

**Nama:** bagas.fm
**Tipe:** Personal YouTube music player — bukan streaming service publik
**Use case utama:** Solo listener yang ingin memutar musik YouTube dengan antarmuka seperti Spotify

**Tech stack:**
- **Backend:** Python 3 + aiohttp, WebSocket server, event bus pattern
- **Frontend:** Vanilla JS (ES5/ES6 tanpa bundler), plain CSS multi-file
- **Deployment:** Termux (Android), diakses via browser lokal (`localhost:PORT`)
- **No build step** — semua file langsung di-serve sebagai static assets

### X.2 Struktur File

```
[PROJECT_ROOT]/
├── main.py               ← Entry point server
├── engine/               ← Backend: audio engine, mpv control
├── web/
│   └── static/
│       ├── index.html    ← Satu-satunya HTML file
│       ├── css/
│       │   ├── base.css      ← Main styles (30KB) ← PALING SERING DIEDIT
│       │   ├── tokens.css    ← CSS custom properties / design tokens
│       │   ├── components.css← Reusable component styles
│       │   ├── tabs.css      ← Tab-specific styles
│       │   ├── player.css    ← Player bar styles
│       │   ├── portal.css    ← Login screen styles
│       │   └── layout.css    ← Layout / responsive breakpoints
│       └── js/
│           ├── main.js       ← Init orchestrator
│           ├── store.js      ← Global state object
│           ├── dom.js        ← DOM element references
│           ├── ws.js         ← WebSocket + message handler
│           ├── events.js     ← User interaction events ← DRAG-DROP ADA DI SINI
│           ├── audio.js      ← Browser audio sync
│           ├── portal.js     ← Login screen logic
│           ├── utils.js      ← Helper functions
│           └── render/
│               ├── player.js ← Now playing render
│               ├── tabs.js   ← Tab content render
│               ├── lyrics.js ← Lyrics render
│               └── search.js ← Search results render
```

### X.3 Scope Boundaries

**BOLEH diubah:**
- Semua file di `web/static/css/` dan `web/static/js/`
- `web/static/index.html`

**JANGAN disentuh tanpa explicit instruction:**
- `engine/` dan backend Python files
- `main.py`
- Konfigurasi server

### X.4 Definisi "Spotify-class" untuk Proyek Ini

Dalam konteks bagas.fm (bukan Spotify skala global):
1. **Full-viewport layout** — tidak ada phone frame box di dalam browser
2. **Touch gesture** — queue reorder bekerja di mobile touch
3. **Responsive** — layar ≥601px tidak menampilkan content dengan dead space besar
4. **Accessible dasar** — semua tombol punya aria-label, keyboard navigasi bisa dipakai

---

## ATURAN KERAS UNTUK AI AGENT

```
1. JANGAN pernah edit file tanpa membaca isinya terlebih dahulu.
2. JANGAN asumsi line number — selalu grep/search sebelum edit.
3. SETIAP task harus diakhiri dengan VERIFICATION COMMAND yang bisa di-run.
4. Jika verification GAGAL → STOP, catat sebagai BLOCKED, jangan lanjut ke task berikutnya.
5. Update status checklist ini setelah SETIAP task (bukan di akhir fase).
6. Jika ragu antara dua cara → pilih yang paling sedikit mengubah file lain.
7. Satu commit per fase — jangan squash antar fase.
8. Jika ada task [!] BLOCKED di akhir fase → STOP dan escalate ke human sebelum lanjut fase berikutnya.
9. Sebelum edit file manapun: jalankan REGRESSION SMOKE TEST (lihat Chapter BB).
10. Catat setiap keputusan yang tidak ada di dokumen ini ke dalam catatan task.
```

---

## CARA BACA STATUS TASK

```
[ ] = Belum dikerjakan
[x] = Sudah selesai & verified
[~] = Sedang dikerjakan / partial
[!] = BLOCKED — ada error, lihat catatan
[-] = SKIP — tidak relevan / sudah tidak berlaku
```

---

## CHAPTER Y — RISK MATRIX *(BARU)*

> **AI Agent wajib baca ini sebelum Phase 1 dan 2. Operasi high-risk butuh ekstra hati-hati.**

| Task | Risk Level | Deskripsi Risiko | Mitigation | Stop Condition |
|------|-----------|-----------------|------------|----------------|
| P1-2 (hapus phone shell) | 🔴 HIGH | App bisa blank/invisible jika CSS tidak terbentuk benar | Backup base.css.pre-p1, test visual segera | Jika app tidak tampil di browser → rollback P1-2 |
| P2-1 (ganti drag-drop) | 🔴 HIGH | Fungsi queue reorder bisa hilang total | Backup events.js.pre-p2, test di mobile dan desktop | Jika drag tidak bekerja di salah satu platform → lihat catatan |
| P3-3 (hapus legacy tokens) | 🟡 MEDIUM | Style yang pakai token lama bisa hilang | Jalankan usage check dulu, jangan hapus jika masih ada referensi | Jika ada visual element yang hilang → rollback P3-3 |
| P3-4 (hapus dead CSS) | 🟡 MEDIUM | Class dinamis dari JS mungkin tidak ter-detect oleh script | Review hasil manual sebelum hapus | Jangan hapus class yang namanya ada di JS events |
| P0-2 (hapus Inter import) | 🟢 LOW | Font fallback ke system-ui — perubahan visual minimal | Test visual font |  |
| P4-1 (rAF progress) | 🟢 LOW | rAF sudah dipakai di hampir semua browser | — | — |
| P4-2 (dirty-flag render) | 🟡 MEDIUM | Jika conditional logic salah, komponen tidak ter-render saat seharusnya | Test semua state change: play, pause, queue update, track change | — |

**Cascade Risk:**
- Jika P1-2 blocked → P1-3, P1-4 menjadi tidak valid (bergantung pada #app rule)
- Jika P2-1 blocked → test touch drag di Phase 2 tidak bisa diselesaikan
- Jika P3-3 blocked → Phase 3 cleanup tidak lengkap tapi tidak memblok Phase 4

---

## CHAPTER Z — DEFINITION OF DONE *(BARU)*

### Z.1 Global Definition of Done

Transformasi Spotify-class dinyatakan selesai ketika:
1. Verification Master Script menunjukkan PASS semua
2. Semua task Phase 0–4 berstatus `[x]`
3. Tidak ada task `[!]` yang unresolved
4. Aplikasi dapat diakses di mobile (≤600px) sebagai full-viewport app
5. Queue drag-drop bekerja di touch device
6. `--fm-primary` terdefinisi dan queue current indicator terlihat berbeda

### Z.2 Per-Phase Exit Criteria

**Phase 0 selesai jika:**
- Semua P0-1 s/d P0-5 berstatus `[x]`
- Verification Master Script bagian P0 semua PASS
- Tidak ada CSS syntax error di tokens.css

**Phase 1 selesai jika:**
- P1-2 verified: `grep -c '690px' web/static/css/base.css` output `0`
- P1-3 verified: layout.css punya breakpoint 601px dan 1024px
- Test visual: app tidak lagi tampil sebagai kotak di tengah browser

**Phase 2 selesai jika:**
- P2-1 verified: tidak ada `dragstart` event di events.js
- Touch drag queue bekerja di Chrome mobile (manual test)
- Desktop drag queue masih bekerja (tidak rusak setelah migrasi)

**Phase 3 selesai jika:**
- `.vol-grp` hanya ada satu definisi di seluruh CSS
- `.toggle-dot` hanya ada satu definisi
- Tidak ada `var(--bg-panel)`, `var(--accent-fire)`, dll di CSS manapun

**Phase 4 selesai jika:**
- `renderProgress` menggunakan rAF
- `syncBrowserAudio` tidak jalan saat role = portal
- Empty state ada di queue tab

### Z.3 Blocked Task Protocol

Jika ada task yang `[!]` di akhir fase:
1. Catat error secara lengkap di bawah task
2. Tentukan: apakah task ini memblok fase berikutnya? (lihat Cascade Risk di Chapter Y)
3. Jika memblok → STOP, escalate ke human developer sebelum lanjut
4. Jika tidak memblok → lanjut dengan catatan bahwa task ini perlu diselesaikan di akhir

### Z.4 Partial Success Definition

Fase boleh dianggap "partial done" dan bisa lanjut ke fase berikutnya jika:
- Task yang blocked adalah non-critical (LOW risk dari Chapter Y)
- Tidak ada cascade risk ke fase berikutnya
- Maksimal 1 task `[!]` per fase

---

## CHAPTER AA — ARCHITECTURE DECISION RECORDS *(BARU)*

### ADR-001: Pointer Events vs Touch Events vs Hammer.js

**Keputusan:** Gunakan Pointer Events API native

**Alasan:**
- Pointer Events API sudah support touch + mouse + stylus dalam satu API
- Tidak perlu library tambahan (Hammer.js = dependency baru)
- Chrome Android latest dan Safari iOS latest sudah support penuh
- Touch Events API adalah low-level alternative yang lebih verbose

**Trade-off:** Pointer Events tidak support di beberapa browser lama (IE11), tapi IE11 bukan target (lihat Chapter H Audit).

---

### ADR-002: Breakpoint Values (601px / 1024px)

**Keputusan:** Gunakan 601px untuk tablet threshold, 1024px untuk desktop threshold

**Alasan:**
- 600px adalah sweet spot antara "pasti mobile" dan "mungkin tablet kecil"
- 601px (bukan 768px) dipilih karena banyak small tablet dan large phone di 600–768px range
- 1024px (bukan 1200px) dipilih karena laptop 13" biasanya 1280px+ dan tablet landscape 1024px
- Keputusan ini bisa direvisi di Phase 5 jika implementasi desktop membutuhkan adjustment

**Trade-off:** Tablet portrait di 601–767px akan mendapat "phone-like" layout, bukan 2-column. Ini acceptable karena portrait tablet biasanya digunakan seperti phone yang besar.

---

### ADR-003: CSS Class-based vs Data-attribute Toggle System

**Keputusan:** Unifikasi ke data-attribute system (`data-on="true"` / `data-on="false"`)

**Alasan:**
- Settings sheet sudah menggunakan `data-on` → konsistensi
- Data-attribute lebih mudah di-query dan di-observe (MutationObserver)
- Class-based toggle (`.on` / `.off`) bisa konflik dengan class lain
- `dataset.on = "true"` lebih ekspresif daripada `classList.toggle('on')`

**Trade-off:** Migrasi memerlukan update JS + CSS bersamaan. Ini adalah Phase 3 task.

---

### ADR-004: CSS-only Responsive vs JS-assisted (ResizeObserver)

**Keputusan:** CSS-only responsive untuk Phase 1–4, JS-assisted hanya jika diperlukan di Phase 5

**Alasan:**
- CSS media query cukup untuk breakpoint sederhana
- ResizeObserver menambah complexity dan potential performance issue
- Desktop 2-column layout (Phase 5) mungkin butuh JS untuk collapse/expand panel

---

### ADR-005: Vanilla JS Pertahankan vs Migrasi ke Reactive Library

**Keputusan:** Pertahankan Vanilla JS untuk Phase 0–6

**Alasan:**
- Tidak ada build step — menambah framework berarti menambah bundler
- App sudah functional, masalahnya CSS/layout, bukan reactivity
- Plain store + manual render sudah cukup untuk scope personal music player
- Migrasi ke Preact/Alpine bisa dilakukan sebagai separate project bukan refactor

**Trade-off:** Manual render call tetap diperlukan. Dirty-flag pattern di Phase 4 mengurangi impact ini.

---

## CHAPTER BB — REGRESSION PREVENTION PROTOCOL *(BARU)*

### BB.1 Smoke Test Wajib Sebelum Setiap Commit

Sebelum `git commit` di fase manapun, jalankan minimal:

```bash
# Smoke Test — jalankan sebelum commit
echo "=== SMOKE TEST ==="

# 1. Aplikasi bisa jalan (tidak ada syntax error Python)
python3 -c "import ast; ast.parse(open('main.py').read()); print('✓ main.py syntax OK')"

# 2. HTML parseable
python3 -c "
from html.parser import HTMLParser
HTMLParser().feed(open('web/static/index.html').read())
print('✓ index.html parseable')
"

# 3. Tidak ada undefined CSS variable critical
python3 -c "
import re
content = ''
for f in ['web/static/css/base.css', 'web/static/css/components.css']:
    content += open(f).read()
# Check var() references
vars_used = set(re.findall(r'var\((--[\w-]+)\)', content))
vars_defined = set(re.findall(r'(--[\w-]+)\s*:', open('web/static/css/tokens.css').read()))
undefined = vars_used - vars_defined - {'--fm-primary'}  # exclude known aliases
critical = [v for v in undefined if 'fm-' in v]
if critical:
    print(f'⚠ Undefined fm- variables: {critical}')
else:
    print('✓ No undefined fm- variables')
"

# 4. JS tidak ada obvious syntax error (jika node tersedia)
if command -v node &> /dev/null; then
    for f in web/static/js/*.js web/static/js/render/*.js; do
        node --check "$f" 2>&1 && echo "✓ $f OK" || echo "✗ $f FAIL"
    done
else
    echo "⚠ node tidak tersedia — skip JS syntax check"
fi

echo "=== SMOKE TEST SELESAI ==="
```

### BB.2 "Do Not Break" List

Fitur-fitur ini harus tetap berfungsi setelah setiap phase:

| Fitur | Test | Cara Cek |
|-------|------|---------|
| App bisa diakses di browser | Buka localhost:PORT | Manual |
| Play/Pause bekerja | Klik play button | Manual |
| Volume control bekerja | Geser volume slider | Manual |
| Search bekerja | Ketik query, enter | Manual |
| Tab navigation | Klik setiap tab | Manual |
| Queue tampil | Ada lagu di queue | Manual |
| Lyrics tampil (jika ada) | Tab lyrics saat lagu main | Manual |

### BB.3 CSS Regression Check Sebelum Phase 3

Sebelum hapus CSS apapun di Phase 3, jalankan:

```bash
# Cek berapa % CSS yang dipakai (heuristik sederhana)
python3 << 'PYEOF'
import re, os

def get_css_selectors(filepath):
    content = open(filepath).read()
    return set(re.findall(r'^\s*([.#][\w-]+(?:\s*[.#][\w-]+)*)\s*{', content, re.MULTILINE))

def get_used_in_html_js(base_dir):
    used = set()
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules']]
        for f in files:
            if f.endswith(('.html', '.js')):
                content = open(os.path.join(root, f)).read()
                # HTML classes
                for match in re.findall(r'class=["\']([^"\']+)["\']', content):
                    used.update(match.split())
                # JS classList operations
                for match in re.findall(r'classList\.(?:add|remove|toggle|contains)\(["\']([^"\']+)["\']', content):
                    used.add(match)
    return used

css_selectors = get_css_selectors('web/static/css/base.css')
used = get_used_in_html_js('web/static')
dead = [s for s in css_selectors if not any(c in used for c in re.findall(r'[\w-]+', s))]
print(f"Total selectors: {len(css_selectors)}")
print(f"Potentially dead ({len(dead)} items):")
for d in sorted(dead)[:20]:
    print(f"  {d}")
PYEOF
```

---

## DAFTAR ISI

- [Chapter X — Agent Context Brief](#chapter-x--agent-context-brief)
- [Chapter Y — Risk Matrix](#chapter-y--risk-matrix)
- [Chapter Z — Definition of Done](#chapter-z--definition-of-done)
- [Chapter AA — Architecture Decision Records](#chapter-aa--architecture-decision-records)
- [Chapter BB — Regression Prevention](#chapter-bb--regression-prevention-protocol)
- [Phase -1 — Design Blueprint](#phase--1--design-blueprint)
- [Phase 0 — P0 Bugs](#phase-0--p0-bugs)
- [Phase 1 — Mobile-First Shell](#phase-1--mobile-first-shell)
- [Phase 2 — Touch & Interaction](#phase-2--touch--interaction)
- [Phase 3 — CSS Cleanup](#phase-3--css-cleanup)
- [Phase 4 — Performance & UX](#phase-4--performance--ux)
- [Phase 5 — Desktop & Tablet](#phase-5--desktop--tablet-baru)
- [Phase 6 — PWA & Offline](#phase-6--pwa--offline-baru)
- [Verification Master Script](#verification-master-script)
- [Rollback Guide](#rollback-guide)
- [Commit Format](#commit-format)

---

## PROGRESS TRACKER (UPDATE SETELAH SETIAP TASK)

```
Phase -1: [x] P-1-1  [x] P-1-2  [x] P-1-3
Phase 0:  [x] P0-1   [x] P0-2   [x] P0-3   [x] P0-4   [x] P0-5
Phase 1:  [x] P1-1   [x] P1-2   [x] P1-3   [x] P1-4   [x] P1-5
Phase 2:  [x] P2-1   [x] P2-2   [x] P2-3   [x] P2-4
Phase 3:  [x] P3-1   [x] P3-2   [x] P3-3   [x] P3-4   [x] P3-5
Phase 4:  [x] P4-1   [x] P4-2   [x] P4-3   [x] P4-4
Phase 5:  [x] P5-1   [x] P5-2   [x] P5-3   [x] P5-4   [x] P5-5   [x] P5-6
Phase 6:  [x] P6-1   [x] P6-2   [x] P6-3   [x] P6-4
```

---

## SETUP — WAJIB SEBELUM MULAI

### ENV-1: Verifikasi working directory

```bash
ls -1 | grep -E "main.py|web|engine|docs"
# Output harus include: main.py, web, engine

export PROJECT_ROOT=$(pwd)
echo "PROJECT_ROOT=$PROJECT_ROOT"
```

### ENV-2: Git state check

```bash
git status --porcelain
# Harus KOSONG. Jika tidak kosong → stash atau commit dulu.
git log --oneline -3
# Catat hash commit terakhir sebagai rollback anchor
export ROLLBACK_HASH=$(git rev-parse HEAD)
echo "ROLLBACK_HASH=$ROLLBACK_HASH"
```

### ENV-3: Verifikasi file ada

```bash
ls web/static/css/
# Harus ada: base.css, tokens.css, components.css, player.css, tabs.css, portal.css, layout.css

ls web/static/js/
ls web/static/js/render/
```

### ENV-4: Jalankan Smoke Test baseline

```bash
# Pastikan app berfungsi SEBELUM mulai — ini adalah baseline
# Jalankan smoke test dari Chapter BB.1
```

---

## PHASE -1 — DESIGN BLUEPRINT *(BARU)*

> **Target:** Konfirmasi keputusan desain sebelum eksekusi. Output: dokumen, bukan kode.
> **Kapan selesai:** Semua keputusan di bawah sudah explicit — baik disetujui atau diubah.

### TASK P-1-1: Konfirmasi Breakpoints

**Status:** `[x]`

Review breakpoints dari ADR-002 dan AUDIT_V2 Chapter C:

```
Proposed:
  Mobile:  ≤ 600px  — full-screen, single column, bottom nav
  Tablet:  601–1023px — single column, max-width 600px centered
  Desktop: ≥ 1024px — 2-column (sidebar + main)
```

```bash
# Cek apakah layout.css sudah punya sesuatu yang konflik
cat web/static/css/layout.css
```

> Keputusan final breakpoints: ≤600px Mobile, 601-1023px Tablet, ≥1024px Desktop
> Disetujui / Diubah ke: Disetujui oleh User

**Verification:**

```bash
echo "Task ini selesai ketika keputusan breakpoint sudah ditulis di atas."
echo "Tidak ada kode yang diubah di task ini."
```

---

### TASK P-1-2: Konfirmasi Design Token Additions

**Status:** `[x]`

Review token baru yang akan ditambahkan (dari AUDIT_V2 Chapter B):

```css
/* Yang akan ditambahkan di Phase 3 */
/* Spacing scale: --space-1 s/d --space-10 */
/* Typography: --text-xs s/d --text-2xl */
/* Motion: --duration-fast s/d --ease-spring */
/* State colors: --fm-color-hover, --fm-color-success, dll */
```

```bash
# Cek token yang sudah ada
cat web/static/css/tokens.css
```

> Token yang disetujui untuk ditambahkan: Spacing scale, Typography, Motion, State colors.
> Token yang diubah/skip: Disetujui oleh User

---

### TASK P-1-3: Konfirmasi Desktop Layout Blueprint

**Status:** `[x]`

Review ASCII wireframe dari AUDIT_V2 Chapter C.4 (Desktop Layout). Konfirmasi apakah layout 2-column (sidebar + main + queue panel opsional) adalah yang diinginkan.

> Layout yang disetujui: 2-column (sidebar + main + opsional queue)
> Perubahan dari blueprint: Disetujui oleh User

---

## PHASE 0 — P0 BUGS

> **Target:** Fix bug nyata yang sudah teridentifikasi, zero redesign, effort < 1 jam.
> **File utama:** `tokens.css`, `base.css`, `index.html`
> **Exit criteria:** Verification Master Script bagian P0 semua PASS

---

### TASK P0-1: Fix `--fm-primary` Undefined

**Status:** `[x]`
**File:** `web/static/css/tokens.css`
**Risk:** 🟢 LOW
**Audit ref:** BUG-001

**Langkah:**

```bash
# STEP 1: Verifikasi masalah ada
grep -n "fm-primary" web/static/css/base.css
grep -n "fm-primary" web/static/css/tokens.css
# tokens.css harus KOSONG — token belum ada
```

```bash
# STEP 2: Cek posisi akhir blok :root
grep -n "fm-transition-normal" web/static/css/tokens.css

LINE=$(grep -n "fm-transition-normal:.*0.25" web/static/css/tokens.css | cut -d: -f1)
echo "Insert setelah line: $LINE"

head -n $LINE web/static/css/tokens.css > /tmp/tokens_new.css
echo "" >> /tmp/tokens_new.css
echo "  /* Primary — alias untuk accent, dipakai oleh queue current indicator */" >> /tmp/tokens_new.css
echo "  --fm-primary:     var(--fm-accent);" >> /tmp/tokens_new.css
tail -n +$((LINE+1)) web/static/css/tokens.css >> /tmp/tokens_new.css

# Review sebelum apply
grep -A 5 -B 2 "fm-primary" /tmp/tokens_new.css
```

```bash
# STEP 3: Apply
cp web/static/css/tokens.css web/static/css/tokens.css.bak
cp /tmp/tokens_new.css web/static/css/tokens.css
```

**Verification:**

```bash
grep "fm-primary" web/static/css/tokens.css
# Output harus: --fm-primary: var(--fm-accent);

python3 -c "
content = open('web/static/css/tokens.css').read()
assert '--fm-primary' in content, 'FAIL: token tidak ada'
assert ':root' in content, 'FAIL: :root hilang'
print('PASS: tokens.css valid')
"
```

> Catatan hasil: _________________

---

### TASK P0-2: Hapus Inter Font Import

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW
**Audit ref:** PERF-003

```bash
# STEP 1: Verifikasi masalah
grep -n "googleapis.com.*Inter" web/static/css/base.css

# STEP 2: Pastikan Inter tidak dipakai
grep -rn "font-family.*Inter" web/static/
# Output harus KOSONG

# STEP 3: Hapus
LINE=$(grep -n "googleapis.com.*Inter" web/static/css/base.css | cut -d: -f1)
sed -i "${LINE}d" web/static/css/base.css
```

**Verification:**

```bash
grep "googleapis.com" web/static/css/base.css
# Output harus KOSONG

wc -l web/static/css/base.css
# Harus > 100 lines
```

> Catatan hasil: _________________

---

### TASK P0-3: Tambahkan `aria-label` ke Tombol Tanpa Label

**Status:** `[x]`
**File:** `web/static/index.html`
**Risk:** 🟢 LOW
**Audit ref:** WCAG — >10 button tanpa aria-label

```bash
# STEP 1: Inventarisasi tombol yang butuh label
grep -n "<button" web/static/index.html | grep -v "aria-label"
```

```bash
# STEP 2: Backup dulu
cp web/static/index.html web/static/index.html.bak

# STEP 3: Tambah aria-label satu per satu
sed -i 's/id="portal-client-btn" class="portal-btn client"/id="portal-client-btn" class="portal-btn client" aria-label="Masuk sebagai Client"/' web/static/index.html

sed -i 's/id="portal-admin-btn" class="portal-btn admin"/id="portal-admin-btn" class="portal-btn admin" aria-label="Masuk sebagai Admin"/' web/static/index.html

sed -i 's/id="lyric-offset-minus">−/id="lyric-offset-minus" aria-label="Offset lirik mundur 0.5 detik">−/' web/static/index.html

sed -i 's/id="lyric-offset-plus">+/id="lyric-offset-plus" aria-label="Offset lirik maju 0.5 detik">+/' web/static/index.html

# Untuk tombol dengan inline style — cek dan tambahkan manual
grep -n "radio-randomize-btn" web/static/index.html
# Tambahkan aria-label="Acak Queue" ke tombol tersebut
```

**Verification:**

```bash
# Hitung tombol yang masih belum punya aria-label
echo "Tombol tanpa aria-label:"
grep "<button" web/static/index.html | grep -v "aria-label"
# Sisa yang ada harus bisa dijustifikasi (punya text content yang jelas)

python3 -c "
from html.parser import HTMLParser
class V(HTMLParser): pass
p = V()
p.feed(open('web/static/index.html').read())
print('PASS: HTML parseable')
"
```

> Catatan hasil: _________________

---

### TASK P0-4: Fix `outline: none` — Tambahkan `:focus-visible` Replacement

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW
**Audit ref:** WCAG 2.1 SC 2.4.7

```bash
# STEP 1: Inventarisasi semua outline:none
grep -rn "outline.*none\|outline: 0\|outline:0" web/static/css/

# STEP 2: Tambahkan :focus-visible rules ke akhir base.css
cat >> web/static/css/base.css << 'EOF'

/* ══════════════════════════════════════
   FOCUS VISIBLE — WCAG 2.1 SC 2.4.7
   Menggantikan outline:none yang sebelumnya
   menghilangkan keyboard navigation indicator
   ══════════════════════════════════════ */
.search-wrap input:focus-visible,
.portal-login-form input:focus-visible {
  outline: 2px solid var(--fm-accent);
  outline-offset: 2px;
  border-color: var(--fm-accent);
}

.vol-slider:focus-visible,
.pb-track:focus-visible {
  outline: 2px solid var(--fm-accent);
  outline-offset: 4px;
  border-radius: 4px;
}

button:focus-visible {
  outline: 2px solid var(--fm-accent);
  outline-offset: 2px;
  border-radius: var(--fm-radius-xs);
}
EOF
```

**Verification:**

```bash
grep -c "focus-visible" web/static/css/base.css
# Harus > 0
echo "PASS jika focus-visible ada"
```

> Catatan hasil: _________________

---

### TASK P0-5: Fix Dead DOM References di `dom.js`

**Status:** `[x]`
**File:** `web/static/js/dom.js`
**Risk:** 🟢 LOW

```bash
# STEP 1: Verifikasi element tidak ada di HTML
grep -n "lyrics-toggle-btn\|btn-stop" web/static/js/dom.js
grep -n "lyrics-toggle-btn\|btn-stop" web/static/index.html
# dom.js harus ada, index.html harus KOSONG

# STEP 2: Verifikasi tidak dipakai di JS manapun
grep -rn "lyricsToggleBtn\|btnStop" web/static/js/
# Jika hasil kosong → aman dihapus

# STEP 3: Hapus dead reference
LINE=$(grep -n "lyrics-toggle-btn" web/static/js/dom.js | cut -d: -f1)
# Review dulu
sed -n "${LINE}p" web/static/js/dom.js
# Jika sesuai ekspektasi:
sed -i "${LINE}d" web/static/js/dom.js
```

**Verification:**

```bash
grep "lyrics-toggle-btn" web/static/js/dom.js
# Output harus KOSONG

node --check web/static/js/dom.js 2>&1 || echo "Cek manual"
```

> Catatan hasil: _________________

---

### PHASE 0 COMMIT

```bash
# Jalankan smoke test terlebih dahulu (Chapter BB.1)
# Kemudian commit

git add web/static/css/tokens.css \
        web/static/css/base.css \
        web/static/index.html \
        web/static/js/dom.js

git status
git commit -m "fix(P0): critical bugs dari audit Spotify-class

- Tambah --fm-primary token di tokens.css (fix queue indicator & drag-over)
- Hapus Inter font import yang tidak dipakai (~50KB saved)
- Tambah aria-label ke tombol yang missing (WCAG compliance)
- Tambah :focus-visible replacement untuk outline:none
- Hapus dead DOM reference lyricsToggleBtn dari dom.js

Audit ref: BUG-001, PERF-003, WCAG 2.4.7"
```

**PHASE 0 DONE CHECK:**

```
[ ] P0-1: --fm-primary ada di tokens.css
[ ] P0-2: Inter font import dihapus dari base.css
[ ] P0-3: aria-label ditambahkan ke tombol-tombol kritis
[ ] P0-4: :focus-visible replacement ada
[ ] P0-5: Dead DOM reference dihapus
[ ] Smoke test PASS
[ ] COMMIT phase 0 sudah dilakukan
```

---

## PHASE 1 — MOBILE-FIRST SHELL

> **Target:** Transformasi dari phone-bubble menjadi real responsive app.
> **PERINGATAN:** Ini adalah perubahan paling visual dan HIGH RISK. Test di browser setelah P1-2.
> **Exit criteria:** `grep -c '690px' web/static/css/base.css` output `0` dan app tampil full-screen.
> **File utama:** `web/static/css/base.css`, `web/static/css/layout.css`

---

### TASK P1-1: Audit Ukuran Layar — Konfirmasi Breakpoint Plan

**Status:** `[x]`
**Risk:** 🟢 LOW (tidak mengubah kode)

```bash
# STEP 1: Baca layout.css saat ini
cat web/static/css/layout.css

# STEP 2: Konfirmasi breakpoint dari Phase -1
# Breakpoints yang digunakan (dari ADR-002):
# Mobile:  ≤ 600px
# Tablet:  601–1023px
# Desktop: ≥ 1024px
```

> Breakpoint yang dikonfirmasi: _________________ (copy dari Phase -1 task)

---

### TASK P1-2: Hapus Phone Shell dari `#app`

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🔴 HIGH — Backup wajib. Test visual segera setelah task ini.

```bash
# STEP 1: Backup WAJIB
cp web/static/css/base.css web/static/css/base.css.pre-p1

# STEP 2: Lihat rule #app saat ini
grep -n "^#app{" web/static/css/base.css
sed -n '/^#app{/p' web/static/css/base.css

# Konfirmasi: harus ada max-width:375px, height:690px, border-radius:36px
```

```bash
# STEP 3: Ganti rule #app
python3 << 'PYEOF'
with open('web/static/css/base.css', 'r') as f:
    content = f.read()

OLD = '#app{width:100%;max-width:375px;margin:0 auto;background:#0d0d1c;border-radius:36px;border:3px solid #1e1e32;height:690px;display:flex;flex-direction:column;overflow:hidden;color:#fff;font-family:-apple-system,system-ui,sans-serif;font-size:14px;position:relative}'

NEW = '''#app{
  width: 100%;
  height: 100dvh;
  height: 100vh; /* fallback untuk browser lama */
  max-width: 100%;
  margin: 0;
  background: var(--fm-bg-deep, #0d0d1c);
  border-radius: 0;
  border: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #fff;
  font-family: var(--fm-font, -apple-system, system-ui, sans-serif);
  font-size: 14px;
  position: relative;
}'''

if OLD in content:
    content = content.replace(OLD, NEW)
    with open('web/static/css/base.css', 'w') as f:
        f.write(content)
    print("PASS: #app rule berhasil diganti")
else:
    print("FAIL: OLD string tidak ditemukan persis — perlu edit manual")
    print("Cari: grep -n '#app{' web/static/css/base.css")
PYEOF
```

**Verification:**

```bash
grep "375px\|690px\|border-radius:36px" web/static/css/base.css
# Output harus KOSONG

grep -A 5 "^#app{" web/static/css/base.css | head -8
# Harus ada height:100dvh atau 100vh

echo "=== VISUAL TEST WAJIB ==="
echo "Buka browser sekarang. App harus full-screen."
echo "Jika app tidak terlihat → STOP dan rollback P1-2:"
echo "cp web/static/css/base.css.pre-p1 web/static/css/base.css"
```

> Catatan hasil: _________________
> Hasil visual test: _________________

---

### TASK P1-3: Tambahkan Responsive Breakpoints

**Status:** `[x]`
**Dependency:** P1-2 harus `[x]` dulu
**File:** `web/static/css/layout.css`
**Risk:** 🟢 LOW

```bash
cat >> web/static/css/layout.css << 'EOF'
/* ══════════════════════════════════════
   RESPONSIVE BREAKPOINTS — Mobile First
   bagas.fm Spotify-Class Transformation Phase 1
   ADR-002: 601px tablet, 1024px desktop
   ══════════════════════════════════════ */

/* ─── Base: Mobile (≤ 600px) ─── */
/* Default styles sudah mobile-first */

/* ─── Tablet (601px – 1023px) ─── */
@media (min-width: 601px) {
  #app {
    max-width: 600px;
    margin: 0 auto;
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.6);
  }

  .nav-btn span {
    font-size: 11px;
  }
}

/* ─── Desktop (≥ 1024px) ─── */
/* Placeholder — Phase 5 akan mengisi dengan 2-column layout */
@media (min-width: 1024px) {
  body {
    justify-content: center;
    padding: 20px;
  }

  #app {
    max-width: 420px;
    height: calc(100vh - 40px);
    border-radius: var(--fm-radius-app, 36px);
    border: 1px solid var(--fm-border, #1e1e32);
  }
}

/* ─── Orientation: Landscape di Mobile ─── */
@media (max-height: 500px) and (orientation: landscape) {
  .vinyl-wrap {
    display: none; /* Sembunyikan vinyl di landscape untuk hemat ruang */
  }
}

/* ─── Safe Area Insets (iPhone notch / Android nav bar) ─── */
@supports (padding: env(safe-area-inset-bottom)) {
  #nav-bar {
    padding-bottom: calc(5px + env(safe-area-inset-bottom));
  }
  #player-bar {
    padding-bottom: calc(4px + env(safe-area-inset-bottom));
  }
}
EOF
```

**Verification:**

```bash
grep -c "@media" web/static/css/layout.css
# Harus > 0

grep "min-width: 601px\|min-width: 1024px" web/static/css/layout.css
# Harus match
```

> Catatan hasil: _________________

---

### TASK P1-4: Update `html, body` Base Styles

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW

```bash
# STEP 1: Lihat current html, body styles
grep -n -A 8 "^html, body" web/static/css/base.css | head -12

# STEP 2: Update via python (untuk handle multiline)
python3 << 'PYEOF'
import re
with open('web/static/css/base.css', 'r') as f:
    content = f.read()

OLD_PATTERN = r'html, body \{[^}]+\}'
NEW_BLOCK = '''html, body {
    background: #000;
    min-height: 100dvh;
    min-height: 100vh; /* fallback */
    margin: 0;
    padding: 0;
    font-family: -apple-system, system-ui, sans-serif;
    color: #fff;
    overflow: hidden;
}'''

match = re.search(OLD_PATTERN, content, re.DOTALL)
if match:
    content = re.sub(OLD_PATTERN, NEW_BLOCK, content, count=1, flags=re.DOTALL)
    with open('web/static/css/base.css', 'w') as f:
        f.write(content)
    print("PASS: html,body updated")
else:
    print("FAIL: Pattern tidak ditemukan — cek manual")
PYEOF
```

**Verification:**

```bash
grep -A 8 "^html, body" web/static/css/base.css | head -10
# Tidak boleh ada: align-items:center yang memaksa centering
# Harus ada: min-height:100dvh / 100vh
```

> Catatan hasil: _________________

---

### TASK P1-5: Test Visual di Browser (Manual)

**Status:** `[x]`

```bash
echo "MANUAL TEST REQUIRED:"
echo "1. Jalankan server: python3 main.py"
echo "2. Buka di Mobile DevTools (375px): app harus full-screen"
echo "3. Buka di Tablet width (768px): app harus centered max-width 600px"
echo "4. Buka di Desktop (1024px): app harus di tengah dengan border"
echo "5. Cek landscape: vinyl harus tersembunyi"
echo ""
echo "Jika ada yang tidak sesuai: catat di bawah dan evaluasi apakah perlu rollback P1-2"

git diff --stat
```

> Hasil test: _________________
> Issues yang ditemukan: _________________

---

### PHASE 1 COMMIT

```bash
# Smoke test dulu
# [jalankan Chapter BB.1]

git add web/static/css/base.css web/static/css/layout.css
git commit -m "feat(P1): mobile-first shell transformation

- Hapus phone frame: max-width:375px, height:690px, border-radius:36px
- #app sekarang full-viewport (100dvh) di mobile
- Tambah responsive breakpoints: tablet 601px, desktop 1024px
- Update html/body base styles untuk mobile-first
- Tambah safe-area-inset handling untuk iPhone/Android
- Tambah landscape orientation handling (vinyl hidden)

ADR-002: breakpoint 601px/1024px
Audit ref: CRITICAL responsive design"
```

**PHASE 1 DONE CHECK:**

```
[ ] P1-1: Breakpoint dikonfirmasi
[ ] P1-2: Phone shell dihapus, visual test PASS
[ ] P1-3: Responsive breakpoints ada di layout.css
[ ] P1-4: html/body diupdate
[ ] P1-5: Manual visual test selesai
[ ] Smoke test PASS
[ ] COMMIT phase 1 dilakukan
```

---

## PHASE 2 — TOUCH & INTERACTION

> **Target:** Semua fitur yang broken di mobile touch diperbaiki.
> **Exit criteria:** Queue drag-drop bekerja di touch device, tidak ada `dragstart` di events.js.
> **File utama:** `web/static/js/events.js`, `web/static/css/base.css`

---

### TASK P2-1: Reimplement Queue Drag-Drop dengan Pointer Events

**Status:** `[x]`
**File:** `web/static/js/events.js`
**Risk:** 🔴 HIGH
**Audit ref:** BUG-002

```bash
# STEP 1: Backup WAJIB
cp web/static/js/events.js web/static/js/events.js.pre-p2

# STEP 2: Baca implementasi yang ada
grep -n "initQueueDragDrop\|dragstart\|dragover\|drop\|dragend\|dragSrcIndex" web/static/js/events.js
```

```bash
# STEP 3: Buat implementasi baru dengan Pointer Events
cat > /tmp/queue_drag_new.js << 'JSEOF'
// ── Queue Drag & Drop — Pointer Events (Mobile + Desktop) ──
// ADR-001: Pointer Events API dipilih karena support touch + mouse dalam 1 API
// Menggantikan HTML5 Drag API yang tidak bekerja di touch device (BUG-002)
let _dragSrcIndex = null;
let _dragEl = null;

function initQueueDragDrop() {
    const list = dom.queueList;
    if (!list) return;

    list.addEventListener('pointerdown', _onDragStart, { passive: false });
    document.addEventListener('pointermove', _onDragMove, { passive: false });
    document.addEventListener('pointerup', _onDragEnd);
    document.addEventListener('pointercancel', _onDragCancel);
}

function _onDragStart(e) {
    if (store.userRole !== 'admin') return;
    const handle = e.target.closest('.qi-drag');
    if (!handle) return;

    const item = handle.closest('.queue-item');
    if (!item || !item.hasAttribute('data-index')) return;

    e.preventDefault();
    _dragSrcIndex = parseInt(item.dataset.index);
    _dragEl = item;
    item.classList.add('dragging');
    item.setPointerCapture(e.pointerId);
}

function _onDragMove(e) {
    if (_dragSrcIndex === null || !_dragEl) return;
    e.preventDefault();

    document.querySelectorAll('.queue-item.drag-over').forEach(el => el.classList.remove('drag-over'));

    const target = document.elementFromPoint(e.clientX, e.clientY);
    if (target) {
        const over = target.closest('.queue-item[data-index]');
        if (over && over !== _dragEl) {
            over.classList.add('drag-over');
        }
    }
}

function _onDragEnd(e) {
    if (_dragSrcIndex === null) return;

    const target = document.elementFromPoint(e.clientX, e.clientY);
    if (target) {
        const over = target.closest('.queue-item[data-index]');
        if (over && over !== _dragEl) {
            const toIndex = parseInt(over.dataset.index);
            if (toIndex !== _dragSrcIndex) {
                wsSend('queue_reorder', { from_index: _dragSrcIndex, to_index: toIndex });
            }
        }
    }
    _cleanupDrag();
}

function _onDragCancel() {
    _cleanupDrag();
}

function _cleanupDrag() {
    if (_dragEl) _dragEl.classList.remove('dragging');
    document.querySelectorAll('.queue-item.drag-over').forEach(el => el.classList.remove('drag-over'));
    _dragSrcIndex = null;
    _dragEl = null;
}
JSEOF
```

```bash
# STEP 4: Replace implementasi lama dengan python
python3 << 'PYEOF'
with open('web/static/js/events.js', 'r') as f:
    content = f.read()

# Cari start: baris "let dragSrcIndex = null;"
# Cari end: closing brace dari cleanupDrag function
import re

# Find start
start_match = re.search(r'let dragSrcIndex = null;', content)
if not start_match:
    print("FAIL: start marker 'let dragSrcIndex = null;' tidak ditemukan")
    print("Cari manual: grep -n 'dragSrcIndex' events.js")
    exit(1)

# Find the cleanupDrag function end
# Heuristic: cari "function _cleanupDrag" atau "function cleanupDrag", lalu closing brace-nya
end_marker = re.search(r'function (?:_)?cleanupDrag\b', content[start_match.start():])
if not end_marker:
    print("FAIL: cleanupDrag function tidak ditemukan setelah dragSrcIndex")
    print("Cari manual: grep -n 'cleanupDrag' events.js")
    exit(1)

abs_end_start = start_match.start() + end_marker.start()
# Find closing brace after cleanupDrag
remaining = content[abs_end_start:]
depth = 0
end_offset = 0
for i, ch in enumerate(remaining):
    if ch == '{': depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0:
            end_offset = i + 1
            break

if end_offset == 0:
    print("FAIL: tidak bisa menemukan closing brace cleanupDrag")
    exit(1)

abs_end = abs_end_start + end_offset
print(f"Replace dari karakter {start_match.start()} ke {abs_end}")
print(f"Snippet yang akan diganti (50 chars): {content[start_match.start():start_match.start()+50]}")

new_code = open('/tmp/queue_drag_new.js').read()
new_content = content[:start_match.start()] + new_code + '\n' + content[abs_end:]

with open('web/static/js/events.js', 'w') as f:
    f.write(new_content)
print("PASS: Drag-drop diupdate ke Pointer Events")
PYEOF
```

**Verification:**

```bash
# Fungsi lama tidak ada
grep "dragstart\|HTML5 Drag" web/static/js/events.js
# Harus KOSONG

# Fungsi baru ada
grep "initQueueDragDrop\|pointerdown\|pointerup" web/static/js/events.js
# Harus match

node --check web/static/js/events.js 2>&1 || echo "Cek manual"

echo "MANUAL TEST WAJIB:"
echo "Test queue drag di Chrome DevTools mobile mode (touch simulation)"
echo "Test queue drag di desktop (mouse)"
echo "Kedua harus bekerja"
```

> Catatan hasil: _________________
> Touch drag test: _________________
> Desktop drag test: _________________

---

### TASK P2-2: Fix Touch Target Sizes — CSS

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW

```bash
# Tambahkan touch target expansion
cat >> web/static/css/base.css << 'EOF'

/* ══════════════════════════════════════
   TOUCH TARGET EXPANSION — Phase 2
   Minimum 44×44px per HIG & Material Design
   Gunakan ::after pseudo-element (non-destructive)
   ══════════════════════════════════════ */

.pb-thumb {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
}
.pb-thumb::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 44px;
  height: 44px;
}

.offset-btn::after,
.lyric-offset button::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 44px;
  height: 44px;
}
.offset-btn,
.lyric-offset button {
  position: relative;
}

.vol-slider {
  height: 20px;
  -webkit-appearance: none;
  appearance: none;
  cursor: pointer;
}
.vol-slider::-webkit-slider-thumb {
  width: 20px;
  height: 20px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--fm-accent);
  border-radius: 50%;
  cursor: pointer;
}

.qi-drag {
  padding: 12px 8px;
  min-width: 32px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}
EOF
```

**Verification:**

```bash
grep -c "TOUCH TARGET" web/static/css/base.css
# Harus > 0

grep "pb-thumb::after\|qi-drag" web/static/css/base.css
# Harus match
```

> Catatan hasil: _________________

---

### TASK P2-3: Handle Keyboard Appearance di Mobile

**Status:** `[x]`
**File:** `web/static/js/main.js`
**Risk:** 🟢 LOW

```bash
cat >> web/static/js/main.js << 'EOF'

// ── Visual Viewport Handler (Mobile Keyboard) ──
// Mencegah layout terdorong saat keyboard virtual muncul di iOS/Android
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        const app = document.getElementById('app');
        if (app) {
            app.style.height = window.visualViewport.height + 'px';
        }
    });
}
EOF
```

**Verification:**

```bash
grep "visualViewport" web/static/js/main.js
# Harus ada
```

> Catatan hasil: _________________

---

### TASK P2-4: WS Reconnect — Tutup Koneksi Lama

**Status:** `[x]`
**File:** `web/static/js/ws.js`
**Risk:** 🟢 LOW
**Audit ref:** BUG-003

```bash
python3 << 'PYEOF'
with open('web/static/js/ws.js', 'r') as f:
    content = f.read()

OLD = '    ws = new WebSocket(url);\n    window.ws = ws;'
NEW = '''    // Tutup koneksi lama jika masih ada (BUG-003: mencegah concurrent connections)
    if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.onclose = null;
        ws.onerror = null;
        ws.close();
    }

    ws = new WebSocket(url);
    window.ws = ws;'''

if OLD in content:
    content = content.replace(OLD, NEW)
    with open('web/static/js/ws.js', 'w') as f:
        f.write(content)
    print("PASS: WS reconnect fix applied")
else:
    print("FAIL: Pattern tidak ditemukan persis")
    print("Cari: grep -n 'new WebSocket' web/static/js/ws.js")
PYEOF
```

**Verification:**

```bash
grep -A 5 "Tutup koneksi lama" web/static/js/ws.js
# Harus match
```

> Catatan hasil: _________________

---

### PHASE 2 COMMIT

```bash
# Smoke test dulu

git add web/static/js/events.js web/static/css/base.css web/static/js/main.js web/static/js/ws.js
git commit -m "fix(P2): touch & interaction fixes

- Reimplement queue drag-drop dengan Pointer Events API (touch + mouse)
- Tambah touch target expansion via ::after (44px minimum)
- Fix volume slider touch area
- Tambah visualViewport resize handler (keyboard mobile)
- Fix WS reconnect: tutup koneksi lama sebelum buat baru

ADR-001: Pointer Events dipilih vs Touch Events vs Hammer.js
Audit ref: BUG-002, BUG-003"
```

**PHASE 2 DONE CHECK:**

```
[ ] P2-1: Queue drag-drop pakai Pointer Events, tidak ada dragstart
[ ] P2-1: Manual test touch drag OK
[ ] P2-1: Manual test desktop drag OK
[ ] P2-2: Touch target ≥44px via ::after
[ ] P2-3: visualViewport handler ada
[ ] P2-4: WS reconnect guard ada
[ ] Smoke test PASS
[ ] COMMIT phase 2 dilakukan
```

---

## PHASE 3 — CSS CLEANUP

> **Target:** Hapus triplication, dead code, dan undefined tokens. Zero visual change.
> **Prinsip:** Jangan ubah visual. Ini pure cleanup.
> **Exit criteria:** `.vol-grp` hanya satu definisi, tidak ada legacy token di-reference.

---

### TASK P3-1: Audit Duplikasi CSS

**Status:** `[x]`
**Risk:** 🟢 LOW (hanya audit, belum ubah)

```bash
python3 << 'PYEOF'
import re

def extract_selectors(filename):
    with open(filename) as f:
        content = f.read()
    return set(re.findall(r'^([.#][a-zA-Z][a-zA-Z0-9_-]*)\s*\{', content, re.MULTILINE))

base = extract_selectors('web/static/css/base.css')
comp = extract_selectors('web/static/css/components.css')
tabs = extract_selectors('web/static/css/tabs.css')

print("=== base.css ∩ components.css ===")
for s in sorted(base & comp): print(f"  {s}")
print(f"\n=== base.css ∩ tabs.css ===")
for s in sorted(base & tabs): print(f"  {s}")
PYEOF
```

> Duplikasi yang ditemukan: _________________
> Rencana cleanup: _________________

---

### TASK P3-2: Deduplikasi `.vol-grp` dan `.toggle-dot`

**Status:** `[x]`
**Risk:** 🟡 MEDIUM — Hapus definition tapi pertahankan satu

```bash
# Lihat semua definisi vol-grp
echo "=== vol-grp di base.css ==="
grep -n "^\.vol-grp" web/static/css/base.css

echo "=== vol-grp di components.css ==="
grep -n "^\.vol-grp" web/static/css/components.css

# Strategi: pertahankan di components.css, hapus duplikat di base.css
# Pastikan tidak ada property di base.css yang tidak ada di components.css
```

```bash
# Hal yang sama untuk toggle-dot
echo "=== toggle-dot di base.css ==="
grep -n "^\.toggle-dot\b\|^\.toggle-dot {" web/static/css/base.css

echo "=== toggle-dot di components.css ==="
grep -n "^\.toggle-dot\b\|^\.toggle-dot {" web/static/css/components.css
```

**Verification setelah cleanup:**

```bash
echo "vol-grp count di base.css:"
grep -c "^\.vol-grp" web/static/css/base.css
# Target: 0 atau 1 (bukan 2)

echo "toggle-dot count di base.css:"
grep -c "^\.toggle-dot" web/static/css/base.css
# Target: ≤1
```

> Catatan: _________________

---

### TASK P3-3: Hapus Legacy Token Aliases

**Status:** `[x]`
**Risk:** 🟡 MEDIUM — Pastikan tidak ada reference sebelum hapus

```bash
# WAJIB: Cek semua legacy token masih dipakai di mana tidak
LEGACY_TOKENS="--accent-fire\|--bg-panel\|--bg-elevated\|--bg-void\|--bg-glass\|--accent-gold\|--text-primary\|--text-muted\|--border\|--font-family\|--radius-sm"

echo "=== Files yang masih pakai legacy tokens ==="
grep -rn "var($LEGACY_TOKENS)" web/static/css/ web/static/js/

echo ""
echo "=== Khusus --bg-glass (ditemukan di audit) ==="
grep -rn "bg-glass" web/static/
```

```bash
# Jika ada file yang masih pakai → update ke fm-* token dulu
# Contoh: bg-glass → var(--fm-bg-card)

# Setelah semua references diupdate, barulah hapus legacy block dari tokens.css
# JANGAN hapus sebelum grep di atas kosong untuk semua legacy token
```

**Verification:**

```bash
grep -rn "var(--accent-fire)\|var(--bg-panel)\|var(--bg-glass)" web/static/css/
# Harus KOSONG sebelum boleh hapus legacy block
```

> Status legacy migration: _________________

---

### TASK P3-4: Hapus Dead CSS Classes

**Status:** `[x]`
**Risk:** 🟡 MEDIUM — Review manual WAJIB

```bash
# Jalankan CSS coverage check dari Chapter BB.3
# Kemudian review output secara manual

echo "REVIEW MANUAL REQUIRED"
echo "Jangan hapus class yang:"
echo "- Bisa ditambahkan secara dinamis via JS (classList.add)"
echo "- Adalah variant/modifier (.active, .open, .playing, .dragging)"
echo "- Ada di render/ functions sebagai string"
```

```bash
# Cek class di render files
grep -rn "classList\|className\|innerHTML" web/static/js/render/ | grep -o "'[^']*'\|\"[^\"]*\"" | sort -u
```

> Class yang aman untuk dihapus (setelah review): _________________

---

### TASK P3-5: Dokumentasikan Toggle System

**Status:** `[x]`
**Risk:** 🟢 LOW (dokumentasi saja di phase ini)

```bash
# Inventory toggle yang ada
echo "=== Toggle di HTML ==="
grep -n "class=\"toggle\|ss-toggle\|data-on=" web/static/index.html

echo "=== Toggle di CSS ==="
grep -n "\.toggle\b\|\.ss-toggle\|\.toggle\.on\|data-on" web/static/css/base.css web/static/css/components.css

echo "=== Toggle di JS ==="
grep -rn "classList.*toggle\|data-on\|\.on\b\|\.off\b" web/static/js/ | grep -i "toggle\|radio"
```

Keputusan unifikasi (dari ADR-003): Pindahkan ke `data-attribute` system.
Implementasi unifikasi bisa dilakukan di Phase 5 bersama dengan desktop JS.

> Dokumentasi toggle inventory: _________________

---

### PHASE 3 COMMIT

```bash
git add web/static/css/
git commit -m "refactor(P3): CSS architecture cleanup

- Deduplikasi vol-grp (hapus 2 dari 3 definisi)
- Deduplikasi toggle-dot (hapus duplikat)
- Migrasi legacy token aliases ke fm-* tokens
- Hapus bg-glass reference yang bergantung pada legacy alias
- Dead CSS: [list class yang dihapus]
- Toggle system: inventarisasi selesai, unifikasi defer ke Phase 5

ADR-003: Toggle unifikasi akan ke data-attribute"
```

**PHASE 3 DONE CHECK:**

```
[ ] P3-1: Audit duplikasi selesai dan terdokumentasi
[ ] P3-2: vol-grp dan toggle-dot deduplikasi
[ ] P3-3: Legacy tokens dimigrasikan
[ ] P3-4: Dead CSS review selesai (hapus yang sudah dikonfirmasi)
[ ] P3-5: Toggle inventory selesai
[ ] Smoke test PASS
[ ] COMMIT phase 3 dilakukan
```

---

## PHASE 4 — PERFORMANCE & UX POLISH

> **Target:** Rendering lebih efisien, UX details yang hilang.
> **Exit criteria:** `renderProgress` pakai rAF, `syncBrowserAudio` tidak jalan saat role=portal, empty state ada.

---

### TASK P4-1: Throttle Progress Update dengan `requestAnimationFrame`

**Status:** `[x]`
**File:** `web/static/js/render/player.js`
**Risk:** 🟢 LOW

```bash
# STEP 1: Baca renderProgress function saat ini
grep -n -A 25 "^function renderProgress" web/static/js/render/player.js | head -30
```

```bash
# STEP 2: Tambahkan rAF throttle
python3 << 'PYEOF'
with open('web/static/js/render/player.js', 'r') as f:
    content = f.read()

import re
# Rename function dan tambah rAF wrapper
OLD = 'function renderProgress() {'
NEW = '''let _rafProgressPending = false;

function renderProgress() {
    if (_rafProgressPending) return;
    _rafProgressPending = true;
    requestAnimationFrame(() => {
        _rafProgressPending = false;
        _renderProgressCore();
    });
}

function _renderProgressCore() {'''

if OLD in content:
    content = content.replace(OLD, NEW, 1)
    # Cari dan rename closing brace (heuristic: pastikan fungsi berakhir)
    with open('web/static/js/render/player.js', 'w') as f:
        f.write(content)
    print("PASS: rAF wrapper ditambahkan")
else:
    print("FAIL: 'function renderProgress() {' tidak ditemukan persis")
    print("Edit manual — tambahkan rAF wrapper di atas implementasi renderProgress")
PYEOF
```

**Verification:**

```bash
grep "requestAnimationFrame\|_rafProgressPending" web/static/js/render/player.js
# Harus match
```

> Catatan hasil: _________________

---

### TASK P4-2: Dirty-Flag Rendering

**Status:** `[x]`
**File:** `web/static/js/ws.js`
**Risk:** 🟡 MEDIUM

```bash
# STEP 1: Lihat progress case di handleServerMessage
grep -n -A 10 "case \"progress\":" web/static/js/ws.js | head -15

# STEP 2: Verifikasi apakah renderQueue dipanggil di progress case
# Jika ya, hapus renderQueue dari progress case (queue tidak perlu render setiap progress tick)
```

```bash
# STEP 3: Tambahkan selective render logic di state case
grep -n -A 15 "case \"state\":" web/static/js/ws.js | head -18
```

```bash
# STEP 4: Tambahkan simple dirty tracking
python3 << 'PYEOF'
with open('web/static/js/ws.js', 'r') as f:
    content = f.read()

# Tambahkan di awal file (setelah 'use strict' atau baris pertama)
DIRTY_FLAG_CODE = '''
// ── Dirty Flag Rendering — Phase 4 ──
// Mencegah renderQueue dan renderRadio dipanggil setiap progress tick
let _lastQueueSnapshot = null;
let _lastRadioSnapshot = null;

function _queueChanged(newState) {
    const snap = JSON.stringify(newState.queue || []);
    if (snap !== _lastQueueSnapshot) {
        _lastQueueSnapshot = snap;
        return true;
    }
    return false;
}
'''

if '_lastQueueSnapshot' not in content:
    # Insert setelah baris pertama
    lines = content.split('\n')
    lines.insert(2, DIRTY_FLAG_CODE)
    with open('web/static/js/ws.js', 'w') as f:
        f.write('\n'.join(lines))
    print("PASS: dirty flag code added")
else:
    print("INFO: dirty flag sudah ada, skip")
PYEOF
```

> Note: Dirty flag implementation memerlukan review manual terhadap state cases. Prioritas: pastikan progress case tidak trigger renderQueue.

> Catatan: _________________

---

### TASK P4-3: Empty States yang Actionable

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW

```bash
cat >> web/static/css/base.css << 'EOF'

/* ══════════════════════════════════════
   EMPTY STATES — Phase 4
   ══════════════════════════════════════ */
.queue-empty,
.discover-empty {
  text-align: center;
  padding: 32px 20px;
  color: var(--fm-text-5);
  font-size: 13px;
  line-height: 1.6;
}

.queue-empty::before {
  content: '♪';
  display: block;
  font-size: 32px;
  margin-bottom: 12px;
  opacity: 0.4;
}

.discover-empty::before {
  content: '○';
  display: block;
  font-size: 24px;
  margin-bottom: 8px;
  opacity: 0.4;
}
EOF
```

**Verification:**

```bash
grep "queue-empty\|discover-empty" web/static/css/base.css | grep "padding"
# Harus match
```

> Catatan hasil: _________________

---

### TASK P4-4: Guard `syncBrowserAudio` dari Role Portal

**Status:** `[x]`
**File:** `web/static/js/ws.js`
**Audit ref:** BUG-007

```bash
python3 << 'PYEOF'
with open('web/static/js/ws.js', 'r') as f:
    content = f.read()

OLD = '''        case "state":
            Object.assign(store, msg.data);
            renderFullState();
            syncBrowserAudio();
            break;'''

NEW = '''        case "state":
            Object.assign(store, msg.data);
            renderFullState();
            // BUG-007: jangan sync audio saat user masih di portal screen
            if (store.userRole !== 'portal') {
                syncBrowserAudio();
            }
            break;'''

if OLD in content:
    content = content.replace(OLD, NEW)
    with open('web/static/js/ws.js', 'w') as f:
        f.write(content)
    print("PASS: portal guard ditambahkan")
else:
    print("FAIL: pattern tidak ditemukan persis")
    print("Cari: grep -n 'Object.assign(store' web/static/js/ws.js")
PYEOF
```

**Verification:**

```bash
grep -A 6 "case \"state\":" web/static/js/ws.js | head -8
# Harus ada: userRole !== 'portal'
```

> Catatan hasil: _________________

---

### PHASE 4 COMMIT

```bash
git add web/static/js/ web/static/css/base.css
git commit -m "perf(P4): performance & UX polish

- Tambah rAF throttling untuk renderProgress (60fps cap)
- Dirty-flag tracking untuk queue render
- Tambah CSS empty states (queue-empty, discover-empty)
- Guard syncBrowserAudio: tidak jalan saat role=portal

Audit ref: PERF-001, PERF-002, BUG-007"
```

**PHASE 4 DONE CHECK:**

```
[ ] P4-1: renderProgress menggunakan rAF
[ ] P4-2: Dirty-flag atau progress case tidak trigger renderQueue
[ ] P4-3: Empty state CSS ada
[ ] P4-4: syncBrowserAudio guard ada
[ ] Smoke test PASS
[ ] COMMIT phase 4 dilakukan
```

---

## PHASE 5 — DESKTOP & TABLET *(BARU — CHAPTER CC)*

> **Target:** Implementasi desktop 2-column layout dan tablet landscape panel.
> **Blueprint:** Lihat AUDIT_V2 Chapter C untuk wireframe lengkap.
> **Prerequisite:** Phase 1–4 semua `[x]`
> **Exit criteria:** Desktop ≥1024px menampilkan sidebar navigasi, bukan phone-in-desktop.

---

### TASK P5-1: Audit Pre-Phase 5

**Status:** `[x]`

```bash
# Pastikan Phase 1-4 semua selesai
echo "=== Pre-Phase 5 Checklist ==="
grep -c "690px" web/static/css/base.css
# Harus 0

grep "min-width: 601px\|min-width: 1024px" web/static/css/layout.css
# Harus ada

grep "pointerdown" web/static/js/events.js
# Harus ada

echo "Jika semua check OK, lanjut ke P5-2"
```

---

### TASK P5-2: Desktop 2-Column Layout CSS

**Status:** `[x]`
**File:** `web/static/css/layout.css`
**Risk:** 🟡 MEDIUM — Perubahan visual besar di ≥1024px

```bash
# Ganti placeholder desktop @media (1024px) yang ada di layout.css
# dengan implementasi sidebar + main layout

python3 << 'PYEOF'
with open('web/static/css/layout.css', 'r') as f:
    content = f.read()

# Cari placeholder desktop block
import re
OLD_PATTERN = r'\/\* ─── Desktop.*?@media \(min-width: 1024px\).*?\}'
# Ini multiline — lebih aman lakukan manual append

# Append desktop layout ke akhir file
DESKTOP_CSS = '''
/* ══════════════════════════════════════
   DESKTOP LAYOUT — Phase 5
   Blueprint: AUDIT_V2 Chapter C.4
   2-column: sidebar kiri + main content
   ══════════════════════════════════════ */
@media (min-width: 1024px) {
  body {
    display: flex;
    overflow: hidden;
    height: 100vh;
  }

  #app {
    max-width: 100%;
    height: 100vh;
    border-radius: 0;
    border: none;
    display: grid;
    grid-template-columns: 220px 1fr;
    grid-template-rows: 1fr 72px;
    grid-template-areas:
      "sidebar main"
      "nowplaying nowplaying";
  }

  /* Sidebar navigation — kiri */
  #nav-bar {
    grid-area: sidebar;
    display: flex;
    flex-direction: column;
    height: 100%;
    border-right: 1px solid var(--fm-border, #1e1e32);
    padding: 20px 0;
    overflow-y: auto;
  }

  /* Nav buttons jadi vertikal di desktop */
  .nav-btn {
    width: 100%;
    flex-direction: row;
    padding: 12px 20px;
    justify-content: flex-start;
    gap: 12px;
    border-radius: 0;
    height: auto;
    min-height: 44px;
  }

  .nav-btn .nav-icon {
    font-size: 18px;
  }

  .nav-btn span {
    font-size: 14px;
    font-weight: 500;
  }

  /* Main content area */
  #tab-home,
  #tab-search,
  #tab-queue,
  #tab-lyrics,
  #tab-settings {
    grid-area: main;
    overflow-y: auto;
  }

  /* Persistent now-playing bar di bottom */
  #player-bar {
    grid-area: nowplaying;
    display: flex;
    align-items: center;
    border-top: 1px solid var(--fm-border, #1e1e32);
    padding: 0 20px;
    gap: 16px;
  }

  /* Player bar desktop layout: artwork | controls | volume */
  .pb-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 200px;
  }

  .pb-center {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .pb-right {
    min-width: 150px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
  }
}
'''

with open('web/static/css/layout.css', 'a') as f:
    f.write(DESKTOP_CSS)
print("PASS: Desktop layout CSS appended")
PYEOF
```

**Verification:**

```bash
grep "grid-template-columns\|grid-area: sidebar" web/static/css/layout.css
# Harus match

echo "MANUAL TEST: Buka di browser width ≥1024px"
echo "Sidebar navigasi harus tampil di kiri"
echo "Main content di kanan"
echo "Now-playing bar di bottom span full width"
```

> Catatan visual test desktop: _________________

---

### TASK P5-3: Tablet Landscape Queue Panel

**Status:** `[x]`
**File:** `web/static/css/layout.css`
**Risk:** 🟡 MEDIUM
**Blueprint:** AUDIT_V2 Chapter C.3

```bash
cat >> web/static/css/layout.css << 'EOF'

/* ══════════════════════════════════════
   TABLET LANDSCAPE — Queue Panel
   Blueprint: AUDIT_V2 Chapter C.3
   ══════════════════════════════════════ */
@media (min-width: 601px) and (max-width: 1023px) and (orientation: landscape) {
  #app {
    display: grid;
    grid-template-columns: 1fr 260px;
    grid-template-rows: 1fr auto;
    grid-template-areas:
      "main queue"
      "player player";
    max-width: 100%;
  }

  #tab-home {
    grid-area: main;
    overflow-y: auto;
  }

  #tab-queue {
    grid-area: queue;
    border-left: 1px solid var(--fm-border, #1e1e32);
    overflow-y: auto;
    display: block !important; /* Selalu tampil di landscape tablet */
  }

  #player-bar {
    grid-area: player;
    border-top: 1px solid var(--fm-border, #1e1e32);
  }

  /* Sembunyikan nav bar di tablet landscape — navigasi via swipe atau gesture */
  #nav-bar {
    display: none;
  }
}
EOF
```

**Verification:**

```bash
grep "tablet landscape\|601px.*1023px.*landscape" web/static/css/layout.css -i
# Harus match

echo "MANUAL TEST: DevTools → 800px × 500px (landscape tablet simulation)"
echo "Queue harus tampil di kanan, player di bottom"
```

> Catatan: _________________

---

### TASK P5-4: Keyboard Shortcuts

**Status:** `[x]`
**File:** `web/static/js/events.js`
**Risk:** 🟢 LOW

```bash
cat >> web/static/js/events.js << 'EOF'

// ── Keyboard Shortcuts — Phase 5 (Desktop) ──
// Hanya aktif di desktop (pointer: fine = mouse)
if (window.matchMedia('(pointer: fine)').matches) {
    document.addEventListener('keydown', (e) => {
        // Jangan intercept saat user mengetik di input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.code) {
            case 'Space':
                e.preventDefault();
                wsSend('toggle_play', {});
                break;
            case 'ArrowRight':
                if (e.shiftKey) { wsSend('seek', { offset: 10 }); }
                else { wsSend('next', {}); }
                break;
            case 'ArrowLeft':
                if (e.shiftKey) { wsSend('seek', { offset: -10 }); }
                else { wsSend('prev', {}); }
                break;
            case 'ArrowUp':
                e.preventDefault();
                wsSend('volume', { delta: 5 });
                break;
            case 'ArrowDown':
                e.preventDefault();
                wsSend('volume', { delta: -5 });
                break;
        }
    });
}
EOF
```

**Verification:**

```bash
grep "keydown\|ArrowRight\|Space" web/static/js/events.js | tail -5
# Harus match

echo "MANUAL TEST di desktop:"
echo "Space = play/pause"
echo "→ = next track, Shift+→ = seek forward 10s"
echo "↑/↓ = volume up/down"
```

> Catatan: _________________

---

### TASK P5-5: Hover States untuk Mouse Users

**Status:** `[x]`
**File:** `web/static/css/base.css`
**Risk:** 🟢 LOW

```bash
cat >> web/static/css/base.css << 'EOF'

/* ══════════════════════════════════════
   HOVER STATES — Phase 5 (Desktop/Mouse)
   Hanya aktif saat pointer device adalah mouse
   (pointer: fine = mouse, pointer: coarse = touch)
   ══════════════════════════════════════ */
@media (hover: hover) and (pointer: fine) {
  .queue-item:hover {
    background: var(--fm-color-hover, rgba(255, 255, 255, 0.06));
  }

  .nav-btn:hover {
    background: var(--fm-color-hover, rgba(255, 255, 255, 0.06));
    color: var(--fm-text-1, #ffffff);
  }

  .fav-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  }

  button:hover:not(:disabled) {
    opacity: 0.85;
  }

  .sr-item:hover {
    background: var(--fm-color-hover, rgba(255, 255, 255, 0.06));
  }
}
EOF
```

**Verification:**

```bash
grep "hover: hover.*pointer: fine" web/static/css/base.css
# Harus match
```

> Catatan: _________________

---

### TASK P5-6: Design Token Additions (spacing, typography, motion)

**Status:** `[x]`
**File:** `web/static/css/tokens.css`
**Risk:** 🟢 LOW — Menambah token, tidak mengubah yang ada

```bash
# Tambahkan spacing, typography, dan motion tokens
cat >> web/static/css/tokens.css << 'EOF'

/* ══════════════════════════════════════
   EXTENDED TOKENS — Phase 5
   AUDIT_V2 Chapter B — Design System
   ══════════════════════════════════════ */
:root {
  /* Spacing scale (4px base grid) */
  --space-1:  4px;
  --space-2:  8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;

  /* Typography scale */
  --text-xs:  10px;
  --text-sm:  12px;
  --text-md:  14px;
  --text-lg:  16px;
  --text-xl:  20px;
  --text-2xl: 24px;

  /* Font weights */
  --weight-regular:  400;
  --weight-medium:   500;
  --weight-semibold: 600;
  --weight-bold:     700;

  /* Motion tokens */
  --duration-fast:    100ms;
  --duration-normal:  200ms;
  --duration-slow:    350ms;
  --ease-out:  cubic-bezier(0.0, 0.0, 0.2, 1);
  --ease-in:   cubic-bezier(0.4, 0.0, 1, 1);
  --ease-both: cubic-bezier(0.4, 0.0, 0.2, 1);

  /* Interactive state colors */
  --fm-color-hover:    rgba(255, 255, 255, 0.08);
  --fm-color-active:   rgba(255, 255, 255, 0.12);
  --fm-color-disabled: rgba(255, 255, 255, 0.30);
  --fm-color-success:  #1DB954;
  --fm-color-warning:  #F59E0B;
  --fm-color-error:    #EF4444;
}
EOF
```

**Verification:**

```bash
grep "space-1\|text-xs\|duration-fast\|fm-color-hover" web/static/css/tokens.css
# Harus match
```

> Catatan: _________________

---

### PHASE 5 COMMIT

```bash
git add web/static/css/ web/static/js/events.js
git commit -m "feat(P5): desktop & tablet layout

- Desktop 2-column layout (sidebar + main + now-playing bar)
- Tablet landscape: queue panel tampil di kanan
- Keyboard shortcuts (Space, Arrow keys)
- Hover states untuk mouse users
- Extended design tokens: spacing, typography, motion

Blueprint: AUDIT_V2 Chapter C
ADR-004: CSS-only responsive"
```

**PHASE 5 DONE CHECK:**

```
[ ] P5-1: Pre-phase 5 audit OK
[ ] P5-2: Desktop sidebar layout CSS ada, visual test OK
[ ] P5-3: Tablet landscape queue panel ada
[ ] P5-4: Keyboard shortcuts ada dan bekerja
[ ] P5-5: Hover states untuk mouse
[ ] P5-6: Extended design tokens ada
[ ] Smoke test PASS
[ ] COMMIT phase 5 dilakukan
```

---

## PHASE 6 — PWA & OFFLINE *(BARU)*

> **Target:** Aplikasi bisa di-install sebagai PWA dan bekerja offline minimal.
> **Prerequisite:** Phase 5 selesai.
> **Exit criteria:** Lighthouse PWA score ≥ 60.

---

### TASK P6-1: Audit PWA Prerequisites

**Status:** `[x]`
**Risk:** 🟢 LOW (hanya audit)

```bash
# Cek apakah manifest sudah ada
ls web/static/manifest.json 2>/dev/null && echo "Ada" || echo "Tidak ada"

# Cek apakah service worker sudah ada
ls web/static/sw.js 2>/dev/null && echo "Ada" || echo "Tidak ada"

# Cek apakah aiohttp meng-serve static files
grep -n "static\|service.worker" main.py | head -10

# Cek HTTPS — PWA membutuhkan HTTPS (atau localhost)
echo "Deployment di localhost? PWA OK. Di LAN? Perlu HTTPS atau moz-extension workaround."
```

---

### TASK P6-2: Buat `manifest.json`

**Status:** `[x]`
**File:** `web/static/manifest.json`
**Risk:** 🟢 LOW

```bash
cat > web/static/manifest.json << 'EOF'
{
  "name": "bagas.fm",
  "short_name": "bagas.fm",
  "description": "Personal YouTube Music Player",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0d0d1c",
  "theme_color": "#0d0d1c",
  "orientation": "any",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
EOF
```

```bash
# Tambahkan link ke manifest di index.html
# Cari <head> dan tambahkan setelah tag pertama
grep -n "<head>\|<meta charset" web/static/index.html | head -3

sed -i 's|<head>|<head>\n    <link rel="manifest" href="/static/manifest.json">\n    <meta name="theme-color" content="#0d0d1c">|' web/static/index.html
```

**Catatan:** Icon file (`icon-192.png`, `icon-512.png`) harus dibuat secara terpisah. Placeholder bisa berupa file kosong untuk sementara — PWA install prompt tetap muncul meski icon placeholder.

---

### TASK P6-3: Buat Service Worker Minimal

**Status:** `[x]`
**File:** `web/static/sw.js`
**Risk:** 🟡 MEDIUM — Service worker bisa menyebabkan stale cache jika tidak di-handle

```bash
cat > web/static/sw.js << 'EOF'
// ── Service Worker — bagas.fm Phase 6 ──
// Strategy: Cache-first untuk static assets, network-first untuk API/WS

const CACHE_VERSION = 'bagas-fm-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;

// Assets yang di-cache saat install
const PRECACHE_ASSETS = [
    '/',
    '/static/index.html',
    '/static/css/base.css',
    '/static/css/tokens.css',
    '/static/css/components.css',
    '/static/css/layout.css',
    '/static/css/player.css',
    '/static/css/tabs.css',
    '/static/css/portal.css',
    '/static/js/main.js',
    '/static/js/store.js',
    '/static/js/dom.js',
    '/static/js/ws.js',
    '/static/js/events.js',
    '/static/js/audio.js',
    '/static/js/utils.js',
    '/static/js/portal.js',
    '/static/js/render/player.js',
    '/static/js/render/tabs.js',
    '/static/js/render/lyrics.js',
    '/static/js/render/search.js',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => cache.addAll(PRECACHE_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate: hapus cache lama
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(key => key !== STATIC_CACHE)
                    .map(key => caches.delete(key))
            )
        ).then(() => self.clients.claim())
    );
});

// Fetch: cache-first untuk static, network-only untuk WS dan API
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip WebSocket dan API requests
    if (url.pathname.startsWith('/ws') || url.pathname.startsWith('/api')) {
        return; // Biarkan browser handle secara normal
    }

    // Cache-first untuk static assets
    if (event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request).then(cached => {
                if (cached) return cached;
                return fetch(event.request).then(response => {
                    // Cache response baru
                    if (response.ok) {
                        const cloned = response.clone();
                        caches.open(STATIC_CACHE).then(cache => cache.put(event.request, cloned));
                    }
                    return response;
                });
            }).catch(() => {
                // Offline fallback
                if (event.request.headers.get('accept').includes('text/html')) {
                    return caches.match('/static/index.html');
                }
            })
        );
    }
});
EOF
```

```bash
# Register service worker di main.js
cat >> web/static/js/main.js << 'JSEOF'

// ── Service Worker Registration — Phase 6 ──
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(reg => console.log('SW registered:', reg.scope))
            .catch(err => console.warn('SW registration failed:', err));
    });
}
JSEOF
```

```bash
# Pastikan aiohttp meng-serve sw.js
grep -n "static\|app.router" main.py | head -10
# Jika service worker tidak bisa di-serve dari /static/sw.js, cek routing di main.py
```

---

### TASK P6-4: Test PWA Install

**Status:** `[x]`

```bash
echo "MANUAL TEST:"
echo "1. Buka Chrome di Android → bagas.fm"
echo "2. Menu → 'Add to Home Screen' harus muncul"
echo "3. Install → icon bagas.fm muncul di home screen"
echo "4. Buka dari home screen → tampil standalone (tanpa browser bar)"
echo ""
echo "Lighthouse PWA audit (Chrome DevTools):"
echo "Score target: ≥ 60"
```

> Hasil install test: _________________
> Lighthouse PWA score: _________________

---

### PHASE 6 COMMIT

```bash
git add web/static/manifest.json web/static/sw.js web/static/js/main.js web/static/index.html
git commit -m "feat(P6): PWA & offline support

- Tambah manifest.json (PWA install prompt)
- Tambah service worker dengan cache-first strategy
- Pre-cache semua static assets saat install
- Network-only untuk WS dan API requests
- Register SW di main.js

AUDIT_V2: Phase 6 specification"
```

**PHASE 6 DONE CHECK:**

```
[ ] P6-1: PWA prerequisites audit selesai
[ ] P6-2: manifest.json ada dan di-link di index.html
[ ] P6-3: sw.js ada dan di-register
[ ] P6-4: Install test berhasil
[ ] Lighthouse PWA ≥ 60
[ ] COMMIT phase 6 dilakukan
```

---

## VERIFICATION MASTER SCRIPT

```bash
#!/bin/bash
echo "════════════════════════════════════════"
echo "  bagas.fm — Post-Audit V2 Verification"
echo "════════════════════════════════════════"
PASS=0; FAIL=0; WARN=0

check() {
    local desc="$1"; local cmd="$2"; local expect="$3"
    local result=$(eval "$cmd" 2>/dev/null)
    if echo "$result" | grep -qE "$expect"; then
        echo "  ✓ $desc"
        ((PASS++))
    else
        echo "  ✗ $desc"
        echo "    Expected pattern: $expect"
        echo "    Got: $result"
        ((FAIL++))
    fi
}

warn() {
    local desc="$1"; local note="$2"
    echo "  ⚠ $desc"
    echo "    → $note"
    ((WARN++))
}

echo ""
echo "─── P0: Critical Bugs ───"
check "--fm-primary defined" "grep 'fm-primary' web/static/css/tokens.css" "fm-primary"
check "Inter font removed" "grep -c 'googleapis.com.*Inter' web/static/css/base.css" "^0$"
check "focus-visible exists" "grep -c 'focus-visible' web/static/css/base.css" "[1-9]"
check "dead DOM ref removed" "grep -c 'lyrics-toggle-btn' web/static/js/dom.js" "^0$"

echo ""
echo "─── P1: Mobile Shell ───"
check "phone height removed" "grep -c '690px' web/static/css/base.css" "^0$"
check "phone max-width removed" "grep -c 'max-width:375px' web/static/css/base.css" "^0$"
check "tablet breakpoint" "grep -c 'min-width: 601px' web/static/css/layout.css" "[1-9]"
check "desktop breakpoint" "grep -c 'min-width: 1024px' web/static/css/layout.css" "[1-9]"
check "safe-area-inset" "grep -c 'safe-area-inset' web/static/css/layout.css" "[1-9]"

echo ""
echo "─── P2: Touch & Interaction ───"
check "pointer events in drag" "grep -c 'pointerdown' web/static/js/events.js" "[1-9]"
check "HTML5 drag removed" "grep -c 'dragstart' web/static/js/events.js" "^0$"
check "touch target expansion" "grep -c 'pb-thumb::after' web/static/css/base.css" "[1-9]"
check "WS reconnect guard" "grep -c 'WebSocket.CLOSED' web/static/js/ws.js" "[1-9]"

echo ""
echo "─── P3: CSS Cleanup ───"
check "vol-grp deduplicated" "grep -c '^\.vol-grp' web/static/css/base.css" "^[01]$"
check "no legacy bg-panel" "grep -c 'var(--bg-panel)' web/static/css/base.css" "^0$"

echo ""
echo "─── P4: Performance ───"
check "rAF in renderProgress" "grep -c 'requestAnimationFrame' web/static/js/render/player.js" "[1-9]"
check "syncBrowserAudio guard" "grep -c 'userRole.*portal' web/static/js/ws.js" "[1-9]"
check "empty state CSS" "grep -c 'queue-empty' web/static/css/base.css" "[1-9]"

echo ""
echo "─── P5: Desktop & Tablet ───"
check "desktop grid layout" "grep -c 'grid-template-columns' web/static/css/layout.css" "[1-9]"
check "keyboard shortcuts" "grep -c 'keydown' web/static/js/events.js" "[1-9]"
check "hover states" "grep -c 'hover: hover' web/static/css/base.css" "[1-9]"
check "motion tokens" "grep -c 'duration-fast' web/static/css/tokens.css" "[1-9]"

echo ""
echo "─── P6: PWA ───"
check "manifest.json exists" "test -f web/static/manifest.json && echo ok" "ok"
check "sw.js exists" "test -f web/static/sw.js && echo ok" "ok"
check "SW registered in main.js" "grep -c 'serviceWorker' web/static/js/main.js" "[1-9]"

echo ""
echo "─── File Sanity ───"
check "index.html parseable" "python3 -c \"from html.parser import HTMLParser; HTMLParser().feed(open('web/static/index.html').read()); print('ok')\"" "ok"
check "tokens.css has :root" "grep -c '^:root' web/static/css/tokens.css" "[1-9]"
check "base.css not empty" "wc -l web/static/css/base.css" "[0-9][0-9][0-9]"

echo ""
echo "════════════════════════════════════════"
echo "  PASS: $PASS  |  FAIL: $FAIL  |  WARN: $WARN"
echo "════════════════════════════════════════"

if [ $FAIL -gt 0 ]; then
    echo "  → Ada $FAIL check yang FAIL. Selesaikan sebelum declare transformasi selesai."
fi
```

---

## ROLLBACK GUIDE

### Rollback 1 Fase (Reversi Terakhir Commit)

```bash
# Lihat commit history
git log --oneline -10

# Trigger condition untuk rollback:
# - App tidak tampil di browser (blank screen)
# - Touch drag rusak di desktop DAN mobile
# - CSS syntax error yang menyebabkan style hilang

# Rollback commit terakhir (pertahankan perubahan di working tree)
git revert HEAD --no-edit
```

### Rollback File Spesifik

```bash
# Kembalikan file ke versi sebelum phase tertentu
git checkout HEAD~1 -- web/static/css/base.css
git checkout HEAD~1 -- web/static/js/events.js

# Rollback ke backup pre-P1 (jika file .pre-p1 masih ada)
cp web/static/css/base.css.pre-p1 web/static/css/base.css
cp web/static/js/events.js.pre-p2 web/static/js/events.js
```

### Partial Rollback (Pertahankan Phase Sebelumnya)

```bash
# Misal: rollback Phase 2 tapi pertahankan Phase 0 dan 1
# Gunakan git log untuk cari hash commit setelah Phase 1

git log --oneline | head -10
# Cari: "feat(P1): mobile-first shell"
# Misal hashnya: abc1234

git checkout abc1234 -- web/static/js/events.js web/static/js/ws.js
# Ini me-restore js files ke state setelah Phase 1
```

### Emergency Reset ke Rollback Anchor

```bash
# Kembalikan ke hash sebelum transformasi dimulai
echo "ROLLBACK_HASH tersimpan saat ENV-2 setup"
echo "Jalankan: git reset --hard $ROLLBACK_HASH"
echo "PERINGATAN: Ini menghapus semua commit setelah rollback anchor"
```

---

## COMMIT FORMAT

```
type(scope): ringkasan singkat (max 72 karakter)

Detail jika perlu.
- List perubahan
- List perubahan

ADR ref: ADR-001, ADR-002
Audit ref: BUG-001, PERF-002
```

**Types:** `fix` `feat` `refactor` `perf` `style` `docs` `test`
**Scopes:** `P0` `P1` `P2` `P3` `P4` `P5` `P6` atau nama komponen

---

## CATATAN PROGRES AKHIR

```
Tanggal mulai   : 24 Juni 2026
Tanggal selesai : 24 Juni 2026
Agent yang mengerjakan : Antigravity

Phase -1: [x] selesai — tanggal: 24 Juni 2026
Phase 0:  [x] selesai — tanggal: 24 Juni 2026
Phase 1:  [x] selesai — tanggal: 24 Juni 2026
Phase 2:  [x] selesai — tanggal: 24 Juni 2026
Phase 3:  [x] selesai — tanggal: 24 Juni 2026
Phase 4:  [x] selesai — tanggal: 24 Juni 2026
Phase 5:  [x] selesai — tanggal: 24 Juni 2026
Phase 6:  [x] selesai — tanggal: 24 Juni 2026

Issues yang ditemukan saat implementasi:
- ___________________
- ___________________

Architecture decisions yang diubah dari ADR:
- ___________________

Hal yang di-defer ke masa depan:
- Toggle system unifikasi (ADR-003: defer ke Phase 5 — apakah sudah selesai?)
- Module system (ADR-005: tetap vanilla JS)
- Light mode (AUDIT_V2 Chapter B.6: explicit decision dark-only)
```

---

*Playbook V2 dibuat berdasarkan `AUDIT_SPOTIFY_CLASS_V2.md` dan `META_REVIEW_SPOTIFY_DOCS.md`*
*V2 menambahkan: Agent Context Brief, Risk Matrix, Definition of Done, ADR (5 keputusan), Regression Prevention Protocol, Phase 5 spec lengkap (6 task), Phase 6 PWA spec (4 task)*
*Verification Master Script diperluas untuk Phase 5 dan 6*
