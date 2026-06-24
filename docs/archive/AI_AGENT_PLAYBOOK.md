# AI_AGENT_PLAYBOOK.md
> **Panduan untuk AI Agent yang menjalankan refactor bagas.fm**  
> Semua instruksi bersifat deterministik dan dapat diverifikasi via bash.  
> Untuk konteks arsitektur & struktur target → lihat `REFACTOR_PLAN_FINAL.md`.

---

## Daftar Isi
1. [Setup & Prerequisite](#1-setup--prerequisite)
2. [Fase 0 — Critical Fixes & Safe Delete](#2-fase-0--critical-fixes--safe-delete)
3. [Fase 1 — CSS Split](#3-fase-1--css-split)
4. [Fase 2 — JS Split](#4-fase-2--js-split)
5. [Fase 3 — Backend Split](#5-fase-3--backend-split)
6. [Fase 4 — Rename & Reorganize](#6-fase-4--rename--reorganize)
7. [Fase 5 — Tests Reorganize](#7-fase-5--tests-reorganize)
8. [Fase 6 — Documentation](#8-fase-6--documentation)
9. [Verification Script](#9-verification-script)
10. [Rollback Plan](#10-rollback-plan)
11. [Error Handling & Recovery](#11-error-handling--recovery)
12. [Success Criteria](#12-success-criteria)

---

## 1. Setup & Prerequisite

### 1.1 Environment Check

```bash
# Verifikasi tools tersedia
python3 --version          # Harus 3.9+
git --version              # Harus ada
python3 -m pytest --version  # Harus ada

# Jika ada yang missing → STOP, install dulu.
```

### 1.2 Repository State

```bash
# Harus di clean working tree
git status --porcelain
# Output harus KOSONG. Jika ada file → stash atau commit dulu, baru mulai.
```

### 1.3 Baseline Test

```bash
# Semua test harus PASS sebelum refactor dimulai
pytest tests/ -v --tb=short 2>&1 | tail -5
# Harus: X passed, 0 failed

# Simpan baseline metrics
pytest tests/ --co -q 2>/dev/null | wc -l > /tmp/baseline_test_count.txt
wc -l main.py > /tmp/baseline_main_py.txt
echo "Baseline ready."
```

---

## 2. Fase 0 — Critical Fixes & Safe Delete

### 2.0 Pre-Check

```bash
echo "=== FASE 0 PRE-CHECK ==="

# Pastikan :root belum ada (idempotency guard)
if grep -q "^:root {" web/static/style.css; then
  echo "SKIP: :root block sudah ada. Fase 0A sudah done."
else
  echo "OK: :root belum ada, lanjut Fase 0A."
fi

# Pastikan tui/ belum dihapus
if [ ! -d "tui" ]; then
  echo "SKIP: tui/ sudah tidak ada. Fase 0B sudah done."
else
  echo "OK: tui/ masih ada, lanjut Fase 0B."
fi
```

---

### 2A. Fix CSS — Tambahkan :root Block

```bash
# 1. Buat token block di file terpisah dulu
cat > /tmp/root_tokens.css << 'TOKEN_EOF'
/* ============================================================
   bagas.fm Design Tokens — SINGLE SOURCE OF TRUTH
   Dibuat dari: bagas_fm_ui_mockup.html + 5 PNG mockup
   JANGAN EDIT nilai di sini tanpa update mockup juga.
   ============================================================ */
:root {
  /* Background */
  --fm-bg-deep:     #0d0d1c;
  --fm-bg-card:     #141426;
  --fm-bg-elevated: #1e1e38;
  --fm-bg-overlay:  #0f0f20;

  /* Accent */
  --fm-accent:      #e040fb;
  --fm-accent-dim:  #c020d0;
  --fm-accent-bg:   #2a1540;
  --fm-cyan:        #00e5ff;
  --fm-teal:        #00e5b0;
  --fm-green:       #00c870;
  --fm-warn:        #f0b429;
  --fm-err:         #ef4444;
  --fm-blue:        #60a5fa;

  /* Text */
  --fm-text-1:      #f0f0ff;
  --fm-text-2:      #e8e8f5;
  --fm-text-3:      #9a9abc;
  --fm-text-4:      #6a6a8c;
  --fm-text-5:      #5a5a7a;

  /* Border */
  --fm-border:      #1e1e32;
  --fm-border-2:    #2e2e48;

  /* Typography */
  --fm-font:        -apple-system, system-ui, sans-serif;

  /* Radius */
  --fm-radius-xs:   4px;
  --fm-radius-sm:   8px;
  --fm-radius-md:   12px;
  --fm-radius-lg:   16px;
  --fm-radius-xl:   20px;
  --fm-radius-pill: 20px;
  --fm-radius-app:  36px;

  /* Shadow */
  --fm-shadow-sm:   0 2px 8px rgba(0,0,0,0.4);
  --fm-shadow-md:   0 4px 16px rgba(0,0,0,0.5);

  /* Transition */
  --fm-transition-fast:   0.15s ease;
  --fm-transition-normal: 0.25s ease;

  /* ============================================================
     LEGACY ALIASES — bridge untuk style.css yang masih pakai nama lama.
     Hapus blok ini setelah Fase 1 CSS split selesai.
     ============================================================ */
  --accent-fire:       #e040fb;
  --bg-panel:          #141426;
  --bg-elevated:       #1e1e38;
  --bg-void:           #0d0d1c;
  --bg-glass:          rgba(20,20,38,0.92);
  --accent-gold:       #f0b429;
  --accent-blue:       #60a5fa;
  --status-err:        #ef4444;
  --text-primary:      #f0f0ff;
  --text-muted:        #6a6a8c;
  --text-dim:          #5a5a7a;
  --border:            #1e1e32;
  --font-family:       -apple-system, system-ui, sans-serif;
  --radius-sm:         8px;
  --radius-md:         12px;
  --radius-lg:         16px;
  --radius-xl:         20px;
  --radius-full:       9999px;
  --shadow-md:         0 2px 8px rgba(0,0,0,0.4);
  --shadow-lg:         0 4px 16px rgba(0,0,0,0.5);
  --transition-fast:   0.15s ease;
  --transition-normal: 0.25s ease;
}

TOKEN_EOF

# 2. Prepend ke style.css
cat /tmp/root_tokens.css web/static/style.css > /tmp/style_merged.css
mv /tmp/style_merged.css web/static/style.css

# 3. Verifikasi :root ada di baris 1
FIRST_ROOT=$(grep -n "^:root {" web/static/style.css | head -1 | cut -d: -f1)
if [ "$FIRST_ROOT" -lt 5 ] 2>/dev/null; then
  echo "✓ :root block ada di baris $FIRST_ROOT"
else
  echo "✗ ERROR: :root block tidak ada di awal file. Rollback."
  git checkout -- web/static/style.css
  exit 1
fi

# 4. Verifikasi token terpakai (ada var() yang refer ke alias lama)
ALIAS_COUNT=$(grep -c "var(--accent-fire)" web/static/style.css)
if [ "$ALIAS_COUNT" -gt 0 ]; then
  echo "✓ Found $ALIAS_COUNT uses of legacy alias — token bridge aktif"
else
  echo "✗ ERROR: Tidak ada uses of token aliases"
  exit 1
fi

echo "=== Fase 0A DONE ==="
```

**Visual check (minta human):**
```
Buka http://localhost:8765
✓ Background hitam #0d0d1c (bukan putih/default)
✓ Play button ungu #e040fb
✓ Progress bar fill ungu
✓ Nav tab bar visible

Jika gagal → git checkout -- web/static/style.css → selesaikan dulu.
```

---

### 2B. Safe Delete tui/

```bash
echo "=== FASE 0B: Safe Delete tui/ ==="

# 1. Verifikasi tidak ada import tui dari luar tui/
STRAY_TUI=$(grep -r "from tui\|import tui" --include="*.py" --exclude-dir=tui . 2>/dev/null)
if [ -n "$STRAY_TUI" ]; then
  echo "ERROR: Ada import tui dari luar:"
  echo "$STRAY_TUI"
  echo "Batalkan — tui/ bukan dead code."
  exit 1
fi
echo "✓ Tidak ada import tui dari luar tui/"

# 2. Verifikasi textual tidak di requirements
if grep -qi "textual" requirements.txt requirements-dev.txt 2>/dev/null; then
  echo "ERROR: 'textual' ada di requirements. Review dulu."
  exit 1
fi
echo "✓ textual tidak di requirements"

# 3. Catat jumlah file sebelum delete (audit trail)
TUI_FILES=$(find tui -type f | wc -l)
echo "Akan menghapus $TUI_FILES files dari tui/"

# 4. Hapus
rm -rf tui/

# 5. Konfirmasi
[ -d "tui" ] && echo "ERROR: tui/ masih ada!" && exit 1
echo "✓ tui/ dihapus"

# 6. Pytest harus tetap pass
pytest tests/ -q 2>&1 | tail -3
echo "=== Fase 0B DONE ==="
```

---

### 2C. Cleanup Minor

```bash
echo "=== FASE 0C: Cleanup ==="

# 1. Hapus file sampah
rm -f web/static/switchTab.txt
echo "✓ switchTab.txt dihapus"

# 2. Fix typo nama folder
if [ -d "docs/archive/audit_arsitktur" ]; then
  mv docs/archive/audit_arsitktur docs/archive/audit_arsitektur
  echo "✓ Typo folder diperbaiki"
fi

# 3. Lowercase semua .PNG
find docs -name "*.PNG" | while read f; do
  target="${f%.PNG}.png"
  mv "$f" "$target"
  echo "✓ Renamed $(basename $f) → $(basename $target)"
done

# 4. Update README.md — hapus mention TUI
if grep -q "TUI Interaktif" README.md; then
  # Hapus baris yang mengandung TUI Interaktif
  sed -i '/TUI Interaktif/d' README.md
  echo "✓ README.md diupdate — baris TUI dihapus"
  
  # Verifikasi
  if grep -qi "tui" README.md; then
    echo "WARN: Masih ada mention tui di README.md — review manual"
    grep -n -i "tui" README.md
  else
    echo "✓ README.md bersih dari mention TUI"
  fi
fi

echo "=== Fase 0C DONE ==="
```

---

### 2D. Commit Fase 0

```bash
# Final pytest sebelum commit
pytest tests/ -q 2>&1 | tail -3

git add -A
git commit -m "fix(css): add :root design tokens; chore: remove dead tui/ code

- Add :root block dengan --fm-* tokens + legacy aliases sebagai bridge
- Delete tui/ folder (dead code: tidak diimport, textual tidak di requirements)
- Delete web/static/switchTab.txt (file sampah)
- Fix typo docs/archive/audit_arsitktur → audit_arsitektur
- Lowercase docs/*.PNG → *.png
- Update README.md (remove TUI section)

All tests pass."

git log --oneline -1
echo "=== Fase 0 COMPLETE ==="
```

---

## 3. Fase 1 — CSS Split

> **Konteks:** `web/static/style.css` (992 baris) dipecah jadi 7 file berdasarkan anchor comments yang sudah terverifikasi dari kode aktual.

### 3.0 Pre-Check

```bash
echo "=== FASE 1 PRE-CHECK ==="

# Pastikan :root sudah ada (Fase 0 done)
grep -q "^:root {" web/static/style.css || { echo "ERROR: Fase 0 belum done"; exit 1; }

# Catat line count style.css sebagai sanity check
echo "style.css total lines: $(wc -l < web/static/style.css)"

# Pastikan folder css belum ada (idempotency guard)
[ -d "web/static/css" ] && echo "WARN: web/static/css/ sudah ada — akan overwrite"

# Verifikasi anchor-anchor kritis ada di file
for anchor in "══════════════════════════════════════" "portal-screen" "Tab Discover" "Radio Tab"; do
  if grep -q "$anchor" web/static/style.css; then
    echo "✓ Anchor ditemukan: '$anchor'"
  else
    echo "✗ WARN: Anchor tidak ditemukan: '$anchor'"
  fi
done
```

---

### 3.1 Buat Folder & Ekstrak tokens.css

```bash
mkdir -p web/static/css

# tokens.css = hanya :root block
# :root ada mulai baris 1 (ditambahkan Fase 0), cari baris closing '}'
ROOT_START=1
ROOT_END=$(awk '/^:root \{/{f=1} f && /^\}$/{print NR; exit}' web/static/style.css)
echo "Extracting :root (baris $ROOT_START–$ROOT_END) → tokens.css"

sed -n "${ROOT_START},${ROOT_END}p" web/static/style.css > web/static/css/tokens.css
echo "✓ tokens.css: $(wc -l < web/static/css/tokens.css) baris"
```

---

### 3.2 Ekstrak base.css

```bash
# base.css = setelah :root block sampai sebelum ══ Player Bar ══ (baris 175 anchor)
BASE_START=$((ROOT_END + 1))
BASE_END=$(grep -n "══════════════════════════════════════" web/static/style.css | \
           awk -F: '$1 > '"$ROOT_END"' {print $1; exit}')
BASE_END=$((BASE_END - 1))

echo "Extracting base (baris $BASE_START–$BASE_END) → base.css"
sed -n "${BASE_START},${BASE_END}p" web/static/style.css > web/static/css/base.css
echo "✓ base.css: $(wc -l < web/static/css/base.css) baris"
```

---

### 3.3 Ekstrak Section Berdasarkan Anchor

```bash
# Helper: ekstrak antara dua anchor (inklusif anchor pertama, eksklusif anchor kedua)
# Usage: extract_between <source> <anchor_from> <anchor_to_exclusive> <target>
extract_between() {
  local src="$1"
  local from_pattern="$2"
  local to_pattern="$3"
  local target="$4"

  local start_line end_line
  start_line=$(grep -n "$from_pattern" "$src" | head -1 | cut -d: -f1)
  end_line=$(grep -n "$to_pattern" "$src" | awk -F: -v s="$start_line" '$1 > s {print $1-1; exit}')

  if [ -z "$start_line" ]; then
    echo "ERROR: Start anchor tidak ditemukan: '$from_pattern'"
    return 1
  fi
  if [ -z "$end_line" ]; then
    # Gunakan EOF jika tidak ada anchor berikutnya
    end_line=$(wc -l < "$src")
  fi

  sed -n "${start_line},${end_line}p" "$src" > "$target"
  echo "✓ $(basename $target): baris $start_line–$end_line ($(wc -l < $target) baris)"
}

SRC="web/static/style.css"

# layout.css: ══ Player Bar ══ → ══ Controls ══
extract_between "$SRC" \
  "Player Bar" \
  "Controls" \
  "web/static/css/layout.css"

# player.css: ══ Controls ══ → ══ Portal ══
extract_between "$SRC" \
  "Controls" \
  "Portal\|portal-screen" \
  "web/static/css/player.css"

# portal.css: ══ Portal ══ → ══ Player Extras ══
extract_between "$SRC" \
  "portal-screen {" \
  "Player Extras\|Volume Slider" \
  "web/static/css/portal.css"

# components.css: ══ Player Extras ══ → ── Tab Discover ──
extract_between "$SRC" \
  "Volume Slider\|Player Extras" \
  "Tab Discover" \
  "web/static/css/components.css"

# tabs.css: ── Tab Discover ── → EOF
START=$(grep -n "Tab Discover" "$SRC" | head -1 | cut -d: -f1)
END=$(wc -l < "$SRC")
sed -n "${START},${END}p" "$SRC" > web/static/css/tabs.css
echo "✓ tabs.css: baris $START–$END ($(wc -l < web/static/css/tabs.css) baris)"
```

---

### 3.4 Rename Variable Lama → fm-* di Semua CSS File

```bash
# Replace semua CSS variable lama dengan fm-* baru
# Jalankan di semua file CSS baru (KECUALI tokens.css — itu sudah punya keduanya)
CSS_FILES="web/static/css/base.css web/static/css/layout.css web/static/css/player.css web/static/css/portal.css web/static/css/components.css web/static/css/tabs.css"

for f in $CSS_FILES; do
  sed -i \
    -e 's/var(--accent-fire)/var(--fm-accent)/g' \
    -e 's/var(--bg-panel)/var(--fm-bg-card)/g' \
    -e 's/var(--bg-elevated)/var(--fm-bg-elevated)/g' \
    -e 's/var(--bg-void)/var(--fm-bg-deep)/g' \
    -e 's/var(--accent-gold)/var(--fm-warn)/g' \
    -e 's/var(--accent-blue)/var(--fm-blue)/g' \
    -e 's/var(--status-err)/var(--fm-err)/g' \
    -e 's/var(--text-primary)/var(--fm-text-1)/g' \
    -e 's/var(--text-muted)/var(--fm-text-4)/g' \
    -e 's/var(--text-dim)/var(--fm-text-5)/g' \
    -e 's/var(--border)/var(--fm-border)/g' \
    -e 's/var(--font-family)/var(--fm-font)/g' \
    -e 's/var(--radius-sm)/var(--fm-radius-sm)/g' \
    -e 's/var(--radius-md)/var(--fm-radius-md)/g' \
    -e 's/var(--radius-lg)/var(--fm-radius-lg)/g' \
    -e 's/var(--radius-xl)/var(--fm-radius-xl)/g' \
    -e 's/var(--radius-full)/var(--fm-radius-pill)/g' \
    -e 's/var(--shadow-md)/var(--fm-shadow-sm)/g' \
    -e 's/var(--shadow-lg)/var(--fm-shadow-md)/g' \
    -e 's/var(--transition-fast)/var(--fm-transition-fast)/g' \
    -e 's/var(--transition-normal)/var(--fm-transition-normal)/g' \
    "$f"
  echo "✓ Replaced vars in $(basename $f)"
done

# Verifikasi: tidak boleh ada legacy var() tersisa di file non-tokens
if grep -h "var(--accent-fire\|var(--bg-panel\|var(--bg-elevated\|var(--text-primary)" $CSS_FILES 2>/dev/null; then
  echo "WARN: Masih ada legacy vars — perlu manual review"
else
  echo "✓ Semua legacy vars sudah di-replace"
fi
```

---

### 3.5 Update index.html

```bash
# Ganti <link> style.css tunggal dengan 7 links berurutan
# Backup dulu
cp web/static/index.html web/static/index.html.bak

# Temukan baris yang ada style.css
OLD_LINK=$(grep -n "style.css" web/static/index.html | head -1)
echo "Link lama: $OLD_LINK"

# Replace dengan 7 links (gunakan Python untuk safely replace)
python3 << 'PYEOF'
with open("web/static/index.html", "r") as f:
    content = f.read()

old = '<link rel="stylesheet" href="/static/style.css">'
# Coba variasi lain jika tidak match persis
if old not in content:
    old = '<link href="/static/style.css" rel="stylesheet">'
if old not in content:
    # Fallback: cari pola style.css
    import re
    match = re.search(r'<link[^>]*style\.css[^>]*>', content)
    if match:
        old = match.group(0)
    else:
        print("ERROR: Link style.css tidak ditemukan di index.html")
        exit(1)

new = """<link rel="stylesheet" href="/static/css/tokens.css">
    <link rel="stylesheet" href="/static/css/base.css">
    <link rel="stylesheet" href="/static/css/layout.css">
    <link rel="stylesheet" href="/static/css/player.css">
    <link rel="stylesheet" href="/static/css/tabs.css">
    <link rel="stylesheet" href="/static/css/components.css">
    <link rel="stylesheet" href="/static/css/portal.css">"""

content = content.replace(old, new, 1)
with open("web/static/index.html", "w") as f:
    f.write(content)

print("✓ index.html updated dengan 7 CSS links")
PYEOF

# Verifikasi 7 link ada
CSS_LINK_COUNT=$(grep -c "css/" web/static/index.html)
echo "CSS links di index.html: $CSS_LINK_COUNT (expected: 7)"
[ "$CSS_LINK_COUNT" -eq 7 ] && echo "✓ OK" || echo "✗ CHECK MANUAL"
```

---

### 3.6 Verify & Commit Fase 1

```bash
# Verifikasi semua 7 file ada dan tidak kosong
for f in tokens.css base.css layout.css player.css tabs.css components.css portal.css; do
  if [ -s "web/static/css/$f" ]; then
    echo "✓ $f ($(wc -l < web/static/css/$f) baris)"
  else
    echo "✗ ERROR: $f kosong atau tidak ada"
  fi
done

# Verifikasi tidak ada hex hardcode di luar tokens.css
HARDCODED=$(grep -h "#[0-9a-fA-F]\{3,6\}" \
  web/static/css/base.css \
  web/static/css/layout.css \
  web/static/css/player.css \
  web/static/css/components.css \
  web/static/css/tabs.css \
  web/static/css/portal.css 2>/dev/null | wc -l)
echo "Hardcoded hex colors di luar tokens.css: $HARDCODED"
[ "$HARDCODED" -eq 0 ] && echo "✓ Bersih" || echo "WARN: Ada hex hardcode — review manual"

# Test
pytest tests/ -q 2>&1 | tail -3

# Hapus style.css lama dan backup
rm -f web/static/style.css web/static/index.html.bak

# Commit
git add web/static/css/ web/static/index.html web/static/style.css
git commit -m "refactor(css): split style.css into 7 focused files with fm-* tokens

- css/tokens.css: :root design tokens (fm-* + legacy aliases untuk bridge)
- css/base.css: reset, typography, global
- css/layout.css: #app, #player-bar, #content-area, nav structure
- css/player.css: seek bar, controls, EQ, badges, log toast
- css/portal.css: admin login modal
- css/components.css: volume, queue drag, lyrics, settings sheet
- css/tabs.css: discover, radio, seed chips, animations
- Rename all var(--old-*) → var(--fm-*) in extracted files
- Update index.html dengan 7 link tags berurutan

All tests pass."

echo "=== Fase 1 COMPLETE ==="
```

---

## 4. Fase 2 — JS Split

> **Konteks:** `web/static/app.js` (1624 baris) dipecah jadi 14 modul. Violation kritis yang WAJIB diperbaiki saat ekstraksi: `addEventListener()` di dalam render functions (baris 378, 410, 438, 466, 600) dan `wsSend()` di dalam render functions.

### 4.0 Pre-Check

```bash
echo "=== FASE 2 PRE-CHECK ==="

# Catat violations yang harus dipindahkan
echo "addEventListener calls di render area:"
grep -n "addEventListener" web/static/app.js | head -20

echo ""
echo "wsSend calls yang mungkin ada di render:"
grep -n "wsSend" web/static/app.js | head -30

echo ""
echo "Total lines app.js: $(wc -l < web/static/app.js)"
```

---

### 4.1 Buat Struktur Folder JS

```bash
mkdir -p web/static/js/render
echo "✓ Folder js/ dan js/render/ dibuat"
```

---

### 4.2 Pola Ekstraksi JS

> **Prinsip:** Setiap file diisi manual oleh agent — ambil fungsi-fungsi dari app.js yang relevan. File tetap di app.js sampai semua ekstraksi selesai; hapus app.js hanya di akhir setelah semua verified.

**Urutan ekstraksi (dari yang paling sedikit dependencies):**

```
1. config.js      ← constants (SEED_ARTISTS, TAB_IDS, dsb) — zero deps
2. store.js       ← const store = {}, updateStore() — zero deps
3. dom.js         ← const dom = { getElementById results } — zero deps
4. utils.js       ← formatTime(), escapeHtml(), dll — zero deps
5. render/player.js ← renderPlayerBar(), renderProgress(), renderPlayBtn() — needs store, dom
6. render/tabs.js   ← renderNowPlaying(), renderQueue(), renderRadio(), renderDiscoverTab()
7. render/lyrics.js ← renderLyrics(), updateOffsetDisplay()
8. render/search.js ← renderSearchResults(), showActionModal(), hideActionModal()
9. eq.js          ← tickEQ(), startEQ(), canvas logic
10. audio.js      ← unlockBrowserAudio(), syncBrowserAudio(), getOrInitAudio()
11. portal.js     ← logout(), portal logic, session check
12. ws.js         ← wsConnect(), wsSend(), handleServerMessage()
13. events.js     ← SEMUA addEventListener() + handler functions
14. main.js       ← switchTab(), init sequence
```

---

### 4.3 Rule Wajib Saat Ekstraksi

**Ketika mengekstrak `render/*.js`:**

```javascript
// ✅ BENAR — render function hanya baca store, return string atau update DOM
function renderPlayerBar() {
  const { isPlaying, currentTrack } = store;
  dom.playBtn.classList.toggle("playing", isPlaying);
  dom.trackTitle.textContent = currentTrack?.title || "—";
}

// ❌ SALAH — wsSend() dari dalam render
function renderRadioTab() {
  dom.radioContainer.innerHTML = buildRadioHTML();
  // INI HARUS PINDAH KE events.js:
  dom.randomizeBtn.addEventListener("click", () => wsSend("radio_randomize"));
}

// ✅ BENAR setelah dipindah ke events.js:
// events.js:
dom.randomizeBtn.addEventListener("click", () => wsSend("radio_randomize"));

// render/tabs.js: (bersih dari listener)
function renderRadioTab() {
  dom.radioContainer.innerHTML = buildRadioHTML();
}
```

**Verifikasi setelah setiap file render dibuat:**
```bash
# Harus kosong — tidak boleh ada di dalam render/
grep -n "addEventListener\|wsSend" web/static/js/render/*.js
```

---

### 4.4 Template main.js

```javascript
// web/static/js/main.js — SELALU load terakhir
(function () {
  "use strict";

  function init() {
    initDOM();       // dom.js
    initPortal();    // portal.js — cek session, tampilkan portal jika perlu
    initAudio();     // audio.js — unlock browser audio context
    initEQ();        // eq.js — setup canvas
    initEvents();    // events.js — semua addEventListener
    wsConnect();     // ws.js — mulai WebSocket connection
  }

  document.addEventListener("DOMContentLoaded", init);
})();
```

---

### 4.5 Update index.html & Commit Fase 2

```bash
# Update index.html: ganti <script src="app.js"> dengan 14 scripts
python3 << 'PYEOF'
with open("web/static/index.html", "r") as f:
    content = f.read()

import re
old_match = re.search(r'<script[^>]*app\.js[^>]*></script>', content)
if not old_match:
    print("ERROR: script app.js tidak ditemukan di index.html")
    exit(1)

new_scripts = """<script src="/static/js/config.js"></script>
    <script src="/static/js/store.js"></script>
    <script src="/static/js/dom.js"></script>
    <script src="/static/js/utils.js"></script>
    <script src="/static/js/render/player.js"></script>
    <script src="/static/js/render/tabs.js"></script>
    <script src="/static/js/render/lyrics.js"></script>
    <script src="/static/js/render/search.js"></script>
    <script src="/static/js/eq.js"></script>
    <script src="/static/js/audio.js"></script>
    <script src="/static/js/portal.js"></script>
    <script src="/static/js/ws.js"></script>
    <script src="/static/js/events.js"></script>
    <script src="/static/js/main.js"></script>"""

content = content.replace(old_match.group(0), new_scripts)
with open("web/static/index.html", "w") as f:
    f.write(content)
print("✓ index.html updated dengan 14 script tags")
PYEOF

# Verifikasi tidak ada listener atau wsSend di dalam render/
echo "=== Violation check di render/ ==="
VIOLATIONS=$(grep -rn "addEventListener\|wsSend" web/static/js/render/ 2>/dev/null | wc -l)
if [ "$VIOLATIONS" -eq 0 ]; then
  echo "✓ Tidak ada violations di render/"
else
  echo "✗ ERROR: $VIOLATIONS violations di render/ — harus dipindah ke events.js"
  grep -rn "addEventListener\|wsSend" web/static/js/render/
  exit 1
fi

# Test
pytest tests/ -q 2>&1 | tail -3

# Hapus app.js lama
rm -f web/static/app.js

# Commit
git add web/static/js/ web/static/index.html web/static/app.js
git commit -m "refactor(js): split app.js (1624 baris) into 14 focused modules

- js/config.js, store.js, dom.js, utils.js
- js/render/player.js, tabs.js, lyrics.js, search.js (pure render only)
- js/eq.js, audio.js, portal.js, ws.js
- js/events.js (all addEventListener consolidated here)
- js/main.js (init sequence, loaded last)
- Fix: remove wsSend() and addEventListener() from render functions

All tests pass."

echo "=== Fase 2 COMPLETE ==="
```

---

## 5. Fase 3 — Backend Split

> **Konteks:** `web/server.py` (700 baris) dipecah ke `server/handlers/`. **Urutan kritis:** extract → update main.py → test → hapus file lama.

### 5.0 Pre-Check

```bash
echo "=== FASE 3 PRE-CHECK ==="
echo "server.py lines: $(wc -l < web/server.py)"

# Identifikasi imports utama di server.py
echo "=== server.py imports ==="
grep "^from\|^import" web/server.py

# Identifikasi violations yang harus diperbaiki
echo ""
echo "=== engine/playback_controller.py — cek import violation ==="
grep "^from integrations\|^import integrations" engine/playback_controller.py || echo "(bersih)"
```

---

### 5.1 Buat Struktur server/

```bash
mkdir -p server/handlers
touch server/__init__.py
touch server/handlers/__init__.py
echo "✓ server/ structure created"
```

---

### 5.2 Urutan Ekstraksi

**Ikuti urutan ini karena ada dependency antar file:**

```
1. server/serializers.py   ← extract _track_to_dict(), _state_to_dict(), _dict_to_track()
                              (tidak ada deps ke handler lain — ekstrak PERTAMA)
2. server/middleware.py    ← extract logging_middleware(), rate_limit_middleware()
3. server/handlers/auth.py ← extract login_handler(), logout_handler(), require_auth
4. server/handlers/http.py ← extract serve_index(), serve_static(), health_check()
5. server/handlers/websocket.py ← extract ws_handler(), ConnectionManager
6. server/app.py           ← create_app(), setup_routes(), run_server()
```

**Setelah setiap file diekstrak, verifikasi:**
```bash
python3 -m py_compile server/serializers.py && echo "✓ Syntax OK"
python3 -c "import server.serializers" && echo "✓ Import OK"
```

---

### 5.3 Fix Architecture Violation di engine/

> `engine/playback_controller.py` saat ini import langsung dari `integrations/` (yang akan berubah jadi `plugins/`). Ini melanggar law: engine tidak boleh import langsung dari plugins.

```python
# Tambahkan ke core/ports.py jika belum ada:
from typing import Protocol

class LyricsProvider(Protocol):
    async def fetch(self, title: str, artist: str) -> str: ...

class SponsorBlockProvider(Protocol):
    async def get_segments(self, video_id: str) -> list: ...
```

```python
# engine/playback_controller.py — ganti direct import:
# SEBELUM (violation):
from integrations.sponsorblock import SponsorBlockHandler
from integrations.lyrics import LyricsFetcher

# SESUDAH (via port):
from core.ports import LyricsProvider, SponsorBlockProvider
# (Implementasi di-inject oleh main.py)
```

```python
# main.py — tambahkan injection:
from plugins.lyrics import GeniusLyricsProvider
from plugins.sponsorblock import SponsorBlockHandler
from engine.playback_controller import PlaybackController

lyrics = GeniusLyricsProvider()
sponsorblock = SponsorBlockHandler()
playback = PlaybackController(lyrics_provider=lyrics, sponsorblock=sponsorblock)
```

---

### 5.4 Update main.py & Commit Fase 3

```bash
# 1. Update main.py import SEBELUM hapus web/server.py
# Ganti: from web.server import ... → from server.app import ...
grep -n "web.server\|web import" main.py  # Lihat baris mana

# Edit main.py untuk import dari server.app
# (lakukan manual atau via sed sesuai baris aktual)

# 2. Test dengan file lama masih ada
pytest tests/ -q 2>&1 | tail -3
# Harus PASS

# 3. Baru hapus file lama
rm -f web/server.py web/__init__.py
echo "✓ web/server.py dihapus"

# 4. Test lagi
pytest tests/ -q 2>&1 | tail -3
# Harus tetap PASS

# 5. Commit
git add -A
git commit -m "refactor(server): split server.py into handler modules

- server/app.py: create_app(), setup_routes(), run_server()
- server/handlers/http.py: serve_index(), serve_static(), health_check()
- server/handlers/websocket.py: ws_handler(), ConnectionManager
- server/handlers/auth.py: login_handler(), logout_handler(), require_auth
- server/serializers.py: track_to_dict(), state_to_dict()
- server/middleware.py: logging, rate limiting
- Fix architecture violation: engine/playback_controller no longer
  imports from integrations/ directly — now uses core/ports.py interface
- Injection wired in main.py

All tests pass."

echo "=== Fase 3 COMPLETE ==="
```

---

## 6. Fase 4 — Rename & Reorganize

```bash
echo "=== FASE 4: Rename & Reorganize ==="

# 1. Rename engine files
git mv engine/queue_mode.py engine/queue_manager.py
git mv engine/radio_mode.py engine/radio_engine.py
echo "✓ engine/ files renamed"

# 2. Rename integrations/ → plugins/
git mv integrations plugins
git mv plugins/termux_notification.py plugins/notifications.py
echo "✓ integrations/ → plugins/ renamed"

# 3. Rename widgets/ → scripts/
[ -d "widgets" ] && git mv widgets scripts && echo "✓ widgets/ → scripts/"

# 4. Pindahkan docs
mkdir -p docs/mockups
[ -f "docs/bagas_fm_ui_mockup.html" ] && git mv docs/bagas_fm_ui_mockup.html docs/mockups/
for f in docs/*.png docs/*.PNG; do
  [ -f "$f" ] && git mv "$f" "docs/mockups/$(basename ${f,,})"
done
echo "✓ docs mockups dipindah ke docs/mockups/"

# 5. Update SEMUA import yang terpengaruh
# Cari semua file Python yang masih import dari path lama
FILES_TO_FIX=$(grep -rl \
  "from integrations\|engine\.queue_mode\|engine\.radio_mode\|from web\.server" \
  --include="*.py" . 2>/dev/null)

if [ -n "$FILES_TO_FIX" ]; then
  echo "Files yang perlu update import:"
  echo "$FILES_TO_FIX"
  
  for f in $FILES_TO_FIX; do
    sed -i \
      -e 's/from integrations\./from plugins./g' \
      -e 's/import integrations\./import plugins./g' \
      -e 's/engine\.queue_mode/engine.queue_manager/g' \
      -e 's/from engine\.queue_mode/from engine.queue_manager/g' \
      -e 's/engine\.radio_mode/engine.radio_engine/g' \
      -e 's/from engine\.radio_mode/from engine.radio_engine/g' \
      -e 's/from web\.server/from server.app/g' \
      "$f"
    echo "  ✓ Updated $f"
  done
else
  echo "✓ Tidak ada import lama yang perlu diupdate"
fi

# 6. Verifikasi tidak ada stray import lama
echo "=== Stray import check ==="
if grep -r "from integrations\|engine\.queue_mode\|engine\.radio_mode" \
   --include="*.py" . 2>/dev/null | grep -v ".git"; then
  echo "WARN: Masih ada stray import — review manual"
else
  echo "✓ Tidak ada stray import lama"
fi

# 7. Test
pytest tests/ -q 2>&1 | tail -3

# 8. Commit
git add -A
git commit -m "refactor: rename files and folders for clarity

- engine/queue_mode.py → queue_manager.py
- engine/radio_mode.py → radio_engine.py
- integrations/ → plugins/
- plugins/termux_notification.py → notifications.py
- widgets/ → scripts/
- docs mockup files → docs/mockups/
- Update all affected imports

All tests pass."

echo "=== Fase 4 COMPLETE ==="
```

---

## 7. Fase 5 — Tests Reorganize

```bash
echo "=== FASE 5: Tests Reorganize ==="

mkdir -p tests/unit/{core,engine,cache,server,plugins}
mkdir -p tests/integration
mkdir -p tests/fixtures

# Peta rename — sesuaikan dengan peta di REFACTOR_PLAN_FINAL.md Bagian 5.5
declare -A TEST_MAP=(
  ["tests/test_patch_0_01_appstate_duration.py"]="tests/unit/core/test_app_state.py"
  ["tests/test_patch_0_02_lyrics_session.py"]="tests/unit/cache/test_lyrics_cache.py"
  ["tests/test_patch_0_03_upsert_temp.py"]="tests/unit/cache/test_db_upsert.py"
  ["tests/test_patch_0_04_ttl_mismatch.py"]="tests/unit/cache/test_db_ttl.py"
  ["tests/test_patch_0_09_10_11_server_perf.py"]="tests/unit/server/test_ws_performance.py"
  ["tests/test_patch_1_01_02_safe_create_task.py"]="tests/unit/core/test_task_utils.py"
  ["tests/test_patch_1_03_eventbus_concurrent.py"]="tests/unit/core/test_event_bus_concurrent.py"
  ["tests/test_patch_1_04_queue_remove_lock.py"]="tests/unit/engine/test_queue_locking.py"
  ["tests/test_patch_1_05_lyrics_generation.py"]="tests/unit/plugins/test_lyrics.py"
  ["tests/test_patch_1_06_radio_circuit_breaker.py"]="tests/unit/engine/test_radio_circuit_breaker.py"
  ["tests/test_patch_1_07_server_timestamp.py"]="tests/unit/server/test_serializers.py"
  ["tests/test_patch_1_08_12_ssrf_path.py"]="tests/unit/server/test_ssrf_guard.py"
  ["tests/test_patch_1_09_password_hashing.py"]="tests/unit/server/test_auth.py"
  ["tests/test_patch_1_10_cleanup.py"]="tests/unit/core/test_cleanup.py"
  ["tests/test_patch_1_11_session_persistence.py"]="tests/unit/server/test_session.py"
  ["tests/test_patch_2_02_command_bus.py"]="tests/unit/core/test_command_bus.py"
  ["tests/test_patch_2_04_audio_output_enum.py"]="tests/unit/core/test_audio_output_enum.py"
  ["tests/test_patch_3_01_07_per_room_eventbus.py"]="tests/unit/core/test_room_event_bus.py"
  ["tests/test_patch_fase0_quick_wins.py"]="tests/unit/test_smoke.py"
  ["tests/test_patch_fase1_security.py"]="tests/unit/server/test_security.py"
  ["tests/test_domain_events.py"]="tests/unit/core/test_domain_events.py"
  ["tests/test_event_bus.py"]="tests/unit/core/test_event_bus.py"
)

for old in "${!TEST_MAP[@]}"; do
  new="${TEST_MAP[$old]}"
  if [ -f "$old" ]; then
    # Pastikan __init__.py ada di folder target
    touch "$(dirname $new)/__init__.py"
    git mv "$old" "$new"
    echo "✓ $(basename $old) → $new"
  else
    echo "SKIP: $old tidak ada"
  fi
done

# Buat fixture sample
cat > tests/fixtures/sample_track.json << 'FIXTURE'
{
  "id": "dQw4w9WgXcQ",
  "title": "Never Gonna Give You Up",
  "artist": "Rick Astley",
  "duration_ms": 213000,
  "source": "youtube"
}
FIXTURE

# Verifikasi semua tests masih bisa di-discover
pytest tests/ --co -q 2>&1 | tail -5
FINAL_COUNT=$(pytest tests/ --co -q 2>/dev/null | wc -l)
BASELINE=$(cat /tmp/baseline_test_count.txt 2>/dev/null || echo "unknown")
echo "Test count: $FINAL_COUNT (baseline: $BASELINE)"

pytest tests/ -q 2>&1 | tail -3

git add -A
git commit -m "refactor(tests): reorganize into domain-based folders

- tests/unit/{core,engine,cache,server,plugins}/
- tests/fixtures/sample_track.json
- Rename test_patch_* files to descriptive names per domain

All tests pass."

echo "=== Fase 5 COMPLETE ==="
```

---

## 8. Fase 6 — Documentation

```bash
echo "=== FASE 6: Documentation ==="

# 1. Update README.md — struktur folder baru
# Review README.md dan pastikan:
# - Folder structure section mencerminkan struktur baru
# - Cara run tidak menyebut TUI
# - Link docs diupdate ke docs/mockups/

grep -n "tui\|widgets\|integrations" README.md  # Harus kosong atau sisa lama

# 2. Buat CONTRIBUTING.md jika belum ada
if [ ! -f "docs/CONTRIBUTING.md" ]; then
  cat > docs/CONTRIBUTING.md << 'DOC'
# Contributing to bagas.fm

## Architecture Laws

Lihat ARCHITECTURE_LOCK.md untuk prinsip lengkap.

## Quick Reference

**Backend:**
- Import direction: `core ← engine ← server ← main`
- Engine akses plugins via `core/ports.py`, bukan direct import
- main.py < 100 baris

**Frontend:**
- Tidak ada hex color di luar `css/tokens.css`
- Tidak ada `addEventListener()` di luar `events.js`
- Tidak ada `wsSend()` di dalam `render/*.js`

## Commit Format

```
feat(scope): description
fix(scope): description
refactor(scope): description
chore: description
```

## Before Push

```bash
pytest tests/ -q
grep -r "addEventListener" web/static/js/render/  # Must be empty
grep -r "wsSend" web/static/js/render/             # Must be empty
```
DOC
  echo "✓ CONTRIBUTING.md dibuat"
fi

git add -A
git commit -m "docs: update README, add CONTRIBUTING.md

- README.md: updated folder structure, removed TUI references
- CONTRIBUTING.md: architecture laws quick reference"

echo "=== Fase 6 COMPLETE ==="
echo ""
echo "=============================="
echo "   REFACTOR SELESAI 🎉"
echo "=============================="
```

---

## 9. Verification Script

> Simpan sebagai `scripts/verify_refactor.sh` dan jalankan setelah setiap fase.

```bash
#!/bin/bash
# Usage: bash scripts/verify_refactor.sh <fase_number>
# Example: bash scripts/verify_refactor.sh 1

PHASE=${1:-"?"}
PASS=0
FAIL=0

check() {
  local label="$1"
  local cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ $label"
    PASS=$((PASS+1))
  else
    echo "  ✗ FAIL: $label"
    FAIL=$((FAIL+1))
  fi
}

echo "=========================================="
echo "  Verification — Fase $PHASE"
echo "=========================================="

echo ""
echo "--- Python Syntax ---"
check "main.py" "python3 -m py_compile main.py"
check "core/*.py" "python3 -m py_compile core/*.py"
check "engine/*.py" "python3 -m py_compile engine/*.py 2>/dev/null || true"

echo ""
echo "--- File Structure ---"
check "tui/ tidak ada" "[ ! -d 'tui' ]"
check "plugins/ ada" "[ -d 'plugins' ]"
check "server/ ada" "[ -d 'server' ]"
check "web/static/css/ ada" "[ -d 'web/static/css' ]"
check "web/static/js/ ada" "[ -d 'web/static/js' ]"
check "web/static/app.js dihapus" "[ ! -f 'web/static/app.js' ]"
check "web/static/style.css dihapus" "[ ! -f 'web/static/style.css' ]"
check "web/server.py dihapus" "[ ! -f 'web/server.py' ]"

echo ""
echo "--- CSS Rules ---"
check "tokens.css ada" "[ -s 'web/static/css/tokens.css' ]"
check "tokens.css punya :root" "grep -q ':root {' web/static/css/tokens.css"
check "Tidak ada legacy var di CSS" \
  "! grep -r 'var(--accent-fire\|var(--bg-panel\|var(--text-primary' web/static/css/ 2>/dev/null | grep -v tokens"

echo ""
echo "--- JS Rules ---"
check "render/ tidak punya addEventListener" \
  "[ \$(grep -r 'addEventListener' web/static/js/render/ 2>/dev/null | wc -l) -eq 0 ]"
check "render/ tidak punya wsSend" \
  "[ \$(grep -r 'wsSend' web/static/js/render/ 2>/dev/null | wc -l) -eq 0 ]"
check "events.js ada" "[ -s 'web/static/js/events.js' ]"

echo ""
echo "--- Import Rules ---"
check "Tidak ada stray 'from integrations'" \
  "! grep -r 'from integrations' --include='*.py' . 2>/dev/null | grep -v '.git'"
check "Tidak ada import engine.queue_mode" \
  "! grep -r 'engine\.queue_mode' --include='*.py' . 2>/dev/null"
check "main.py < 100 baris" "[ \$(wc -l < main.py) -lt 100 ]"

echo ""
echo "--- Test Suite ---"
PYTEST_OUT=$(pytest tests/ -q 2>&1 | tail -3)
echo "  $PYTEST_OUT"
echo "$PYTEST_OUT" | grep -q "passed" && check "All tests pass" "true" || { echo "  ✗ FAIL: Tests"; FAIL=$((FAIL+1)); }

echo ""
echo "=========================================="
echo "  RESULT: $PASS passed, $FAIL failed"
echo "=========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
```

---

## 10. Rollback Plan

### Rollback 1 Commit

```bash
git reset --hard HEAD~1
git clean -fd
pytest tests/ -q
```

### Rollback ke Fase Tertentu

```bash
# Lihat commit per fase
git log --oneline | head -10

# Rollback ke commit yang diinginkan
git reset --hard <COMMIT_HASH>
git clean -fd
pytest tests/ -q
```

### Rollback 1 File Saja

```bash
# Restore file spesifik dari commit sebelumnya
git checkout HEAD~1 -- web/server.py
pytest tests/unit/server/ -q
```

### Emergency Reset ke Awal

```bash
# Lihat commit pertama
git log --oneline --reverse | head -1

# Reset ke baseline
git reset --hard <INITIAL_COMMIT_HASH>
git clean -fd
pytest tests/ -q
```

---

## 11. Error Handling & Recovery

### Test Failures

```bash
# Capture detail
pytest tests/ -v --tb=long 2>&1 | grep -A 15 "FAILED" > /tmp/fail.log
cat /tmp/fail.log

# Common causes:
# [1] Import path lama belum diupdate → cek Pattern C Fase 4
# [2] __init__.py missing di folder baru → touch server/__init__.py
# [3] Circular import → cek import direction (core tidak boleh import engine)
# [4] Fungsi terputus saat ekstraksi → verifikasi fungsi lengkap di file baru
```

### ModuleNotFoundError

```bash
# Cek file ada
ls -la plugins/lyrics.py
ls -la server/handlers/auth.py

# Cek __init__.py ada
ls plugins/__init__.py server/__init__.py server/handlers/__init__.py

# Test import langsung
python3 -c "from plugins.lyrics import LyricsFetcher; print('OK')"
python3 -c "from server.handlers.auth import login_handler; print('OK')"
```

### CSS Rusak Setelah Fase 1

```bash
# Cek urutan link di index.html (tokens.css HARUS pertama)
grep "<link.*css" web/static/index.html

# Cek tokens.css tidak kosong
wc -l web/static/css/tokens.css  # Harus > 50 baris

# Diff dengan original
git show HEAD~1:web/static/style.css > /tmp/orig.css
wc -l /tmp/orig.css  # Bandingkan dengan total semua css baru
cat web/static/css/*.css | wc -l
```

---

## 12. Success Criteria

Refactor dinyatakan **SUKSES** jika semua berikut terpenuhi:

```bash
bash scripts/verify_refactor.sh all
# Output: X passed, 0 failed
```

Atau manual:

| Kriteria | Command Verifikasi |
|---|---|
| All tests pass | `pytest tests/ -q` → 0 failed |
| main.py < 100 baris | `wc -l main.py` |
| tui/ dihapus | `[ ! -d tui ]` |
| integrations/ → plugins/ | `[ -d plugins ] && [ ! -d integrations ]` |
| queue_mode → queue_manager | `[ ! -f engine/queue_mode.py ]` |
| radio_mode → radio_engine | `[ ! -f engine/radio_mode.py ]` |
| app.js dihapus | `[ ! -f web/static/app.js ]` |
| style.css dihapus | `[ ! -f web/static/style.css ]` |
| web/server.py dihapus | `[ ! -f web/server.py ]` |
| 7 CSS files | `ls web/static/css/*.css \| wc -l` → 7 |
| ~14 JS files | `ls web/static/js/**/*.js \| wc -l` → ~14 |
| Tidak ada addEventListener di render/ | `grep -r "addEventListener" web/static/js/render/` → kosong |
| Tidak ada wsSend di render/ | `grep -r "wsSend" web/static/js/render/` → kosong |
| Tidak ada hex color di luar tokens.css | `grep -h "#[0-9a-f]\{6\}" web/static/css/{base,layout,player,components,tabs,portal}.css` → kosong |

---

*End of AI_AGENT_PLAYBOOK.md*
