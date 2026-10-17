@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================================
echo   AgyAutoAllow - Dependencies Installer
echo ======================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python ကို ရှာမတွေ့ပါ။
    echo 1. Python 3.9 သို့မဟုတ် အထက်ကို https://www.python.org/downloads/ မှ ဒေါင်းလုဒ်ရယူပါ။
    echo 2. Install လုပ်ရာတွင် "Add python.exe to PATH" ကို မဖြစ်မနေ အမှန်ခြစ် ပေးပါ။
    echo.
    pause
    exit /b 1
)

echo Python တွေ့ရှိပါသည်။ လိုအပ်သော package များကို install လုပ်နေပါသည်...
python -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Package များ install လုပ်ရာတွင် အမှားတစ်ခု ဖြစ်ပေါ်ခဲ့သည်။
    echo အင်တာနက်လိုင်း စစ်ဆေးပြီး ပြန်လည် ကြိုးစားကြည့်ပါ။
    pause
    exit /b 1
)

echo.
echo ======================================================
echo [SUCCESS] Package များ အောင်မြင်စွာ တပ်ဆင်ပြီးပါပြီ!
echo.
echo - ပုံမှန်သုံးရန်: AgyAutoAllow.pyw ကို double-click နှိပ်ပါ (Tray တွင် စတင်မည်)
echo - Menu ဖြင့် စမ်းသပ်ရန်: run.cmd ကို run ပါ
echo ======================================================
echo.
pause
