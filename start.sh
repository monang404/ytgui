#!/usr/bin/env bash
# yt-termux-player-pro startup script untuk Linux / Termux
# Diperbarui: Fase 3 — Per-Room EventBus Architecture

# ──────────────────────────────────────────────────────────
#  KONFIGURASI — Ubah sesuai kebutuhan
# ──────────────────────────────────────────────────────────

export YTGUI_HOST="0.0.0.0"
export YTGUI_PORT=8765

# Direktori kerja (default: folder script ini berada)
# Uncomment dan ubah jika ingin menempatkan cache di tempat lain
# export YT_PLAYER_BASE="/sdcard/ytgui"

# Kredensial admin
# Jika tidak di-set, password akan digenerate otomatis dan disimpan di cache/admin_password.txt
# Jika di-set, password akan di-hash otomatis saat startup (tidak perlu hash manual)
# export YTGUI_ADMIN_USER="admin"
# export YTGUI_ADMIN_PASS="password_rahasia_anda"

# Token opsional untuk akses endpoint /metrics dari luar localhost
# Jika tidak di-set, /metrics hanya bisa diakses dari 127.0.0.1
# export YTGUI_METRICS_TOKEN="token_rahasia_metrics"

# Port TCP untuk MPV di Windows (tidak dipakai di Linux/Termux)
# export YT_PLAYER_MPV_PORT=12345

# ──────────────────────────────────────────────────────────
#  STARTUP
# ──────────────────────────────────────────────────────────

YTGUI_PORT=${YTGUI_PORT:-8765}

echo -e "\033[1;32m====================================================\033[0m"
echo -e "\033[1;32m          YTGUI Web Server — Starting Up            \033[0m"
echo -e "\033[1;32m====================================================\033[0m"
echo ""
echo "[1/4] Menyiapkan environment variables..."
sleep 1

echo "[2/4] Memeriksa dependensi Python..."
MISSING_DEPS=0
DEPS="aiohttp aiosqlite yt_dlp syncedlyrics structlog prometheus_client opentelemetry"
for dep in $DEPS; do
    if ! python3 -c "import $dep" &> /dev/null; then
        echo -e "      \033[1;31m[GAGAL]\033[0m Modul '$dep' tidak ditemukan."
        MISSING_DEPS=1
    fi
done
if [ $MISSING_DEPS -eq 0 ]; then
    echo -e "      \033[1;32m[OK]\033[0m Semua dependensi Python lengkap."
else
    echo -e "      \033[1;33m[Peringatan]\033[0m Ada dependensi yang belum lengkap!"
    echo -e "      Jalankan: \033[1;37mpip install -r requirements.txt\033[0m"
    sleep 3
fi
sleep 1

echo "[3/4] Memeriksa instalasi MPV..."
if command -v mpv &> /dev/null; then
    MPV_VER=$(mpv --version 2>/dev/null | head -1 | awk '{print $2}')
    echo -e "      \033[1;32m[OK]\033[0m MPV terdeteksi (v${MPV_VER:-?})."
else
    echo -e "      \033[1;33m[Peringatan]\033[0m MPV tidak terdeteksi!"
    echo -e "      Termux : \033[1;37mpkg install mpv\033[0m"
    echo -e "      Debian  : \033[1;37msudo apt install mpv\033[0m"
    echo -e "      Arch    : \033[1;37msudo pacman -S mpv\033[0m"
    sleep 3
fi
sleep 1

echo "[4/4] Merapikan sesi sebelumnya..."

# Matikan proses MPV yang mungkin masih berjalan
if command -v killall &> /dev/null; then
    killall mpv > /dev/null 2>&1
else
    pkill mpv > /dev/null 2>&1
fi

# Bersihkan socket per-room (Fase 3: per-room socket di /tmp/mpv-socket-*)
if [ -d "/tmp" ]; then
    rm -f /tmp/mpv-socket-* 2>/dev/null
fi

# Juga bersihkan socket di BASE_DIR/cache/sockets/ jika ada
SOCKET_DIR="${YT_PLAYER_BASE:-$(dirname "$0")}/cache/sockets"
if [ -d "$SOCKET_DIR" ]; then
    rm -f "$SOCKET_DIR"/*.sock 2>/dev/null
fi

# Bebaskan port jika masih terpakai
if command -v fuser &> /dev/null; then
    fuser -k ${YTGUI_PORT}/tcp > /dev/null 2>&1
elif command -v lsof &> /dev/null; then
    lsof -ti tcp:${YTGUI_PORT} | xargs kill -9 > /dev/null 2>&1
fi
sleep 1

# ──────────────────────────────────────────────────────────
#  INFO PASSWORD ADMIN
# ──────────────────────────────────────────────────────────

PASS_FILE="${YT_PLAYER_BASE:-$(dirname "$0")}/cache/admin_password.txt"
echo ""
echo -e "\033[1;33m[Info Akses Admin]\033[0m"
if [ -n "$YTGUI_ADMIN_PASS" ]; then
    echo "  Password diambil dari environment variable YTGUI_ADMIN_PASS."
elif [ -f "$PASS_FILE" ]; then
    echo "  Password tersimpan di: $PASS_FILE"
    echo "  (Password disimpan dalam format pbkdf2 hash — tidak bisa dibaca langsung)"
else
    echo "  Password baru akan di-generate otomatis saat server pertama kali dijalankan."
    echo "  Cek output server untuk melihat password yang digenerate."
fi
echo "  Username  : ${YTGUI_ADMIN_USER:-admin}"

# ──────────────────────────────────────────────────────────
#  MULAI SERVER
# ──────────────────────────────────────────────────────────

echo ""
echo -e "\033[1;36m====================================================\033[0m"
echo -e "\033[1;36m  Akses Client : http://localhost:${YTGUI_PORT}/\033[0m"
echo -e "\033[1;36m  Akses Admin  : http://localhost:${YTGUI_PORT}/admin\033[0m"
echo -e "\033[1;36m  Health Check : http://localhost:${YTGUI_PORT}/health\033[0m"
echo -e "\033[1;36m  Metrics      : http://localhost:${YTGUI_PORT}/metrics\033[0m"
echo -e "\033[1;36m====================================================\033[0m"
echo ""
sleep 1

python3 main.py
