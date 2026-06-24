#!/usr/bin/env bash
# ============================================================
# fix_miniplayer.sh
# Fix: mini player hancur di non-home tabs (Search, Radio, dll)
#
# Root cause:
#   - .pb-ctrl  punya inline style="position:relative;"
#   - .pb-badges punya inline style="position:absolute; ..."
#   Inline style tidak bisa di-override oleh CSS class selector,
#   sehingga override `position: static` di mini player mode
#   tidak bekerja — .pb-badges melayang keluar container.
#
# Changes:
#   web/static/index.html   — hapus 2 inline style
#   web/static/css/base.css — upgrade .pb-badges + tambah hide rule
#
# Usage:
#   cd /path/to/ytgui-main
#   bash fix_miniplayer.sh
# ============================================================

set -euo pipefail

HTML="web/static/index.html"
CSS="web/static/css/base.css"

# ---------- validasi file ada ----------
for f in "$HTML" "$CSS"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: File tidak ditemukan: $f"
        echo "Jalankan script ini dari root folder proyek (ytgui-main/)."
        exit 1
    fi
done

echo "==> bagas.fm — Mini Player Patch"
echo "    HTML : $HTML"
echo "    CSS  : $CSS"
echo ""

# ============================================================
# PATCH 1 — index.html
# Hapus inline style dari .pb-ctrl
# ============================================================
BEFORE_CTRL='        <div class="pb-ctrl" style="position:relative;">'
AFTER_CTRL='        <div class="pb-ctrl">'

if grep -qF "$BEFORE_CTRL" "$HTML"; then
    sed -i "s|        <div class=\"pb-ctrl\" style=\"position:relative;\">|        <div class=\"pb-ctrl\">|" "$HTML"
    echo "[PATCH 1 OK] Hapus inline style dari .pb-ctrl"
else
    echo "[PATCH 1 SKIP] .pb-ctrl inline style tidak ditemukan (sudah di-patch?)"
fi

# ============================================================
# PATCH 2 — index.html
# Hapus inline style dari .pb-badges
# ============================================================
BEFORE_BADGES='            <div class="pb-badges" style="position:absolute; left:0; bottom:12px; display:flex; gap:4px; align-items:center;">'
AFTER_BADGES='            <div class="pb-badges">'

if grep -qF "$BEFORE_BADGES" "$HTML"; then
    python3 - "$HTML" "$BEFORE_BADGES" "$AFTER_BADGES" <<'PYEOF'
import sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
PYEOF
    echo "[PATCH 2 OK] Hapus inline style dari .pb-badges"
else
    echo "[PATCH 2 SKIP] .pb-badges inline style tidak ditemukan (sudah di-patch?)"
fi

# ============================================================
# PATCH 3 — base.css
# Upgrade .pb-badges: tambah position/left/bottom/align-items
# ============================================================
OLD_BADGES='.pb-badges{display:flex;gap:5px;margin-top:5px;margin-bottom:4px}'
NEW_BADGES='.pb-badges{display:flex;gap:5px;margin-top:5px;margin-bottom:4px;position:absolute;left:0;bottom:12px;align-items:center}'

if grep -qF "$OLD_BADGES" "$CSS"; then
    sed -i "s|${OLD_BADGES}|${NEW_BADGES}|" "$CSS"
    echo "[PATCH 3 OK] .pb-badges di CSS ditambah position/left/bottom"
else
    echo "[PATCH 3 SKIP] .pb-badges belum match — cek manual"
fi

# ============================================================
# PATCH 4 — base.css
# Tambah hide rule untuk .pb-badges di mini player mode
# Disisipkan tepat sebelum penutup blok @media mini player (baris setelah .btn-play override)
# ============================================================
ANCHOR='    body:not(\[data-active-tab="home"\]) #player-bar .btn-play {
        width: 44px;
        height: 44px;
        font-size: 16px;
    }
}'

HIDE_RULE='    body:not([data-active-tab="home"]) #player-bar .btn-play {
        width: 44px;
        height: 44px;
        font-size: 16px;
    }
    body:not([data-active-tab="home"]) #player-bar .pb-badges {
        display: none !important;
    }
}'

# Gunakan python untuk insert yang lebih aman daripada sed multi-line
python3 - "$CSS" <<'PYEOF'
import sys, re

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Cek apakah hide rule sudah ada
if 'pb-badges" {\n        display: none !important;' in content or \
   '.pb-badges {\n        display: none !important;' in content:
    print("[PATCH 4 SKIP] Hide rule .pb-badges di mini player sudah ada")
    sys.exit(0)

old = (
    '    body:not([data-active-tab="home"]) #player-bar .btn-play {\n'
    '        width: 44px;\n'
    '        height: 44px;\n'
    '        font-size: 16px;\n'
    '    }\n'
    '}'
)
new = (
    '    body:not([data-active-tab="home"]) #player-bar .btn-play {\n'
    '        width: 44px;\n'
    '        height: 44px;\n'
    '        font-size: 16px;\n'
    '    }\n'
    '    body:not([data-active-tab="home"]) #player-bar .pb-badges {\n'
    '        display: none !important;\n'
    '    }\n'
    '}'
)

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[PATCH 4 OK] Hide rule .pb-badges ditambahkan ke mini player block")
else:
    print("[PATCH 4 SKIP] Anchor string tidak cocok — cek manual base.css")
PYEOF

# ============================================================
# Verifikasi akhir
# ============================================================
echo ""
echo "=== Verifikasi ==="

echo -n "pb-ctrl tidak punya inline style : "
if grep -q 'pb-ctrl.*style=' "$HTML"; then
    echo "GAGAL — masih ada inline style"
else
    echo "OK"
fi

echo -n "pb-badges tidak punya inline style: "
if grep -q 'pb-badges.*style=' "$HTML"; then
    echo "GAGAL — masih ada inline style"
else
    echo "OK"
fi

echo -n ".pb-badges CSS punya position:absolute: "
if grep -q 'pb-badges.*position:absolute' "$CSS"; then
    echo "OK"
else
    echo "GAGAL"
fi

echo -n "Hide rule pb-badges di mini player : "
if grep -q 'home.*pb-badges' "$CSS" || grep -A2 'not.*home.*pb-badges' "$CSS" | grep -q 'none'; then
    echo "OK"
else
    # second check
    if grep -q 'pb-badges' "$CSS" | grep -q 'none'; then
        echo "OK"
    else
        python3 -c "
import sys
with open('$CSS') as f: c = f.read()
ok = ('pb-badges' in c and 'none !important' in c[c.find('pb-badges'):c.find('pb-badges')+200])
print('OK' if ok else 'GAGAL — tambahkan manual')
"
    fi
fi

echo ""
echo "Patch selesai. Restart server bagas.fm dan test di browser."
