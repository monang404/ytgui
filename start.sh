#!/usr/bin/env bash
# yt-termux-player-pro startup script untuk Linux / Termux

export YTGUI_HOST="0.0.0.0"
export YTGUI_PORT=8765

# Uncomment baris di bawah ini untuk mengunci kredensial admin
# Jika dibiarkan terkunci, sistem akan men-generate password otomatis secara aman (di-hash)
# export YTGUI_ADMIN_USER="admin"
# export YTGUI_ADMIN_PASS="password_rahasia_anda"

echo -e "\033[1;32m===================================================\033[0m"
echo -e "\033[1;32m            Memulai YTGUI Web Server               \033[0m"
echo -e "\033[1;32m===================================================\033[0m"
echo ""
echo "[1/3] Menyiapkan environment variables..."
sleep 1

echo "[2/3] Memeriksa dependensi Python..."
if python3 -c "import aiohttp, aiosqlite, yt_dlp, syncedlyrics, structlog" &> /dev/null; then
    echo -e "      \033[1;32m[OK]\033[0m Dependensi lengkap."
else
    echo -e "      \033[1;33m[Peringatan]\033[0m Dependensi belum lengkap! Sebaiknya jalankan 'pip install -r requirements.txt'."
    sleep 2
fi
sleep 1

echo "[3/3] Memeriksa instalasi MPV..."
if command -v mpv &> /dev/null; then
    echo -e "      \033[1;32m[OK]\033[0m MPV terdeteksi."
else
    echo -e "      \033[1;33m[Peringatan]\033[0m MPV tidak terdeteksi! Jalankan 'pkg install mpv' di Termux."
    sleep 2
fi
sleep 1

echo ""
echo "[Merapikan Sesi]"
echo "Mencari server lama yang mungkin masih berjalan..."
if command -v killall &> /dev/null; then
    killall mpv >/dev/null 2>&1
else
    pkill mpv >/dev/null 2>&1
fi

if command -v fuser &> /dev/null; then
    fuser -k ${YTGUI_PORT}/tcp >/dev/null 2>&1
else
    if command -v lsof &> /dev/null; then
        lsof -ti tcp:${YTGUI_PORT} | xargs kill -9 >/dev/null 2>&1
    fi
fi
sleep 1

echo ""
echo "[Memulai Server]"
echo "Menyiapkan YTGUI (Bagas.FM) . . ."
echo ""
echo -e "\033[1;36m===================================================\033[0m"
echo -e "\033[1;36m  Akses Client : http://localhost:${YTGUI_PORT}/\033[0m"
echo -e "\033[1;36m  Akses Admin  : http://localhost:${YTGUI_PORT}/admin\033[0m"
echo -e "\033[1;36m===================================================\033[0m"
sleep 1

python main.py
