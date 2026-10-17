@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================================
echo   AgyAutoAllow - Antigravity Auto Allow / Submit
echo ======================================================
echo.
echo [1] Tray App စတင်မည် (Background / Console မပါ - ပုံမှန်အသုံးပြုနည်း)
echo [2] Console Mode (Live Log များကို Terminal တွင် ကြည့်မည်)
echo [3] Dry-Run Mode (စမ်းသပ်ရန် - တကယ် မနှိပ်ဘဲ log ပဲ ထုတ်မည်)
echo [4] Diagnose (Antigravity window နှင့် ခလုတ်များ ရှာတွေ့လား စစ်ဆေးမည်)
echo [5] List Windows (ဖွင့်ထားသော Antigravity window များကို စာရင်းထုတ်မည်)
echo [6] Discover Buttons (တွေ့သမျှ UI element နှင့် ခလုတ်များကို Dump လုပ်မည်)
echo [7] Screenshot ရိုက်မည် (Image Fallback Template အတွက်)
echo [8] Install Requirements (လိုအပ်သော Library များကို Install လုပ်မည်)
echo [9] Windows Startup တွင် ထည့်မည် (ကွန်ပျူတာဖွင့်တိုင်း အလိုအလျောက် run)
echo [0] ထွက်မည် (Exit)
echo.
set /p choice="နံပါတ်တစ်ခု ရွေးပါ [1]: "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo AgyAutoAllow ကို စတင်နေပါသည်...
    start "" pythonw "%~dp0AgyAutoAllow.pyw"
    echo ညာဘက် Taskbar System Tray ထဲတွင် အစိမ်းရောင် icon ပေါ်လာပါမည်။
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
if "%choice%"=="0" exit /b 0

echo.
pause