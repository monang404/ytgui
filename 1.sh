#!/usr/bin/env bash
# =============================================================================
# fix_ytgui_bugs.sh — Patch 3 bug ytgui (Android Chrome Mobile)
#
# BUG 1: Navbar invisible setelah login
#         → body belum punya data-active-tab saat #app pertama muncul,
#           sehingga CSS position:absolute player-bar menutupi navrow.
#
# BUG 2: Radio toggle tidak bereaksi (tap tidak ada efek)
#         → touchend swipe handler di document menelan event tap di radio card.
#
# BUG 3: Radio toggle tidak optimistic (kuning + playlist baru muncul setelah
#         server reply, terasa lag atau tidak sama sekali jika WS lambat)
#         → store & render tidak diupdate sebelum wsSend.
#
# Usage:
#   chmod +x fix_ytgui_bugs.sh
#   ./fix_ytgui_bugs.sh /path/to/ytgui-main
#
# Jika path tidak diberikan, script mencari di direktori saat ini.
# =============================================================================

set -euo pipefail

# ── Resolve project root ──────────────────────────────────────────────────────
ROOT="${1:-$(pwd)}"
ROOT="${ROOT%/}"   # hapus trailing slash

MAIN_JS="$ROOT/web/static/js/main.js"
PORTAL_JS="$ROOT/web/static/js/portal.js"
EVENTS_JS="$ROOT/web/static/js/events.js"

# ── Helpers ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

check_file() {
    [[ -f "$1" ]] || die "File tidak ditemukan: $1"
}

# Ganti teks menggunakan Python (hindari masalah delimiter sed di semua OS)
py_replace() {
    local file="$1" old="$2" new="$3"
    python3 - "$file" "$old" "$new" <<'PYEOF'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
if old not in content:
    print(f"NOTFOUND", end='')
    sys.exit(0)
count = content.count(old)
if count > 1:
    print(f"AMBIGUOUS:{count}", end='')
    sys.exit(0)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content.replace(old, new, 1))
print("OK", end='')
PYEOF
}

apply_patch() {
    local label="$1" file="$2" old="$3" new="$4"
    local result
    result=$(py_replace "$file" "$old" "$new")
    case "$result" in
        OK)        info "$label" ;;
        NOTFOUND)  warn "$label — pola tidak ditemukan, mungkin sudah diterapkan. Dilewati." ;;
        AMBIGUOUS*) die "$label — pola ditemukan ${result#*:}x (ambigu). Batalkan." ;;
        *)         die "$label — error tak terduga: $result" ;;
    esac
}

# ── Validasi file ─────────────────────────────────────────────────────────────
echo ""
echo "=== ytgui Bug Patcher ==="
echo "Project root: $ROOT"
echo ""

check_file "$MAIN_JS"
check_file "$PORTAL_JS"
check_file "$EVENTS_JS"

# ── Backup ────────────────────────────────────────────────────────────────────
BACKUP_DIR="$ROOT/.patch_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp "$MAIN_JS"   "$BACKUP_DIR/"
cp "$PORTAL_JS" "$BACKUP_DIR/"
cp "$EVENTS_JS" "$BACKUP_DIR/"
info "Backup tersimpan di: $BACKUP_DIR"
echo ""

# =============================================================================
# BUG 1 — Navbar invisible setelah login
#
# FIX A: Set data-active-tab sebelum init() agar CSS selectors langsung valid.
# File: main.js
# =============================================================================
apply_patch \
  "BUG 1 — Fix A: set data-active-tab sebelum init() [main.js]" \
  "$MAIN_JS" \
  '    function init() {
        initDOM();
        initPortal();
        initAudio();
        initEvents();
        wsConnect();
    }' \
  '    function init() {
        // FIX BUG-1: set data-active-tab SEBELUM DOM diinit supaya CSS selector
        // body:not([data-active-tab="home"]) tidak aktif saat #app pertama muncul.
        // Tanpa ini, player-bar jadi position:absolute dan menutupi navbar.
        document.body.dataset.activeTab = (typeof store !== "undefined" && store.active_tab)
            ? store.active_tab
            : "home";
        initDOM();
        initPortal();
        initAudio();
        initEvents();
        wsConnect();
    }'

