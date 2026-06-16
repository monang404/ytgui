#!/data/data/com.termux/files/usr/bin/bash
SOCK="/tmp/mpv-yt-player.sock"

if [ -S "$SOCK" ]; then
    echo '{"command":["add","volume", 5]}' | \
        socat - UNIX-CONNECT:"$SOCK" 2>/dev/null
fi
