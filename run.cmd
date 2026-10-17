@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================================
echo   AgyAutoAllow - Antigravity Auto Allow / Submit
echo ======================================================
echo.
echo [1] Start Tray App (normal usage, no console)
echo [2] Console Mode (view live logs in terminal)
echo [3] Dry-Run Mode (test, no real clicks)
echo [4] Diagnose (check if Antigravity window/buttons found)
echo [5] List Windows
echo [6] Discover Buttons (dump UI elements)
echo [7] Screenshot (for image fallback templates)
echo [8] Install Requirements (pip install)
echo [9] Add to Windows Startup (auto-run on boot)
echo [A] Relaunch Antigravity (with accessibility flag)
echo [0] Exit
echo.
set /p choice="Choose [1]: "
if "%choice%"=="" set choice=1

if /I "%choice%"=="1" (
    echo Starting AgyAutoAllow...
    start "" pythonw "%~dp0AgyAutoAllow.pyw"
    echo Green icon will appear in the system tray (bottom-right).
    timeout /t 3 >nul
    exit /b 0
)
if "%choice%"=="2" python "%~dp0agy_auto_allow.py" --console
if "%choice%"=="3" python "%~dp0agy_auto_allow.py" --no-tray --console --dry-run
if "%choice%"=="4" python "%~dp0agy_auto_allow.py" --diagnose
if "%choice%"=="5" python "%~dp0agy_auto_allow.py" --list-windows
if "%choice%"=="6" python "%~dp0agy_auto_allow.py" --discover --hidden-elements
if "%choice%"=="7" python "%~dp0agy_auto_allow.py" --grab
if "%choice%"=="8" (
    call "%~dp0install_requirements.cmd"
    exit /b 0
)
if "%choice%"=="9" (
    call "%~dp0install_startup.cmd"
    exit /b 0
)
if /I "%choice%"=="A" python "%~dp0agy_auto_allow.py" --relaunch-agy
if "%choice%"=="0" exit /b 0

echo.
pause