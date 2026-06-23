@echo off
chcp 65001 > nul
color 0A
title YTGUI Web Server Startup
echo ====================================================
echo           YTGUI Web Server -- Starting Up
echo ====================================================
echo.

:: ──────────────────────────────────────────────────────────
::  KONFIGURASI — Hilangkan "::" di depan baris untuk mengaktifkan
:: ──────────────────────────────────────────────────────────

set YTGUI_HOST=0.0.0.0
set YTGUI_PORT=8765

:: Direktori kerja (default: folder script ini berada)
:: set YT_PLAYER_BASE=C:\ytgui

:: Kredensial admin
:: Jika tidak di-set, password akan digenerate otomatis dan disimpan di cache\admin_password.txt
:: Jika di-set, password akan di-hash otomatis saat startup (tidak perlu hash manual)
:: set YTGUI_ADMIN_USER=admin
:: set YTGUI_ADMIN_PASS=password_rahasia_anda

:: Token opsional untuk akses endpoint /metrics dari luar localhost
:: Jika tidak di-set, /metrics hanya bisa diakses dari 127.0.0.1
:: set YTGUI_METRICS_TOKEN=token_rahasia_metrics

:: Port TCP untuk MPV di Windows (digunakan karena Windows tidak support Unix socket)
:: set YT_PLAYER_MPV_PORT=12345

:: ──────────────────────────────────────────────────────────
::  STARTUP
:: ──────────────────────────────────────────────────────────

echo [1/4] Menyiapkan environment variables...
timeout /t 1 > nul

echo [2/4] Memeriksa dependensi Python...
set DEPS_OK=1
for %%m in (aiohttp aiosqlite yt_dlp syncedlyrics structlog prometheus_client opentelemetry) do (
    python -c "import %%m" > nul 2>&1
    if errorlevel 1 (
        echo       [GAGAL] Modul '%%m' tidak ditemukan.
        set DEPS_OK=0
    )
)
if "%DEPS_OK%"=="1" (
    echo       [OK] Semua dependensi Python lengkap.
) else (
    echo       [Peringatan] Ada dependensi yang belum lengkap!
    echo       Jalankan: pip install -r requirements.txt
    timeout /t 3 > nul
)
timeout /t 1 > nul

echo [3/4] Memeriksa instalasi MPV...
where mpv > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo       [Peringatan] MPV tidak terdeteksi di PATH!
    echo       Download dari: https://mpv.io/installation/
    echo       Lalu tambahkan mpv.exe ke PATH sistem.
    timeout /t 3 > nul
) else (
    echo       [OK] MPV terdeteksi.
)
timeout /t 1 > nul

echo [4/4] Merapikan sesi sebelumnya...
:: Matikan instance MPV yang mungkin masih berjalan dari sesi sebelumnya
taskkill /F /IM mpv.exe > nul 2>&1

:: Bebaskan port jika masih terpakai
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R ":%YTGUI_PORT% " 2^>nul') do (
    taskkill /F /PID %%a > nul 2>&1
)
timeout /t 1 > nul

:: ──────────────────────────────────────────────────────────
::  INFO PASSWORD ADMIN
:: ──────────────────────────────────────────────────────────

echo.
echo [Info Akses Admin]
if defined YTGUI_ADMIN_PASS (
    echo   Password diambil dari environment variable YTGUI_ADMIN_PASS.
) else (
    if exist "cache\admin_password.txt" (
        echo   Password tersimpan di: cache\admin_password.txt
        echo   (Format pbkdf2 hash -- tidak bisa dibaca langsung)
    ) else (
        echo   Password baru akan di-generate otomatis saat server pertama dijalankan.
        echo   Cek output server untuk melihat password yang digenerate.
    )
)
if defined YTGUI_ADMIN_USER (
    echo   Username  : %YTGUI_ADMIN_USER%
) else (
    echo   Username  : admin
)

:: ──────────────────────────────────────────────────────────
::  MULAI SERVER
:: ──────────────────────────────────────────────────────────

echo.
echo ====================================================
echo  Akses Client : http://localhost:%YTGUI_PORT%/
echo  Akses Admin  : http://localhost:%YTGUI_PORT%/admin
echo  Health Check : http://localhost:%YTGUI_PORT%/health
echo  Metrics      : http://localhost:%YTGUI_PORT%/metrics
echo ====================================================
echo.
timeout /t 1 > nul

python main.py
echo.
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Server berhenti dengan error. Kode: %ERRORLEVEL%
    echo Cek ytplayer.log untuk detail.
)
pause
