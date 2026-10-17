# -*- coding: utf-8 -*-
"""
AgyAutoAllow.pyw
================
ဒီဖိုင်ကို double-click လုပ်ရင် console window မပေါ်ဘဲ tray app စတင်မယ်။

uiautomation စတဲ့ library တွေ မရှိတဲ့ Python (ဥပမာ Windows py launcher) နဲ့
ဖွင့်မိရင် အလိုအလျောက် မှန်ကန်တဲ့ Python ကို ရှာပြီး ပြန်ဖွင့်ပေးမယ်။
"""
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# uiautomation ရှိလား စစ် — မရှိရင် မှန်ကန်တဲ့ pythonw ကို ရှာပြီး re-exec
def _has_uia(python_exe: str) -> bool:
    try:
        r = subprocess.run(
            [python_exe, "-c", "import uiautomation, pystray, PIL; print('ok')"],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0 and "ok" in (r.stdout or "")
    except Exception:
        return False

try:
    import uiautomation  # noqa: F401
    import pystray  # noqa: F401
except ImportError:
    # မှန်ကန်တဲ့ pythonw ကို ရှာမယ်
    candidates = []
    # 1. ဒီ script ရှိတဲ့ နေရာနဲ့ တူတဲ့ python
    for base in (os.path.dirname(sys.executable),):
        if base:
            candidates.append(os.path.join(base, "pythonw.exe"))
            candidates.append(os.path.join(base, "python.exe"))
    # 2. လူသုံးများတဲ့ တပ်ဆင်ထားတဲ့ နေရာများ
    la = os.environ.get("LOCALAPPDATA", "")
    if la:
        py_root = os.path.join(la, "Programs", "Python")
        if os.path.isdir(py_root):
            for name in sorted(os.listdir(py_root), reverse=True):
                d = os.path.join(py_root, name)
                if os.path.isdir(d):
                    candidates.append(os.path.join(d, "pythonw.exe"))
    # 3. PATH ထဲက pythonw
    import shutil
    w = shutil.which("pythonw")
    if w:
        candidates.append(w)

    # dedup
    seen = set()
    uniq = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            uniq.append(c)

    chosen = None
    for c in uniq:
        if os.path.isfile(c) and _has_uia(c):
            chosen = c
            break

    if chosen:
        # မှန်ကန်တဲ့ pythonw နဲ့ ဒီ .pyw ကို ပြန် run
        subprocess.Popen([chosen, os.path.abspath(__file__)],
                         cwd=BASE_DIR,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        sys.exit(0)
    else:
        # မရရင် error log ရေးပြီး console mode နဲ့ ပြန်စမ်း
        import datetime, traceback
        err_path = os.path.join(BASE_DIR, "logs", "startup_error.log")
        os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
        with open(err_path, "a", encoding="utf-8") as f:
            f.write("\n=== %s ===\n" % datetime.datetime.now().isoformat())
            f.write("uiautomation ရှိတဲ့ Python မတွေ့ပါ။\n")
            f.write("စစ်ဆေးထားတဲ့ လမ်းကြောင်းများ:\n")
            for c in uniq:
                f.write("  - %s\n" % c)
        # fallback: console mode နဲ့ ပြန်ဖွင့် (error ပြဖို့)
        python_exe = os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                  "Programs", "Python", "Python313", "python.exe")
        if os.path.isfile(python_exe):
            subprocess.Popen([python_exe, os.path.join(BASE_DIR, "agy_auto_allow.py"), "--console"],
                             cwd=BASE_DIR)
        sys.exit(1)

# မှန်ကန်တဲ့ Python နဲ့ ရောက်လာပြီ — app စတင်
import agy_auto_allow  # noqa: E402

sys.argv = ["agy_auto_allow.py"]
sys.exit(agy_auto_allow.main())