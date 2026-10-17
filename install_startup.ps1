# AgyAutoAllow — Startup installer (Windows / PowerShell)
# Windows စတင်တိုင်း AgyAutoAllow ကို နောက်ကွယ်ကနေ အလိုအလျောက် စတင်စေတယ်။

$ErrorActionPreference = "Stop"

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $dir "agy_auto_allow.py"

if (-not (Test-Path $script)) {
    Write-Host "agy_auto_allow.py ကို မတွေ့ပါ: $script" -ForegroundColor Red
    exit 1
}

Write-Host "Python ကို စစ်နေသည်..." -ForegroundColor Cyan
$pythonw = $null
try {
    $pythonw = (& python -c "import sys, os, uiautomation, pystray, PIL; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>$null)
} catch { $pythonw = $null }

if (-not $pythonw -or -not (Test-Path $pythonw)) {
    Write-Host "လိုအပ်တဲ့ package တွေ မရှိပါ သို့မဟုတ် pythonw.exe မတွေ့ပါ။" -ForegroundColor Yellow
    Write-Host "အရင်ဆုံး ဒီ command ကို run ပါ:" -ForegroundColor Yellow
    Write-Host "    python -m pip install -r `"$dir\requirements.txt`""
    exit 1
}

$startup = [Environment]::GetFolderPath('Startup')
$lnkPath = Join-Path $startup "AgyAutoAllow.lnk"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnkPath)
$sc.TargetPath = $pythonw
$sc.Arguments = '"' + $script + '"'
$sc.WorkingDirectory = $dir
$sc.WindowStyle = 7
$sc.Description = "Antigravity Allow/Submit ကို အလိုအလျောက် နှိပ်ပေးတဲ့ tray app"
$sc.Save()

Write-Host "တင်ပြီးပါပြီ: $lnkPath" -ForegroundColor Green
Write-Host "ဖျက်ချင်ရင် uninstall_startup.cmd ကို run ပါ။"
