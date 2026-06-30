#!/usr/bin/env bash

# ----------------------------------------------------------
#  CONFIGURATION
# ----------------------------------------------------------
export YTGUI_HOST="0.0.0.0"
export YTGUI_PORT=${YTGUI_PORT:-8765}

# export YTGUI_ADMIN_USER="admin"
# export YTGUI_ADMIN_PASS="your_secret_password"

# ----------------------------------------------------------
#  COLORS & FORMATTING
# ----------------------------------------------------------
RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[1;36m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
MAGENTA="\033[1;35m"

# ----------------------------------------------------------
#  BANNER
# ----------------------------------------------------------
clear
echo -e "${MAGENTA}${BOLD}"
cat << "EOF"
   __   __ _____  ____  _   _   ___     _____  __  __
   \ \ / /|_   _|/ ___|| | | |  | |    |  ___||  \/  |
    \ V /   | | | |  _ | | | |  | |    | |_   | |\/| |
     | |    | | | |_| || |_| |  | |    |  _|  | |  | |
     |_|    |_|  \____| \___/   |_|    |_|    |_|  |_|

EOF
echo -e "${CYAN}    ========================================================="
echo -e "                    YTGUI Web Server Startup                 "
echo -e "    =========================================================${RESET}"
echo ""

# ----------------------------------------------------------
#  STARTUP SEQUENCE
# ----------------------------------------------------------

echo -e "${CYAN}[*]${RESET} Initializing Environment Variables..."
sleep 0.5

echo -e "${CYAN}[*]${RESET} Checking Python Dependencies..."
MISSING_DEPS=0
DEPS="aiohttp aiosqlite yt_dlp syncedlyrics structlog prometheus_client opentelemetry"
for dep in $DEPS; do
    if ! python3 -c "import $dep" &> /dev/null; then
        echo -e "    ${RED}[-]${RESET} Missing module: $dep"
        MISSING_DEPS=1
    fi
done

if [ $MISSING_DEPS -eq 0 ]; then
    echo -e "    ${GREEN}[+]${RESET} All Python dependencies are satisfied."
else
    echo -e "\n${YELLOW}[!] WARNING: Some dependencies are missing.${RESET}"
    echo -e "    Please run: ${BOLD}pip install -r requirements.txt${RESET}\n"
    sleep 2
fi

echo -e "${CYAN}[*]${RESET} Verifying MPV Installation..."
if command -v mpv &> /dev/null; then
    MPV_VER=$(mpv --version 2>/dev/null | head -1 | awk '{print $2}')
    echo -e "    ${GREEN}[+]${RESET} MPV detected (v${MPV_VER:-?})."
else
    echo -e "    ${RED}[-]${RESET} MPV not found in system PATH!"
    echo -e "        Termux : ${BOLD}pkg install mpv${RESET}"
    echo -e "        Debian : ${BOLD}sudo apt install mpv${RESET}"
    echo -e "        Arch   : ${BOLD}sudo pacman -S mpv${RESET}"
    sleep 2
fi

echo -e "${CYAN}[*]${RESET} Cleaning Up Previous Sessions..."
if command -v killall &> /dev/null; then
    killall mpv > /dev/null 2>&1
else
    pkill mpv > /dev/null 2>&1
fi

if [ -d "/tmp" ]; then
    rm -f /tmp/mpv-socket-* 2>/dev/null
fi

SOCKET_DIR="${YT_PLAYER_BASE:-$(dirname "$0")}/cache/sockets"
if [ -d "$SOCKET_DIR" ]; then
    rm -f "$SOCKET_DIR"/*.sock 2>/dev/null
fi

if command -v fuser &> /dev/null; then
    fuser -k ${YTGUI_PORT}/tcp > /dev/null 2>&1
elif command -v lsof &> /dev/null; then
    lsof -ti tcp:${YTGUI_PORT} | xargs kill -9 > /dev/null 2>&1
fi

# ----------------------------------------------------------
#  ADMIN ACCESS INFO
# ----------------------------------------------------------
PASS_FILE="${YT_PLAYER_BASE:-$(dirname "$0")}/cache/admin_password.txt"
echo ""
echo -e "${MAGENTA}---------------------------------------------------------${RESET}"
echo -e "${BOLD} Admin Access Information${RESET}"
echo -e "${MAGENTA}---------------------------------------------------------${RESET}"

if [ -n "$YTGUI_ADMIN_PASS" ]; then
    echo -e "  [i] Password loaded from environment (YTGUI_ADMIN_PASS)."
elif [ -f "$PASS_FILE" ]; then
    echo -e "  [i] Password stored securely in: $PASS_FILE"
else
    echo -e "  [i] A new password will be auto-generated on first launch."
fi
echo -e "  [i] Username: ${BOLD}${YTGUI_ADMIN_USER:-admin}${RESET}"

# ----------------------------------------------------------
#  SERVER STARTUP
# ----------------------------------------------------------
echo ""
echo -e "${CYAN}    =========================================================${RESET}"
echo -e "       Client Interface : ${BOLD}http://localhost:${YTGUI_PORT}/${RESET}"
echo -e "       Admin Interface  : ${BOLD}http://localhost:${YTGUI_PORT}/admin${RESET}"
echo -e "       System Health    : ${BOLD}http://localhost:${YTGUI_PORT}/health${RESET}"
echo -e "       Metrics          : ${BOLD}http://localhost:${YTGUI_PORT}/metrics${RESET}"
echo -e "${CYAN}    =========================================================${RESET}"
echo ""
echo -e "${GREEN}[*] Starting Server...${RESET}"
sleep 1

python3 main.py

if [ $? -ne 0 ]; then
    echo -e "\n${RED}[X] Server terminated with an error.${RESET}"
    echo -e "    Please check the application logs for details."
fi
