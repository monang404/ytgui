@echo off
color 0A
title YTGUI Web Server Startup
echo ===================================================
echo             Memulai YTGUI Web Server
echo ===================================================
echo.
echo [1/3] Menyiapkan environment variables...
set YTGUI_HOST=0.0.0.0
set YTGUI_PORT=8765

:: Hilangkan tanda "::" di bawah ini untuk mengunci kredensial admin
:: set YTGUI_ADMIN_USER=admin
:: set YTGUI_ADMIN_PASS=password_rahasia_anda
timeout /t 1 >nul

echo [2/3] Memeriksa dependensi Python...
python -c "import aiohttp, aiosqlite, yt_dlp, syncedlyrics" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo       [Peringatan] Dependensi belum lengkap! Pastikan Anda sudah menjalankan 'pip install -r requirements.txt'.
    timeout /t 2 >nul
) else (
    echo       [OK] Dependensi lengkap.
)
timeout /t 1 >nul

echo [3/3] Memeriksa instalasi MPV...
where mpv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo       [Peringatan] MPV tidak terdeteksi di sistem PATH Anda! Aplikasi mungkin tidak dapat memutar musik.
    timeout /t 2 >nul
) else (
    echo       [OK] MPV terdeteksi.
)
timeout /t 1 >nul

echo.
echo [Merapikan Sesi]
echo Membersihkan Sesi sebelumnya..
taskkill /F /IM mpv.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%YTGUI_PORT%') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [Memulai Server] 
echo Menyiapkan YTGUI (Bagas.FM) . . .
echo.
echo ===================================================
echo  Akses Client : http://localhost:%YTGUI_PORT%/
echo  Akses Admin  : http://localhost:%YTGUI_PORT%/admin
echo ===================================================
timeout /t 1 >nul
python main.py
pause
