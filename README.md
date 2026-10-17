# AgyAutoAllow (noenter-grav) — Antigravity Auto Allow / Submit Tool

[![GitHub](https://img.shields.io/badge/GitHub-uzinlay85%2Fnoenter-grav-blue?logo=github)](https://github.com/uzinlay85/noenter-grav.git)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?logo=windows)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Antigravity** (Google AI coding IDE) တွင် Code များ စမ်းသပ်ချိန်၊ Command များ Run ချိန်၌ AI က ခွင့်ပြုချက် (Permission) တောင်းသည့် **Allow / Submit / Accept / Run / Continue / Yes** စသည့် dialog ခလုတ်များ ပေါ်လာပါက — အခြား App (Browser, Telegram, Editor, Excel စသည်) များကို အသုံးပြုနေစဉ်၌ပင် **နောက်ကွယ် (Background) မှနေ၍ မောက်စ် Focus မခိုးဘဲ အလိုအလျောက် နှိပ်ပေးမည့် ပေါ့ပါးသော Windows System Tray App** ဖြစ်ပါသည်။

---

## ⚡ ထူးခြားချက်များ (Key Features)

* **မောက်စ် Focus မခိုးပါ** — Windows UI Automation (UIA) ရဲ့ `Invoke` pattern ဖြင့် နောက်ကွယ်မှ တိုက်ရိုက် နှိပ်ပေးသောကြောင့် သင် စာရိုက်နေစဉ် Cursor ပြေးသွားခြင်း၊ Focus ပျောက်သွားခြင်း လုံးဝ မဖြစ်ပါ။
* **လုံခြုံရေး Blocklist စနစ်** — `Cancel`, `Reject`, `Deny`, `No`, `Stop`, `Delete`, `Skip` စသည့် ခလုတ်များကို **ဘယ်တော့မှ မနှိပ်** အောင် တားမြစ်ထားပါသည်။
* **ကျဉ်းမြောင်းသော ခွင့်ပြုချက်ကိုသာ ရွေးချယ်ခြင်း** — "Yes, allow this time" နှင့် "Always allow" ရွေးစရာများ ပါလာပါက အန္တရာယ်အကင်းဆုံးဖြစ်သော အပေါ်ဆုံး တစ်ခုတည်းကိုသာ နှိပ်ပါသည်။
* **ပေါ့ပါးပြီး CPU အစားသက်သာခြင်း** — အသုံးမပြုနေချိန် (Idle) တွင် စစ်ဆေးမှုကြာချိန်ကို အလိုအလျောက် လျှော့ချပေးပါသည်။
* **System Tray + Global Hotkeys** — Taskbar tray မှ အဖွင့်/အပိတ် အလွယ်တကူ ပြုလုပ်နိုင်သလို Shortcut Hotkeys များဖြင့်လည်း ထိန်းချုပ်နိုင်ပါသည်။

---

## 📦 ယူရမည့် ဖိုင်များ (Files Included)

ဒီ Tool ကို အသုံးပြုရန် အောက်ပါဖိုင်များ ပါဝင်ပါသည် (တစ်ခုလုံးကို ဒေါင်းလုဒ်ရယူရုံပါပဲ) —

| ဖိုင်အမည် | အသုံးပြုပုံ ရှင်းလင်းချက် |
|---|---|
| 🟢 **`AgyAutoAllow.pyw`** | **အဓိက အသုံးပြုရမည့်ဖိုင်**။ Double-click နှိပ်ရုံဖြင့် Command Prompt မပေါ်ဘဲ Background Tray အနေဖြင့် တိတ်တဆိတ် အလုပ်လုပ်ပါမည်။ |
| ⚙️ **`agy_auto_allow.py`** | Main CLI & Tray Core Script ဖြစ်သည်။ Diagnose, Console, Dry-run စသည့် option များနှင့် စမ်းသပ်နိုင်သည်။ |
| 🧠 **`agycore.py`** | Window ရှာဖွေခြင်း၊ Child window ခွဲခြမ်းစိတ်ဖြာခြင်းနှင့် Button နှိပ်ခြင်းတို့ကို ဆောင်ရွက်ပေးသည့် Automation Engine ဖြစ်သည်။ |
| 📝 **`config.json`** | စိတ်ကြိုက် ပြင်ဆင်နိုင်သော Setting ဖိုင် (ခွင့်ပြုမည့် စာလုံးများ၊ blocklist များ၊ hotkeys များ ပါဝင်သည်)။ |
| 📦 **`requirements.txt`** | Tool အတွက် လိုအပ်သော Python Library များစာရင်း။ |
| ⚡ **`install_requirements.cmd`** | Python library များကို **တစ်ချက်နှိပ်ရုံဖြင့် အလိုအလျောက် Install လုပ်ပေးမည့်ဖိုင်**။ |
| 🚀 **`run.cmd`** | စမ်းသပ်စစ်ဆေးရန်အတွက် Menu ရွေးချယ်စရာများ ပါဝင်သော Launcher Script။ |
| 🔄 **`install_startup.cmd`** | ကွန်ပျူတာ စဖွင့်တိုင်း AgyAutoAllow ကို အလိုအလျောက် ပွင့်စေရန် ထည့်သွင်းပေးသည့်ဖိုင်။ |
| ❌ **`uninstall_startup.cmd`** | Startup ထဲမှ ပြန်လည်ဖယ်ရှားပေးသည့်ဖိုင်။ |
| 📁 **`assets/templates/`** | Image fallback အသုံးပြုလိုသူများအတွက် Template ပုံများ ထည့်သွင်းရန် folder။ |
| 📁 **`logs/`** | လုပ်ဆောင်ချက် မှတ်တမ်းများ သိမ်းဆည်းသည့် folder။ |

---

## 📥 ယူနည်း / Download ရယူနည်း (How to Get / Download)

အောက်ပါ နည်းလမ်း (၂) မျိုးထဲမှ အဆင်ပြေရာ တစ်မျိုးဖြင့် ရယူနိုင်ပါသည် —

### နည်းလမ်း (၁) - Git Clone ဖြင့် ရယူနည်း (အကြံပြုသည်)

Command Prompt သို့မဟုတ် Terminal ကို ဖွင့်ပြီး အောက်ပါ command ကို ရိုက်ထည့်ပါ:

```bash
git clone https://github.com/uzinlay85/noenter-grav.git
cd noenter-grav
```

### နည်းလမ်း (၂) - ZIP ဖိုင်အဖြစ် ဒေါင်းလုဒ် ရယူနည်း

1. GitHub စာမျက်နှာ [https://github.com/uzinlay85/noenter-grav](https://github.com/uzinlay85/noenter-grav.git) သို့ သွားပါ။
2. အပေါ်ညာဘက်ရှိ အစိမ်းရောင် **`<> Code`** ခလုတ်ကို နှိပ်ပါ။
3. ထွက်လာသော menu ထဲမှ **`Download ZIP`** ကို နှိပ်ပြီး ဒေါင်းလုဒ်လုပ်ပါ။
4. ဒေါင်းလုဒ်ရလာသော `noenter-grav-main.zip` ဖိုင်ကို မိမိထားလိုသည့် folder (ဥပမာ `C:\Tools\AgyAutoAllow` သို့မဟုတ် Desktop) ထဲသို့ **Extract (zip ဖြေ)** လိုက်ပါ။

---

## 💻 ကွန်ပျူတာ လိုအပ်ချက်များ (System Requirements)

* **Operating System:** Windows 10 သို့မဟုတ် Windows 11 (64-bit)
* **Python:** Version 3.9 နှင့် အထက် (Python မရှိသေးပါက [python.org](https://www.python.org/downloads/) မှ ဒေါင်းလုဒ်ဆွဲ၍ Install လုပ်ပါ)
  > ⚠️ **သတိပြုရန်:** Python install သည့်အခါ Setup window အောက်ခြေရှိ **"Add python.exe to PATH"** ကို **မဖြစ်မနေ အမှန်ခြစ် ပေးပါ**။
* **Target Application:** Antigravity IDE

---

## 🛠️ တပ်ဆင်နည်းနှင့် စတင်အသုံးပြုနည်း အဆင့်ဆင့် (Step-by-Step Guide)

### အဆင့် (၁) - လိုအပ်သော Library များကို Install လုပ်ခြင်း

Folder ထဲရှိ **`install_requirements.cmd`** ကို Double-Click နှိပ်ပါ။
*(Python library များဖြစ်သော `uiautomation`, `comtypes`, `pillow`, `pystray` များကို အလိုအလျောက် တင်ပေးသွားပါမည်။)*

*(သို့မဟုတ် Command Prompt မှတစ်ဆင့် `pip install -r requirements.txt` ဟု ရိုက်ထည့်နိုင်ပါသည်)*

---

### အဆင့် (၂) - Antigravity Shortcut တွင် Flag ထည့်ခြင်း (အလွန်အရေးကြီးသည် ⚠️)

Antigravity IDE သည် Chromium/Electron framework ကို အခြေခံထားသောကြောင့် default အနေဖြင့် ခလုတ်များ၏ Accessibility tree ကို မဆောက်ပေးတတ်ပါ။ ခလုတ်များကို Tool က ရှာတွေ့နိုင်ရန် အောက်ပါအတိုင်း **တစ်ကြိမ်သာ** ပြင်ဆင်ပေးထားရပါမည် —

1. Desktop ပေါ်ရှိ သို့မဟုတ် Start Menu ထဲရှိ **Antigravity** Shortcut icon ကို **Right-Click** နှိပ်ပါ။
2. **Properties** ကို ရွေးပါ။
3. **Shortcut** tab အောက်ရှိ **Target** အကွက်၏ အဆုံးတွင် space (ကွက်လပ်) တစ်ချက်ခြားပြီး အောက်ပါ စာသားကို ထည့်ပါ:
   ```text
    --force-renderer-accessibility
   ```
   *(ဥပမာ အပြည့်အစုံ - `"C:\Users\YourName\AppData\Local\Programs\Antigravity\Antigravity.exe" --force-renderer-accessibility`)*
4. **Apply** နှိပ်ပြီး **OK** နှိပ်ပါ။
5. Antigravity ကို ပိတ်ပြီး အဆိုပါ Shortcut ဖြင့် အသစ် ပြန်ဖွင့်ပါ။

> 💡 *အကြံပြုချက်:* Antigravity ပွင့်နေစဉ် အမြန် restart လုပ်လိုပါက `run.cmd` ကို run ပြီး သို့မဟုတ် terminal တွင် `python agy_auto_allow.py --relaunch-agy` ဟု run နိုင်ပါသည်။

---

### အဆင့် (၃) - စတင်အသုံးပြုခြင်း (Running the App)

#### 🔹 ပုံမှန် အသုံးပြုနည်း (အကြံပြုသည်)
Folder ထဲရှိ **`AgyAutoAllow.pyw`** ကို Double-Click နှိပ်ပါ။
* ဘာ Window မှ မပေါ်ဘဲ ညာဘက်အောက်ထောင့် Taskbar System Tray ထဲတွင် **အစိမ်းရောင် အမှန်ခြစ် (✓)** icon လေး ပေါ်လာပါမည်။
* ထိုအချိန်မှစ၍ Antigravity တွင် AI က Allow/Submit တောင်းတိုင်း ၁ စက္ကန့်အတွင်း အလိုအလျောက် နှိပ်ပေးသွားပါမည်။

#### 🔹 စမ်းသပ်စစ်ဆေးလိုပါက
Folder ထဲရှိ **`run.cmd`** ကို Double-Click နှိပ်ပါ —
* `[1]` Tray App စတင်မည်
* `[2]` Console Mode (Live Log များကို terminal တွင် ကြည့်မည်)
* `[3]` Dry-Run Mode (တကယ် မနှိပ်ဘဲ စမ်းသပ်မည်)
* `[4]` Diagnose (Antigravity ခလုတ်များကို ရှာတွေ့နိုင်ခြင်း ရှိ/မရှိ စစ်ဆေးမည်)
* `[9]` Windows Startup တွင် ထည့်မည်

---

## ⌨️ Hotkeys နှင့် Tray Icon ထိန်းချုပ်မှုများ

### 🖱️ Tray Icon အသုံးပြုပုံ
* **Left-Click (ဘယ်ကလစ်):** Auto-Allow စနစ်ကို ချက်ချင်း **ON ⇄ OFF** ခလုတ်ဖွင့်/ပိတ် ပြုလုပ်နိုင်သည်။
  * 🟢 အစိမ်းရောင် icon = အလုပ်လုပ်နေသည် (Active)
  * 🔴 အနီရောင် icon = ရပ်နားထားသည် (Paused)
* **Right-Click (ညာကလစ်):** Menu ပွင့်လာပါမည် —
  * Status (အခြေအနေနှင့် နှိပ်ခဲ့သောအကြိမ်အရေအတွက် ကြည့်ခြင်း)
  * Scan Now (ချက်ချင်း ချက်ချင်း scan ဖတ်ခိုင်းခြင်း)
  * Discover Buttons (လက်ရှိခလုတ်များကို dump ထုတ်ခြင်း)
  * Reload Config (setting အပြောင်းအလဲများကို ချက်ချင်း load လုပ်ခြင်း)
  * Open Log (မှတ်တမ်း log ဖိုင်ကို notepad ဖြင့် ဖွင့်ခြင်း)
  * Quit (ပရိုဂရမ်မှ လုံးဝ ထွက်ခြင်း)

### ⌨️ Global Hotkeys (မည်သည့်ဆော့ဖ်ဝဲလ်သုံးနေပါစေ နှိပ်နိုင်သည်)

| Shortcut | လုပ်ဆောင်ချက် |
|---|---|
| `Ctrl + Alt + A` | Auto-Allow **ON ⇄ OFF** ဖွင့်/ပိတ် ပြုလုပ်မည် |
| `Ctrl + Alt + D` | လက်ရှိ Antigravity window ရှိ ခလုတ်များကို Dump လုပ်ပြီး log ထဲ မှတ်တမ်းတင်မည် |
| `Ctrl + Alt + L` | Log မှတ်တမ်းဖိုင်ကို ဖွင့်မည် |
| `Ctrl + Alt + Q` | App ကို လုံးဝ ပိတ်သိမ်းမည် (Quit) |

*(Hotkey များကို `config.json` ထဲတွင် စိတ်ကြိုက် ပြောင်းလဲနိုင်ပါသည်)*

---

## 🔄 Windows စတင်တိုင်း အလိုအလျောက် Run စေရန်

ကွန်ပျူတာ ဖွင့်တိုင်း ကိုယ်တိုင် သွားနှိပ်စရာမလိုဘဲ အလိုအလျောက် ပွင့်စေလိုပါက —
* **ထည့်သွင်းရန်:** **`install_startup.cmd`** ကို double-click နှိပ်ပါ။ (Windows Startup ထဲသို့ shortcut ထည့်ပေးပါမည်)
* **ဖယ်ရှားရန်:** **`uninstall_startup.cmd`** ကို double-click နှိပ်ပါ။

---

## 🛡️ လုံခြုံရေးနှင့် စည်းမျဉ်းများ (Safety Guardrails)

ဒီ tool သည် အောက်ပါ လုံခြုံရေး စည်းမျဉ်းများဖြင့် တည်ဆောက်ထားပါသည်:

1. **သတ်မှတ်ထားသော စာသားများသာ နှိပ်ခြင်း:**
   * ခွင့်ပြုထားသော စာလုံးများ: `allow`, `submit`, `accept`, `run`, `continue`, `yes`, `ok`, `confirm`, `proceed`, `trust`, စသည်တို့ ဖြစ်ပါသည်။
2. **Blocklist တားမြစ်ချက်များ:**
   * `cancel`, `reject`, `deny`, `no`, `stop`, `skip`, `delete`, `discard`, `undo` စသည်တို့ ပါဝင်နေသော မည်သည့်ခလုတ်ကိုမဆို **လုံးဝ (လုံးဝ) မနှိပ်ပါ**။
3. **Antigravity ရဲ့ Dialog များတွင် နှိပ်ပုံ:**
   * ဥပမာ - `Allow running diagnosis script?` ဒိုင်ယာလော့ဂ်တွင်:
     * `1  Yes, allow this time` ➔ **✅ နှိပ်သည်** (အန္တရာယ် အကင်းဆုံးနှင့် အကျဉ်းဆုံး ရွေးချယ်မှု)
     * `2/3/4  Yes, and always allow ...` ➔ **⏸️ မနှိပ်ပါ** (Permission အကျယ်ကြီး မဖြစ်စေရန်)
     * `5  No (tell the agent ...)` ➔ **⛔ Blocklist - မနှိပ်ပါ**
     * `Skip` ➔ **⛔ Blocklist - မနှိပ်ပါ**
     * `Submit` ➔ **✅ နှိပ်သည်**

---

## 🔧 ပြဿနာဖြေရှင်းနည်း (Troubleshooting)

### မေး။ ။ App ကို ဖွင့်ထားသော်လည်း ခလုတ်များကို ရှာမတွေ့ပါ / မနှိပ်ပေးပါ
**ဖြေရှင်းရန်:**
1. Antigravity Shortcut တွင် `--force-renderer-accessibility` flag ထည့်ထားခြင်း ရှိမရှိ စစ်ဆေးပါ။ (အဆင့် ၂ ကို ကြည့်ပါ)
2. `run.cmd` ကို ဖွင့်ပြီး `[4] Diagnose` ဖြင့် စစ်ဆေးကြည့်ပါ။ အကယ်၍ Window တွေ့သော်လည်း Element အရေအတွက် နည်းနေပါက Flag မပါဘဲ ဖွင့်ထားသောကြောင့် ဖြစ်ပါသည်။
3. အမြန်ဆုံး ဖြေရှင်းရန် Terminal တွင် အောက်ပါ command ကို run လိုက်ပါ:
   ```bash
   python agy_auto_allow.py --relaunch-agy
   ```

### မေး။ ။ Antigravity ကို Minimize လုပ်ထားပါက အလုပ်လုပ်ပါသလား
**ဖြေရှင်းရန်:**
* Chromium Engine သည် Minimize ပြုလုပ်ထားသော Window များ၏ UI Render ကို ရပ်ဆိုင်း (Throttle) ထားတတ်သောကြောင့် Default အနေဖြင့် မနှိပ်ပါ။
* Antigravity ကို အခြား App များ (ဥပမာ Browser) ၏ အောက်တွင် ကွယ်နေပါစေ၊ Taskbar ပေါ်တွင် ဖွင့်ထားပေးပါ (Focus ပေးထားရန် မလိုပါ)။

### မေး။ ။ 'python' is not recognized as an internal or external command ဟု ပေါ်နေပါက
**ဖြေရှင်းရန်:**
* Python ကို Install လုပ်စဉ် "Add python.exe to PATH" ကို အမှန်ခြစ် မပေးခဲ့မိသောကြောင့် ဖြစ်ပါသည်။
* Python Installer ကို ပြန် run ပြီး **Modify** ကို နှိပ်၍ **Add Python to environment variables** ကို အမှန်ခြစ် ပေးပါ။

---

## ⚙️ စိတ်ကြိုက် ချိန်ညှိခြင်း (`config.json`)

လိုအပ်ပါက `config.json` ကို Notepad ဖြင့် ဖွင့်၍ အောက်ပါ setting များကို စိတ်ကြိုက် ပြင်ဆင်နိုင်ပါသည်:

```jsonc
{
  "enabled": true,                  // စတင်ချိန်တွင် Auto-Allow ဖွင့်ထားမည်
  "dry_run": false,                 // true ထားပါက တကယ်မနှိပ်ဘဲ log ပဲ ထုတ်မည်
  "prevent_screen_sleep": true,     // ON ဖြစ်နေစဉ် မျက်နှာပြင် sleep မဖြစ်အောင် ထားမည်
  "poll_interval_seconds": 0.5,     // စစ်ဆေးမည့် အကြိမ်နှုန်း (စက္ကန့်)
  "labels": [ ... ],                // ခွင့်ပြုမည့် ခလုတ် စာရင်း
  "block_labels": [ ... ],          // တားမြစ်မည့် ခလုတ် စာရင်း
  "hotkeys": {
    "toggle": "ctrl+alt+a",
    "discover": "ctrl+alt+d",
    "open_log": "ctrl+alt+l",
    "quit": "ctrl+alt+q"
  }
}
```

---

## 📄 License

ဤပရောဂျက်ကို [MIT License](LICENSE) ဖြင့် လွတ်လပ်စွာ အသုံးပြုနိုင်ပါသည်။
Developed for Antigravity AI IDE users.
