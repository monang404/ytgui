#!/data/data/com.termux/files/usr/bin/bash
SOCK="${TMPDIR:-/data/data/com.termux/files/usr/tmp}/mpv-yt-player.sock"

if [ -S "$SOCK" ]; then
    echo '{"command":["playlist-next","force"]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
    termux-notification --title "YT Player" --content "⏭ Next Track"
fi
