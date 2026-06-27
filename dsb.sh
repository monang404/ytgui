#!/usr/bin/env bash
# disable_sw.sh — Matikan Service Worker ytgui buat development.
#
# Yang dilakukan script ini (idempotent — aman dijalankan berkali-kali):
#   1. Comment-out registrasi service worker di web/static/js/main.js
#      (supaya SW baru nggak ke-install lagi).
#   2. Suntik script kecil di web/static/index.html yang otomatis
#      UNREGISTER service worker lama + hapus semua Cache Storage
#      begitu halaman dibuka — jadi HP kamu nggak perlu manual
#      clear cache di Settings, cukup reload halaman sekali.
#   3. Bump CACHE_VERSION di web/static/sw.js (jaga-jaga kalau nanti
#      mau diaktifkan lagi, biar nggak ke-cache versi basi).
#
# File asli dibackup dengan suffix .bak_presw sebelum diubah.
#
# Cara pakai:
#   chmod +x disable_sw.sh
#   ./disable_sw.sh                # default: dijalankan dari root project ytgui-main
#   ./disable_sw.sh /path/ke/ytgui-main

set -euo pipefail

PROJECT_DIR="${1:-.}"
MAIN_JS="${PROJECT_DIR}/web/static/js/main.js"
INDEX_HTML="${PROJECT_DIR}/web/static/index.html"
SW_JS="${PROJECT_DIR}/web/static/sw.js"

for f in "$MAIN_JS" "$INDEX_HTML" "$SW_JS"; do
    if [ ! -f "$f" ]; then
        echo "[ERROR] File tidak ditemukan: $f"
        echo "        Jalankan script ini dari root project ytgui-main, atau:"
        echo "        ./disable_sw.sh /path/ke/ytgui-main"
        exit 1
    fi
done

backup() {
    local f="$1"
    local bak="${f}.bak_presw"
    if [ ! -f "$bak" ]; then
        cp "$f" "$bak"
        echo "[backup] $f -> $bak"
    else
        echo "[skip backup] $bak sudah ada, tidak ditimpa"
    fi
}

echo "=== 1. Comment-out registrasi Service Worker di main.js ==="
backup "$MAIN_JS"

python3 - "$MAIN_JS" << 'PYEOF'
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

MARKER = "DISABLED selama development"
if MARKER in src:
    print("[skip] Registrasi SW sudah dalam keadaan disabled.")
    sys.exit(0)

pattern = re.compile(
    r"if \('serviceWorker' in navigator\) \{.*?\n\}\n",
    re.DOTALL,
)

match = pattern.search(src)
if not match:
    print("[WARNING] Blok registrasi serviceWorker tidak ditemukan (mungkin sudah diubah manual).")
    sys.exit(0)

block = match.group(0)
commented = "\n".join(
    ("// " + line) if line.strip() else line
    for line in block.rstrip("\n").split("\n")
)
replacement = (
    f"// {MARKER} — biar nggak ke-cache stale.\n"
    "// Aktifkan lagi kalau sudah siap \"production\" (uncomment di bawah).\n"
    f"{commented}\n"
)

new_src = src[:match.start()] + replacement + src[match.end():]
with open(path, "w", encoding="utf-8") as f:
    f.write(new_src)

print("[OK] Registrasi service worker sudah dikomentari.")
PYEOF

echo ""
echo "=== 2. Suntik auto-unregister + clear cache di index.html ==="
backup "$INDEX_HTML"

python3 - "$INDEX_HTML" << 'PYEOF'
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

MARKER = "AUTO-UNREGISTER-SW"
if MARKER in src:
    print("[skip] Snippet auto-unregister sudah ada di index.html.")
    sys.exit(0)

SNIPPET = """<!-- AUTO-UNREGISTER-SW: matikan SW lama + bersihkan cache. Hapus blok ini setelah selesai development. -->
<script>
(function () {
    if (!('serviceWorker' in navigator)) return;
    navigator.serviceWorker.getRegistrations().then(function (regs) {
        regs.forEach(function (r) {
            r.unregister();
            console.log('[dev] Service worker unregistered:', r.scope);
        });
    });
    if (window.caches && caches.keys) {
        caches.keys().then(function (keys) {
            keys.forEach(function (k) {
                caches.delete(k);
                console.log('[dev] Cache dihapus:', k);
            });
        });
    }
})();
</script>
</body>"""

if "</body>" not in src:
    print("[WARNING] Tag </body> tidak ditemukan, snippet tidak disisipkan.")
    sys.exit(0)

new_src = src.replace("</body>", SNIPPET, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(new_src)

print("[OK] Snippet auto-unregister disisipkan sebelum </body>.")
PYEOF

echo ""
echo "=== 3. Bump CACHE_VERSION di sw.js (jaga-jaga) ==="
backup "$SW_JS"

TS="$(date +%Y%m%d_%H%M)"
if grep -q "^const CACHE_VERSION" "$SW_JS"; then
    sed -i.tmp "s/^const CACHE_VERSION = '.*';.*/const CACHE_VERSION = 'bagas-fm-${TS}-dev';/" "$SW_JS"
    rm -f "${SW_JS}.tmp"
    echo "[OK] CACHE_VERSION dibump ke bagas-fm-${TS}-dev"
else
    echo "[WARNING] Baris CACHE_VERSION tidak ditemukan di $SW_JS, dilewati."
fi

echo ""
echo "=== SELESAI ==="
echo "Restart server (kalau perlu), lalu reload halaman SEKALI di browser HP kamu."
echo "Saat reload itu, script auto-unregister akan jalan otomatis dan bersihkan SW + cache lama."
echo "Reload SEKALI LAGI setelah itu untuk memastikan halaman benar-benar fresh."
echo ""
echo "Untuk balikin semua perubahan ini (kalau mau aktifkan SW lagi nanti):"
echo "  mv ${MAIN_JS}.bak_presw ${MAIN_JS}"
echo "  mv ${INDEX_HTML}.bak_presw ${INDEX_HTML}"
echo "  mv ${SW_JS}.bak_presw ${SW_JS}"
