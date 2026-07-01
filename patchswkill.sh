#!/usr/bin/env bash
# ============================================================================
# patch_swkill.sh — ytgui: bersihkan Service Worker zombie yang nge-cache JS
# lama (ws.js, audio.js, player.js, dll) sehingga perubahan dari patch.sh
# sebelumnya tidak kelihatan di browser walau server sudah pakai kode baru.
#
# Root cause: web/static/sw.js pakai strategi cache-first untuk static asset.
# Registrasinya di main.js sudah di-comment ("DISABLED selama development"),
# TAPI service worker yang sempat ter-register di sesi sebelumnya tetap aktif
# di browser dan terus melayani Cache Storage miliknya sendiri, lepas dari
# apapun yang berubah di disk/server. Hard refresh biasa TIDAK cukup karena
# Service Worker beroperasi di luar jalur HTTP cache normal.
#
# Fix ini menambahkan kill-switch <script> di awal <body> index.html yang:
#   1. Unregister semua Service Worker yang ter-attach ke origin ini.
#   2. Hapus semua Cache Storage (caches.keys() -> caches.delete()).
#   3. Kalau memang ada yang dibersihkan, reload sekali (pakai sessionStorage
#      flag supaya tidak reload-loop) supaya semua asset di-fetch ulang
#      langsung dari network.
#
# Jalankan dari root project ytgui (folder yang berisi main.py).
# Aman dijalankan berkali-kali (idempotent).
# ============================================================================
set -euo pipefail

MARKER="PATCH-SW-KILLSWITCH-01"

# ---------------------------------------------------------------------------
# 0. Validasi lokasi
# ---------------------------------------------------------------------------
if [[ ! -f "main.py" || ! -d "web/static" ]]; then
    echo "[ERROR] Jalankan script ini dari root folder project ytgui (folder yang ada main.py)." >&2
    exit 1
fi

INDEX_HTML="web/static/index.html"

if [[ ! -f "$INDEX_HTML" ]]; then
    echo "[ERROR] File tidak ditemukan: $INDEX_HTML (struktur project beda dari yang diharapkan)" >&2
    exit 1
fi

PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"; else echo "[ERROR] python3 tidak ditemukan." >&2; exit 1; fi

if grep -q "$MARKER" "$INDEX_HTML" 2>/dev/null; then
    echo "[SKIP] Kill-switch sudah pernah dipasang sebelumnya (marker $MARKER ditemukan). Tidak ada yang dilakukan."
    exit 0
fi

# ---------------------------------------------------------------------------
# 1. Backup
# ---------------------------------------------------------------------------
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".patch_swkill_backup_${TS}"
mkdir -p "$BACKUP_DIR/$(dirname "$INDEX_HTML")"
cp "$INDEX_HTML" "$BACKUP_DIR/$INDEX_HTML"
echo "[INFO] Backup file asli disimpan di: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 2. Apply patch
# ---------------------------------------------------------------------------
"$PY" - "$INDEX_HTML" "$MARKER" <<'PYEOF'
import sys

index_html, MARKER = sys.argv[1:3]

def M(s):
    return s.replace("__MARKER__", MARKER)

with open(index_html, "r", encoding="utf-8") as fh:
    content = fh.read()

# Cari titik sisip: tepat sebelum baris <script src=".../config.js" ...>
# (script pertama yang dimuat), supaya kill-switch jalan paling awal.
anchor = '<script src="/static/js/config.js" defer></script>'
count = content.count(anchor)
if count != 1:
    print(f"[ERROR] Anchor tag config.js ditemukan {count}x di {index_html} (harus tepat 1x). "
          f"Struktur index.html mungkin sudah beda dari yang diharapkan — patch dibatalkan.", file=sys.stderr)
    sys.exit(1)

snippet = M('''<script>
    // __MARKER__: Service Worker registration sudah di-DISABLE di main.js,
    // tapi SW lama yang sempat ter-register di sesi sebelumnya tetap aktif
    // di browser dan terus melayani JS/CSS dari cache lamanya sendiri,
    // lepas dari perubahan apapun di server/disk. Ini sebabnya patch.sh
    // sudah jalan benar tapi browser "tidak berubah". Jalankan SEKALI di
    // awal load, sebelum script lain: unregister semua SW yang nyangkut +
    // hapus semua Cache Storage punya origin ini, lalu kalau memang ada
    // yang dihapus, force reload sekali biar fetch ulang semua asset
    // langsung dari network (bukan dari SW yang baru mati).
    (function () {
        "use strict";
        if (!('serviceWorker' in navigator)) return;
        var didCleanup = false;

        var unregisterAll = navigator.serviceWorker.getRegistrations()
            .then(function (regs) {
                if (!regs.length) return;
                didCleanup = true;
                return Promise.all(regs.map(function (r) { return r.unregister(); }));
            })
            .catch(function (e) { console.warn('[sw-kill] unregister failed:', e); });

        var clearCaches = ('caches' in window)
            ? caches.keys().then(function (keys) {
                if (!keys.length) return;
                didCleanup = true;
                return Promise.all(keys.map(function (k) { return caches.delete(k); }));
            }).catch(function (e) { console.warn('[sw-kill] cache clear failed:', e); })
            : Promise.resolve();

        Promise.all([unregisterAll, clearCaches]).then(function () {
            if (didCleanup && !sessionStorage.getItem('sw_killswitch_reloaded')) {
                console.log('[sw-kill] stale service worker / cache dibersihkan, reload sekali...');
                sessionStorage.setItem('sw_killswitch_reloaded', '1');
                location.reload();
            } else if (didCleanup) {
                console.log('[sw-kill] dibersihkan (reload sudah pernah dilakukan sesi ini).');
            }
        });
    })();
    </script>

    ''') + anchor

content = content.replace(anchor, snippet)

with open(index_html, "w", encoding="utf-8") as fh:
    fh.write(content)

print(f"[OK] Kill-switch terpasang -> {index_html}")
print("[DONE] Patch berhasil diterapkan.")
PYEOF

# ---------------------------------------------------------------------------
# 3. Verifikasi
# ---------------------------------------------------------------------------
if ! grep -q "$MARKER" "$INDEX_HTML"; then
    echo "[ERROR] Marker tidak ditemukan di $INDEX_HTML setelah patch — sesuatu salah." >&2
    exit 1
fi
echo "[OK] Marker terverifikasi di $INDEX_HTML"

# Cek dasar: jumlah <script>...</script> yang baru ditambah balance (1 open, 1 close)
OPEN_COUNT=$(grep -o "<script>" "$INDEX_HTML" | wc -l)
echo "[INFO] Total <script> tag tanpa atribut (termasuk kill-switch) di file: $OPEN_COUNT"

echo ""
echo "============================================================"
echo " Kill-switch berhasil dipasang di: $INDEX_HTML"
echo " Backup file asli ada di: $BACKUP_DIR"
echo ""
echo " Restart server (python main.py / start.sh), lalu buka ytgui"
echo " di Chrome Android SEKALI seperti biasa (tidak perlu hard-refresh"
echo " manual / clear site data lagi) — kill-switch akan otomatis:"
echo "   1. Unregister service worker lama"
echo "   2. Hapus semua Cache Storage punya origin ini"
echo "   3. Reload halaman sekali otomatis"
echo " Setelah reload itu, semua JS (termasuk fix dari patch.sh sebelumnya)"
echo " akan diambil langsung dari server, bukan dari cache SW lama."
echo "============================================================"
