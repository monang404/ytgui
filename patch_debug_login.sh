#!/usr/bin/env bash
# patch_debug_login.sh
# Uncomment dan set YTGUI_ADMIN_USER & YTGUI_ADMIN_PASS di start.sh
# Usage: bash patch_debug_login.sh [path/to/start.sh]

START_SH="${1:-$(dirname "$0")/start.sh}"

if [ ! -f "$START_SH" ]; then
    echo "[ERROR] File tidak ditemukan: $START_SH"
    exit 1
fi

sed -i \
    's|^# export YTGUI_ADMIN_USER=.*|export YTGUI_ADMIN_USER="admin"|' \
    "$START_SH"

sed -i \
    's|^# export YTGUI_ADMIN_PASS=.*|export YTGUI_ADMIN_PASS="admin"|' \
    "$START_SH"

echo "[OK] start.sh berhasil di-patch:"
grep -E "YTGUI_ADMIN_USER|YTGUI_ADMIN_PASS" "$START_SH" | head -2
