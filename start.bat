@echo off
color 0B

echo.
echo    __   __ _____  ____  _   _  _____    _____  __  __
echo    \ \ / / ^|_   _^|/ ___^|^| ^| ^| ^|^|_   _^|  ^|  ___^|^|  \/  ^|
echo     \ V /   ^| ^|  ^| ^|  _ ^| ^| ^| ^|  ^| ^|    ^| ^|_   ^| ^|\/^| ^|
echo      ^| ^|    ^| ^|  ^| ^|_^| ^|^| ^|_^| ^|  ^| ^|    ^|  _^|  ^| ^|  ^| ^|
echo      ^|_^|    ^|_^|   \____^| \___/   ^|_^|    ^|_^|    ^|_^|  ^|_^|
echo.
echo    ================================================================
echo                      YTGUI Web Server Startup
echo    ================================================================
echo.

:: ----------------------------------------------------------
::  CONFIGURATION
:: ----------------------------------------------------------
set "YTGUI_HOST=0.0.0.0"
set "YTGUI_PORT=8765"

:: Admin credentials (uncomment to set explicitly)
:: set "YTGUI_ADMIN_USER=admin"
:: set "YTGUI_ADMIN_PASS=your_secret_password"

:: ----------------------------------------------------------
::  STARTUP SEQUENCE
:: ----------------------------------------------------------

echo  [*] Initializing Environment Variables...
ping 127.0.0.1 -n 2 > nul

echo  [*] Checking Python Dependencies...
set "DEPS_OK=1"
for %%m in (aiohttp aiosqlite yt_dlp syncedlyrics structlog prometheus_client opentelemetry) do (
    python -c "import %%m" > nul 2>&1
    if errorlevel 1 (
        echo      [-] Missing module: %%m
        set "DEPS_OK=0"
    )
)

if "%DEPS_OK%"=="1" (
    echo      [+] All Python dependencies are satisfied.
) else (
    echo.
    echo  [!] WARNING: Some dependencies are missing.
    echo      Please run: pip install -r requirements.txt
    echo.
    ping 127.0.0.1 -n 4 > nul
)

echo  [*] Verifying MPV Installation...
where mpv > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo      [-] MPV not found in system PATH.
    echo          Download from: https://mpv.io/installation/
    echo          Then add mpv.exe to your system PATH.
    echo.
    ping 127.0.0.1 -n 4 > nul
) else (
    echo      [+] MPV detected.
)

echo  [*] Cleaning Up Previous Sessions...
taskkill /F /IM mpv.exe > nul 2>&1
powershell -Command "Get-Process -Id (Get-NetTCPConnection -LocalPort %YTGUI_PORT% -ErrorAction SilentlyContinue).OwningProcess -ErrorAction SilentlyContinue | Stop-Process -Force" > nul 2>&1

:: ----------------------------------------------------------
::  ADMIN ACCESS INFO
:: ----------------------------------------------------------
echo.
echo  ----------------------------------------------------------------
echo   Admin Access Information
echo  ----------------------------------------------------------------
if defined YTGUI_ADMIN_PASS (
    echo   [i] Password loaded from environment variable YTGUI_ADMIN_PASS.
) else (
    if exist "cache\admin_password.txt" (
        echo   [i] Password stored securely in: cache\admin_password.txt
    ) else (
        echo   [i] A new password will be auto-generated on first launch.
    )
)
if defined YTGUI_ADMIN_USER (
    echo   [i] Username: %YTGUI_ADMIN_USER%
) else (
    echo   [i] Username: admin
)

:: ----------------------------------------------------------
::  SERVER STARTUP
:: ----------------------------------------------------------
echo.
echo    ================================================================
echo       Client Interface : http://localhost:%YTGUI_PORT%/
echo       Admin Interface  : http://localhost:%YTGUI_PORT%/admin
echo       System Health    : http://localhost:%YTGUI_PORT%/health
echo       Metrics          : http://localhost:%YTGUI_PORT%/metrics
echo    ================================================================
echo.
echo  [*] Starting Server...
ping 127.0.0.1 -n 2 > nul

python main.py
echo.
if %ERRORLEVEL% neq 0 (
    echo  [X] Server terminated with error code: %ERRORLEVEL%
    echo      Please check the application logs for details.
)
pause
