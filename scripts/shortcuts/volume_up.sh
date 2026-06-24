#!/data/data/com.termux/files/usr/bin/bash
BASE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SOCK="$BASE_DIR/cache/sockets/ytplayer_mpv.sock"

if [ -S "$SOCK" ]; then
    echo '{"command":["add","volume", 5]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
fi
