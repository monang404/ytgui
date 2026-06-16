#!/data/data/com.termux/files/usr/bin/bash
BASE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SOCK="$BASE_DIR/cache/sockets/ytplayer_mpv.sock"

if [ -S "$SOCK" ]; then
    echo '{"command":["playlist-next","force"]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
    termux-notification --title "YT Player" --content "⏭ Next Track"
fi