# FIX B: Paksa recalculate viewport height saat app ditampilkan setelah login.
# File: portal.js — blok admin di applyRoleUI()
# =============================================================================
apply_patch \
  "BUG 1 — Fix B: fixViewportHeight() saat login admin [portal.js]" \
  "$PORTAL_JS" \
  '    } else if (store.userRole === "admin") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.remove("client-mode");
        dom.logoutBtn.style.display = "flex";
        switchTab("home");
    }' \
  '    } else if (store.userRole === "admin") {
        dom.portalScreen.classList.remove("portal-active");
        dom.appContainer.classList.remove("portal-active");
        document.body.classList.remove("client-mode");
        dom.logoutBtn.style.display = "flex";
        switchTab("home");
        // FIX BUG-1: setelah #app visible, paksa recalculate tinggi viewport.
        // Android Chrome tidak auto-fire visualViewport resize saat element
        // berubah dari display:none ke display:flex, sehingga nav-bar bisa
        // terpotong sampai user scroll atau resize manual.
        if (window.visualViewport) {
            const _app = document.getElementById("app");
            if (_app) {
                _app.style.height = window.visualViewport.height + "px";
            }
        }
    }'

# =============================================================================
# BUG 2 — Swipe handler menelan tap di radio card
#
# FIX: Guard touchend agar tidak intercept tap pada elemen interaktif.
# File: main.js
# =============================================================================
apply_patch \
  "BUG 2 — Guard swipe agar tidak block tap radio toggle [main.js]" \
  "$MAIN_JS" \
  'document.addEventListener('\''touchend'\'', e => {
    if (e.changedTouches.length === 1) {
        const touchEndX = e.changedTouches[0].screenX;
        if (Math.abs(touchEndX - touchStartX) > 80) {
            if (touchEndX < touchStartX) cmd('\''next'\'');
            else cmd('\''prev'\'');
        }
    }
});' \
  'document.addEventListener('\''touchend'\'', e => {
    // FIX BUG-2: jangan intercept tap pada elemen yang punya handler sendiri.
    // Tanpa guard ini, tap singkat di radio-toggle-btn atau button lain bisa
    // terbaca sebagai swipe (delta X < 80 tapi handler tetap konsumsi event).
    if (e.target.closest(
        "#radio-toggle-btn, button, a, input, select, textarea, [role=\"button\"]"
    )) return;
    if (e.changedTouches.length === 1) {
        const touchEndX = e.changedTouches[0].screenX;
        if (Math.abs(touchEndX - touchStartX) > 80) {
            if (touchEndX < touchStartX) cmd('\''next'\'');
            else cmd('\''prev'\'');
        }
    }
});'

# =============================================================================
# BUG 3 — Radio toggle tidak optimistic (kuning + playlist lag / tidak muncul)
#
# FIX: Update store & render SEBELUM wsSend supaya UI langsung bereaksi.
# File: events.js
# =============================================================================
apply_patch \
  "BUG 3 — Optimistic update untuk radio toggle [events.js]" \
  "$EVENTS_JS" \
  '    dom.radioToggleBtn.addEventListener("click", () => {
        if (store.userRole !== "admin") return;
        const newMode = store.playback_mode === "RADIO" ? "QUEUE" : "RADIO";
        wsSend("set_mode", { mode: newMode });
    });' \
  '    dom.radioToggleBtn.addEventListener("click", () => {
        if (store.userRole !== "admin") return;
        const newMode = store.playback_mode === "RADIO" ? "QUEUE" : "RADIO";
        // FIX BUG-3: optimistic update — jangan tunggu server reply.
        // Sebelumnya UI baru berubah setelah WS state message datang dari server,
        // sehingga tombol terasa tidak bereaksi (lag atau blank di mobile).
        store.playback_mode = newMode;
        if (typeof renderRadio === "function") renderRadio();
        if (typeof renderQueue === "function") renderQueue();
        wsSend("set_mode", { mode: newMode });
    });'

# ── Selesai ───────────────────────────────────────────────────────────────────
echo ""
echo "=== Patch selesai ==="
echo ""
echo "File yang diubah:"
echo "  · $MAIN_JS"
echo "  · $PORTAL_JS"
echo "  · $EVENTS_JS"
echo ""
echo "Untuk membatalkan semua perubahan:"
echo "  cp $BACKUP_DIR/* $ROOT/web/static/js/"
echo ""
