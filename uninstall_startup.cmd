@echo off
chcp 65001 >nul
echo ======================================================
echo   AgyAutoAllow - Windows Startup မှ ဖယ်ရှားခြင်း
echo ======================================================
echo.
set "LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AgyAutoAllow.lnk"
if exist "%LNK%" (
    del "%LNK%"
    echo [OK] Windows Startup ထဲမှ AgyAutoAllow shortcut ကို အောင်မြင်စွာ ဖယ်ရှားပြီးပါပြီ။
) else (
    echo [INFO] Startup folder ထဲတွင် AgyAutoAllow shortcut မရှိပါ။
)
echo.
pause
