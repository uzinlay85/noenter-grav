# -*- coding: utf-8 -*-
"""
AgyAutoAllow — Antigravity Auto Allow / Submit
==============================================

Antigravity (AI coding IDE) မှာ AI က permission တောင်းတဲ့ Allow/Submit/Accept ...
button တွေ ပေါ်လာရင် app တခြားတွေ သုံးနေရင်းက နောက်ကွယ်ကနေ
အလိုအလျောက် နှိပ်ပေးတဲ့ ပေါ့ပါးတဲ့ tray app။

အသုံး
  python agy_auto_allow.py                # tray app (ပုံမှန်)
  python agy_auto_allow.py --console      # log ကို terminal မှာပါ ပြ
  python agy_auto_allow.py --no-tray      # tray မပါဘဲ console ပဲ
  python agy_auto_allow.py --discover     # လက်ရှိ button တွေကို dump (debug)
  python agy_auto_allow.py --list-windows # target window တွေကို ပြ
  python agy_auto_allow.py --grab         # Antigravity screenshot ရိုက် (image fallback အတွက်)
  python agy_auto_allow.py --dry-run      # တကယ် မနှိပ်ဘဲ စမ်း
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import agycore as core  # noqa: E402

APP_NAME = "AgyAutoAllow"
WM_HOTKEY = 0x0312


# --------------------------------------------------------------------------
# Tray
# --------------------------------------------------------------------------
class TrayApp:
    def __init__(self, engine: "core.Engine", logger, config_file: Path,
                 hotkey_manager: Optional["core.HotkeyManager"] = None):
        self.engine = engine
        self.log = logger
        self.config_file = config_file
        self.hotkeys = hotkey_manager
        self.icon = None
        self._last_notify = 0.0
        self._notify_lock = threading.Lock()
        self._a11y_state: Dict[str, Any] = {}
        self.engine.on_event = self._on_engine_event

    # -------------------------------------------------- icon
    def _image(self, enabled: bool):
        from PIL import Image, ImageDraw

        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        if enabled:
            draw.ellipse((1, 1, size - 2, size - 2), fill=(34, 154, 73, 255))
            draw.line([(16, 33), (27, 45), (48, 19)], fill=(255, 255, 255, 255), width=8, joint="curve")
        else:
            draw.ellipse((1, 1, size - 2, size - 2), fill=(140, 140, 140, 255))
            draw.rectangle((20, 18, 27, 46), fill=(255, 255, 255, 255))
            draw.rectangle((37, 18, 44, 46), fill=(255, 255, 255, 255))
        return img

    def _menu(self):
        import pystray

        engine = self.engine
        stats = engine.stats
        last = stats.get("last_label")
        last_line = ("Last: %s (%.0fs ago)" % (last, time.time() - (stats.get("last_time_ts") or time.time()))
                     if last else "Last: —")
        hotkey_text = ""
        if self.hotkeys:
            hotkey_text = "  ".join(
                "%s=%s" % (name, spec)
                for name, (spec, _action) in self.hotkeys.bindings.items()
            )

        items = [
            pystray.MenuItem(
                lambda item: ("Auto-Allow: ON  ✔" if engine.enabled else "Auto-Allow: OFF"),
                self.on_toggle, default=True,
            ),
            pystray.MenuItem(lambda item: "Status: %s" % engine.status[:70], None, enabled=False),
            pystray.MenuItem(
                lambda item: "Clicks: %d this run / %d total   (poll %ss, scan %sms)" % (
                    stats.get("clicks_this_run", 0), stats.get("clicks_total", 0),
                    stats.get("poll_interval"), stats.get("last_scan_ms")),
                None, enabled=False,
            ),
            pystray.MenuItem(lambda item: last_line, None, enabled=False),
            pystray.MenuItem(lambda item: "dry-run: %s" % ("YES" if engine.dry_run else "no"), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Scan now", self.on_scan),
            pystray.MenuItem("Discover buttons now (log)", self.on_discover),
            pystray.MenuItem("Reload config", self.on_reload),
            pystray.MenuItem("Open log file", self.on_open_log),
            pystray.MenuItem("Open config.json", self.on_open_config),
        ]
        if hotkey_text:
            items.append(pystray.Menu.SEPARATOR)
            items.append(pystray.MenuItem("Hotkeys: " + hotkey_text, None, enabled=False))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self.on_quit))
        return pystray.Menu(*items)

    # -------------------------------------------------- notifications
    def notify(self, message: str, title: str = APP_NAME, force: bool = False) -> None:
        if self.icon is None:
            return
        cfg = self.engine.cfg
        min_gap = float(cfg.get("notify_min_seconds", 4.0))
        with self._notify_lock:
            now = time.time()
            if not force and now - self._last_notify < min_gap:
                return
            self._last_notify = now
        try:
            self.icon.notify(message, title)
        except Exception as exc:
            self.log.debug("notify မအောင်မြင်ပါ: %s", exc)

    def _refresh(self) -> None:
        if self.icon is None:
            return
        try:
            self.icon.icon = self._image(self.engine.enabled)
            self.icon.title = "%s — %s" % (APP_NAME, "ON" if self.engine.enabled else "OFF")
            self.icon.update_menu()
        except Exception:
            pass

    # -------------------------------------------------- engine events
    def _on_engine_event(self, kind: str, payload: Dict[str, Any]) -> None:
        if kind == "click":
            self.engine.stats["last_time_ts"] = time.time()
            candidate = payload.get("candidate")
            result = payload.get("result")
            if self.engine.cfg.get("notify_on_click", True) and candidate is not None:
                self.notify("နှိပ်လိုက်တယ်: %s\n(%s)" % (candidate.name, result.method))
        elif kind == "a11y_empty":
            handle_a11y_empty(
                self.engine.cfg, self.log, payload, self._a11y_state,
                notify=lambda message: self.notify(message, force=True),
            )
        self._refresh()

    # -------------------------------------------------- menu actions
    def on_toggle(self, icon=None, item=None):
        value = self.engine.toggle()
        self.notify("Auto-Allow %s" % ("ON — နောက်ကွယ်ကနေ နှိပ်ပေးမယ်" if value else "OFF — ရပ်ထားတယ်"),
                    force=True)
        self._refresh()

    def on_scan(self, icon=None, item=None):
        def work():
            try:
                results = self.engine.post(lambda: self.engine.tick())
                self.log.info("scan now: %d action", len(results or []))
                self.notify("Scan ပြီး — %d action" % len(results or []), force=True)
            except Exception as exc:
                self.log.exception("scan now error: %s", exc)
            self._refresh()
        threading.Thread(target=work, name="scan-now", daemon=True).start()

    def on_discover(self, icon=None, item=None):
        def work():
            try:
                report = self.engine.post(
                    lambda: self.engine.discover(save_dir=BASE_DIR / "logs"), timeout=60.0)
                total = sum(len(w.get("elements", [])) for w in report["windows"])
                matched = [
                    row for w in report["windows"] for row in w.get("elements", [])
                    if row.get("matched_label")
                ]
                self.log.info("discover: window %d, element %d, matched %d -> %s",
                              len(report["windows"]), total, len(matched), report.get("saved_to"))
                self.notify("Discover ပြီး — element %d, match %d\n%s"
                            % (total, len(matched), report.get("saved_to", "")), force=True)
            except Exception as exc:
                self.log.exception("discover error: %s", exc)
                self.notify("Discover မအောင်မြင်ပါ: %s" % exc, force=True)
        threading.Thread(target=work, name="discover", daemon=True).start()

    def on_reload(self, icon=None, item=None):
        try:
            cfg = core.load_config(str(self.config_file))
            self.engine.cfg = cfg
            self.engine.dry_run = bool(cfg.get("dry_run", False))
            self.engine.enabled = bool(cfg.get("enabled", True))
            self.engine.rebuild_condition()
            self.engine._templates = None
            self.log.info("config ပြန်တင်ပြီး: %s", self.config_file)
            self.notify("Config ပြန်တင်ပြီး", force=True)
        except Exception as exc:
            self.log.exception("config reload error: %s", exc)
            self.notify("Config မတင်နိုင်ပါ: %s" % exc, force=True)
        self._refresh()

    def on_open_log(self, icon=None, item=None):
        path = core.resolve_path(str(self.engine.cfg.get("log_file", "logs/agy_auto_allow.log")))
        self._open(path)

    def on_open_config(self, icon=None, item=None):
        self._open(self.config_file)

    def _open(self, path: Path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
            os.startfile(str(path))  # noqa: S606
        except Exception as exc:
            self.log.warning("ဖိုင်ဖွင့်လို့မရပါ %s: %s", path, exc)

    def on_quit(self, icon=None, item=None):
        self.log.info("ထွက်နေသည်...")
        self.engine.request_stop()
        if self.hotkeys:
            self.hotkeys.stop()
        if self.icon is not None:
            self.icon.stop()

    # -------------------------------------------------- run
    def run(self) -> None:
        import pystray

        engine_thread = threading.Thread(target=self.engine.run_forever, name="engine", daemon=True)
        engine_thread.start()

        self.icon = pystray.Icon(
            APP_NAME,
            icon=self._image(self.engine.enabled),
            title="%s — %s" % (APP_NAME, "ON" if self.engine.enabled else "OFF"),
            menu=self._menu(),
        )
        self.log.info("Tray app စတင်ပြီး (right-click = menu, left-click = ON/OFF)")
        self.icon.run()


# --------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------
def print_windows(engine: "core.Engine") -> None:
    windows, total = engine.find_windows()
    print("Top-level window %d ခု စစ်ပြီး — target %d ခု တွေ့တယ်" % (total, len(windows)))
    for window in windows:
        try:
            hwnd = int(window.NativeWindowHandle or 0)
            minimized = bool(hwnd and ctypes.windll.user32.IsIconic(hwnd))
            print("  * %r  pid=%s hwnd=%s minimized=%s class=%r"
                  % (window.Name, window.ProcessId, hwnd, minimized, window.ClassName))
        except Exception as exc:
            print("  * (ဖတ်လို့မရပါ: %s)" % exc)
    if not windows:
        print("\n  Antigravity ကို ဖွင့်ထားပြီး window ကို minimize မလုပ်ထားပါနဲ့။")
        print("  process_names =", engine.cfg.get("process_names"))


def print_discover(engine: "core.Engine", save: bool = True, show_all: bool = True) -> None:
    report = engine.discover(save_dir=(BASE_DIR / "logs") if save else None)
    print("=" * 72)
    print("AgyAutoAllow discover — %s" % report["timestamp"])
    print("=" * 72)
    if not report["windows"]:
        print("Antigravity window မတွေ့ပါ (top-level %d ခု ရှိတယ်)" % report["top_level_windows_seen"])
        print("→ Antigravity ကို ဖွင့်ထားပြီး minimize မလုပ်ထားပါနဲ့။")
    for window in report["windows"]:
        elements = window.get("elements", [])
        print("\nWINDOW: %r  pid=%s hwnd=%s minimized=%s  (element %d)"
              % (window["title"], window["pid"], window["hwnd"], window["minimized"], len(elements)))
        roots = window.get("roots", [])
        if roots:
            summary = ", ".join(
                "%s:%s" % (r.get("class") or "?", r.get("elements", r.get("error", "?")))
                for r in roots
            )
            print("  root %d ခု — %s" % (len(roots), summary))
        matched = [row for row in elements if row.get("matched_label")]
        if matched:
            print("  ✔ match ဖြစ်တဲ့ button တွေ (ဒါတွေကို နှိပ်မယ်) —")
            for row in matched:
                print("     - %-32r %-18s rect=%s label=%r"
                      % (row["name"], row["type"], row["rect"], row["matched_label"]))
        else:
            print("  match ဖြစ်တဲ့ button မတွေ့ပါ။")
        blocked = [row for row in elements if row.get("blocked_by")]
        if blocked:
            print("  ⛔ blocklist နဲ့ တားထားတာတွေ —")
            for row in blocked:
                print("     - %-32r (%s)" % (row["name"], row["blocked_by"]))
        if show_all:
            print("  element အားလုံး —")
            for row in elements:
                if row.get("matched_label") or row.get("blocked_by"):
                    continue
                print("     · %-40r %-18s rect=%s enabled=%s offscreen=%s"
                      % (row["name"], row["type"], row["rect"], row["enabled"], row["offscreen"]))
    if report.get("saved_to"):
        print("\nအပြည့်အစုံ: %s" % report["saved_to"])
    print("\nမှတ်ချက်: element စာရင်း လုံးလုံး ဗလာဖြစ်နေရင် Antigravity ကို")
    print("  --force-renderer-accessibility flag နဲ့ ပြန်ဖွင့်ကြည့်ပါ (README ထဲမှာ ရှင်းပြထားတယ်)။")


def do_grab(engine: "core.Engine") -> None:
    try:
        from PIL import ImageGrab
    except Exception as exc:
        print("Pillow မရှိပါ: %s" % exc)
        return
    windows, _ = engine.find_windows()
    if not windows:
        print("Antigravity window မတွေ့ပါ - minimize မလုပ်ထားပါနဲ့။")
        return
    out_dir = BASE_DIR / "assets" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, window in enumerate(windows):
        hwnd = int(window.NativeWindowHandle or 0)
        rect = (0, 0, 0, 0)
        try:
            rect_obj = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect_obj))
            rect = (rect_obj.left, rect_obj.top, rect_obj.right, rect_obj.bottom)
        except Exception:
            pass
        if rect[2] - rect[0] <= 0:
            continue
        try:
            image = ImageGrab.grab(bbox=rect, all_screens=True)
        except Exception as exc:
            print("screenshot ရိုက်လို့မရပါ: %s" % exc)
            continue
        path = out_dir / ("antigravity_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
        image.save(path)
        print("screenshot: %s  (%dx%d)" % (path, image.width, image.height))
    print("\nဒီပုံကို Paint နဲ့ဖွင့်ပြီး Allow/Submit button ကို ဖြတ်(crop)ကာ")
    print("assets\\templates\\allow.png စသဖြင့် သိမ်းထားရင် image fallback သုံးလို့ရတယ်။")


def run_console(engine: "core.Engine", logger) -> None:
    a11y_state: Dict[str, Any] = {}

    def on_event(kind: str, payload: Dict[str, Any]) -> None:
        if kind == "a11y_empty":
            handle_a11y_empty(
                engine.cfg, logger, payload, a11y_state,
                notify=lambda message: print("\n[!] %s" % message),
            )
        else:
            logger.info("event: %s", kind)

    engine.on_event = on_event
    thread = threading.Thread(target=engine.run_forever, name="engine", daemon=True)
    thread.start()
    print("AgyAutoAllow console mode — ရပ်ချင်ရင် Ctrl+C")
    print("  enabled=%s  dry_run=%s  click_mode=%s  poll=%.2fs"
          % (engine.enabled, engine.dry_run, engine.cfg.get("click_mode"),
             engine.cfg.get("poll_interval_seconds")))
    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nရပ်နေသည်...")
    finally:
        engine.request_stop()
        thread.join(timeout=3)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def relaunch_antigravity(flags=None, logger=None, wait_seconds: float = 5.0,
                         quiet: bool = False) -> int:
    """Antigravity ကို --force-renderer-accessibility flag နဲ့ ပြန်ဖွင့်တယ်။

    Chromium/Electron က accessibility tree ကို လိုအပ်မှ ဆောက်တာမို့ တချို့စက်တွေမှာ
    ဒီ flag မပါဘဲ Allow/Submit button တွေ UI Automation မှာ မပေါ်တတ်ဘူး။
    wait_seconds=0 ဆိုရင် အရင် စောင့်တဲ့ countdown ကို ကျော်တယ် (auto mode အတွက်)။
    """
    exe = None
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Antigravity", "Antigravity.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Antigravity", "Antigravity.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            exe = candidate
            break

    def say(message: str) -> None:
        if not quiet:
            print(message)
        if logger:
            logger.info("[relaunch] %s", message)

    if not exe:
        say("Antigravity.exe ကို မတွေ့ပါ။ ဒီလမ်းကြောင်းတွေမှာ ရှာကြည့်ပါ:")
        for candidate in candidates:
            say("    " + candidate)
        return 1

    flags = flags or ["--force-renderer-accessibility"]
    say("Antigravity: %s" % exe)
    say("ပိတ်ပြီး ဒီ flag နဲ့ ပြန်ဖွင့်မယ်: %s" % " ".join(flags))
    if wait_seconds and wait_seconds > 0:
        say("⚠️  သိမ်းမထားတဲ့ စာရှိရင် အခုပဲ သိမ်းပါ။ %d စက္ကန့်အတွင်း Ctrl+C = ပယ်ဖျက်"
            % int(wait_seconds))
        try:
            for remaining in range(int(wait_seconds), 0, -1):
                if not quiet:
                    print("   စတင်ဖို့ %d..." % remaining, end="\r", flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            say("ပယ်ဖျက်လိုက်တယ်။")
            return 1
    try:
        result = subprocess.run(["taskkill", "/IM", "Antigravity.exe", "/F"],
                                capture_output=True, text=True)
        if logger:
            logger.info("taskkill rc=%s %s", result.returncode, (result.stdout or "").strip()[:200])
        time.sleep(2.0)
        subprocess.Popen([exe] + list(flags))
        say("ပြန်ဖွင့်ပြီးပါပြီ (accessibility ဖွင့်ထားတယ်)။")
        say("Antigravity ပေါ်လာတဲ့အခါ:  python agy_auto_allow.py --discover --hidden-elements")
        return 0
    except Exception as exc:
        say("ပြန်ဖွင့်လို့မရပါ: %s" % exc)
        return 1


def handle_a11y_empty(cfg: Dict[str, Any], logger, payload: Dict[str, Any],
                      state: Dict[str, Any], notify=None) -> None:
    """Antigravity UI tree ဗလာဖြစ်နေတဲ့အခါ — သတိပေးပြီး (လိုရင်) ပြန်ဖွင့်တယ်။"""
    elements = payload.get("elements")
    logger.warning(
        "Antigravity UI Automation tree မှာ element %s ခုပဲ — "
        "`--force-renderer-accessibility` မပါဘဲ ဖွင့်ထားလို့ ဖြစ်နိုင်တယ် "
        "(runtime nudge=%s)", elements, payload.get("nudged"))
    message = ("Antigravity UI ကို မမြင်ရပါ (element %s)။\n"
               "သိမ်းပြီး `--relaunch-agy` နဲ့ flag နဲ့ ပြန်ဖွင့်ပါ။" % elements)
    if notify is not None:
        try:
            notify(message)
        except Exception:
            pass

    if not cfg.get("auto_relaunch_on_empty", False):
        return
    now = time.time()
    cooldown = float(cfg.get("auto_relaunch_cooldown_seconds", 180.0))
    if now - float(state.get("last_relaunch", 0.0)) < cooldown:
        logger.info("auto relaunch ကို cooldown ကြောင့် ကျော်လိုက်တယ် (%.0fs)", cooldown)
        return
    state["last_relaunch"] = now

    def work():
        logger.info("Antigravity ကို accessibility flag နဲ့ အလိုအလျောက် ပြန်ဖွင့်မယ်")
        try:
            relaunch_antigravity(logger=logger, wait_seconds=0.0, quiet=True)
        except Exception as exc:
            logger.exception("auto relaunch error: %s", exc)

    threading.Thread(target=work, name="auto-relaunch", daemon=True).start()


def run_diagnose(cfg: Dict[str, Any], logger) -> int:
    """Antigravity ကို တကယ် ရှာတွေ့လား + content ပေါ်လား ဆိုတာ တစ်ခါတည်း စစ်ပြီး
    သုံးစွဲသူကို ရိုးရှင်းတဲ့ အဖြေ (✅/❌ + နောက်လုပ်ရမယ့် အဆင့်) ပေးတယ်။"""
    print("=" * 60)
    print("  AgyAutoAllow စစ်ဆေးမှု")
    print("=" * 60)

    engine = core.Engine(cfg, logger)
    windows, total = engine.find_windows()
    print("\n[1] Top-level window စစ်")
    print("    မြင်ရတဲ့ top-level window စုစုပေါင်း: %d" % total)
    print("    Antigravity target တွေ့တာ: %d" % len(windows))

    if not windows:
        print("\n❌ Antigravity window မတွေ့ဘူး။")
        print("   → Antigravity ကို အရင် ဖွင့်ထားပါ (minimize မလုပ်ထားပါနဲ့)။")
        print("   → အခြား profile/workspace ဆိုရင် `--window-title \"Myanmar\"` လို သုံးပါ။")
        return 1

    any_content = False
    for window in windows:
        try:
            title = window.Name or ""
            pid = int(window.ProcessId or 0)
            hwnd = int(window.NativeWindowHandle or 0)
        except Exception:
            continue
        print("\n[2] Window: %r  (pid=%d, hwnd=%d)" % (title[:50], pid, hwnd))

        # child HWND စာရင်း
        kids = core.child_windows(hwnd) if hwnd else []
        print("    child HWND တွေ့တာ: %d ခု" % len(kids))
        render = [k for k in kids if "chrome" in core.window_class(k).lower() or "render" in core.window_class(k).lower()]
        if render:
            print("    ✅ Chrome/RenderWidgetHost child တွေ့တယ်: %s" % [core.window_class(k) for k in render])
        elif kids:
            print("    (child တွေကို မတွေ့ရသေး — အောက်က content စစ်မယ်)")

        report = engine.discover(save_dir=None, retries=2, retry_wait=1.5)
        entry = None
        for w in report["windows"]:
            if int(w.get("hwnd", 0)) == hwnd:
                entry = w
                break
        if entry is None and report["windows"]:
            entry = report["windows"][0]
        elements = entry.get("elements", []) if entry else []
        roots = entry.get("roots", []) if entry else []
        render_root = None
        for r in roots:
            if "render" in str(r.get("class", "")).lower() or "chrome" in str(r.get("class", "")).lower():
                render_root = r
        content_count = int(render_root.get("elements", 0)) if render_root else 0
        print("    UI element စုစုပေါင်း: %d" % len(elements))
        if render_root:
            print("    Chrome_RenderWidgetHostHWND ထဲက content: %d" % content_count)

        matched = [row for row in elements if row.get("matched_label")]
        blocked = [row for row in elements if row.get("blocked_by")]

        if len(elements) <= 5:
            print("\n❌ Content မပေါ်သေး — titlebar button ၃ ခုပဲ ရတယ်။")
            print("   → ဒီ command ကို run ပါ:  python agy_auto_allow.py --relaunch-agy")
            print("     (Antigravity ကို ပိတ်ပြီး --force-renderer-accessibility နဲ့ ပြန်ဖွင့်ပေးမယ်)")
        elif content_count == 0 and render_root:
            print("\n⚠️  Content root တွေ့ပေမယ့် အထဲမှာ element မရှိသေး — ၂–၃ စက္ကန့် စောင့်ပြီး ပြန်စစ်ပါ။")
            print("   → မရသေးရင် `python agy_auto_allow.py --relaunch-agy`")
        else:
            any_content = True
            print("\n✅ Content ပေါ်ပြီ! နှိပ်မယ့် button တွေ:")
            if matched:
                for row in matched:
                    print("     - %r  (%s)  label=%s" % (row["name"], row["type"], row["matched_label"]))
            else:
                print("     (label နဲ့ ကိုက်တဲ့ button မတွေ့သေး — အောက်က 'blocklist' စစ်ပါ)")
            if blocked:
                print("   blocklist နဲ့ တားထားတာတွေ: %s" % [r["name"] for r in blocked])

    print("\n" + "=" * 60)
    if any_content:
        print("  ✅ အောင်မြင် — tray app ကို စတင်နိုင်ပါပြီ")
        print("     → AgyAutoAllow.pyw ကို double-click (သို့)  python agy_auto_allow.py")
        return 0
    print("  ❌ Content မပေါ်သေး — အပေါ်က ညွှန်ကြားချက်အတိုင်း လုပ်ပါ။")
    print("=" * 60)
    return 1


def apply_overrides(cfg: Dict[str, Any], args) -> Dict[str, Any]:
    if args.interval is not None:
        cfg["poll_interval_seconds"] = max(0.05, float(args.interval))
    if args.click_mode:
        cfg["click_mode"] = args.click_mode
    if args.labels:
        cfg["labels"] = [part.strip() for part in str(args.labels).split(",") if part.strip()]
    if args.dry_run:
        cfg["dry_run"] = True
    if args.force:
        cfg["enabled"] = True
    if args.window_title:
        cfg["window_title_regex"] = str(args.window_title)
    if args.watch_any:
        cfg["process_names"] = []
    return cfg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agy_auto_allow",
        description="Antigravity ရဲ့ Allow/Submit button တွေကို နောက်ကွယ်ကနေ အလိုအလျောက် နှိပ်ပေးတဲ့ tray app",
    )
    parser.add_argument("--config", help="config.json လမ်းကြောင်း (default: script folder)")
    parser.add_argument("--console", action="store_true", help="log ကို terminal မှာပါ ပြမယ်")
    parser.add_argument("--no-tray", dest="no_tray", action="store_true", help="tray မပါဘဲ console mode နဲ့ run")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="တကယ် မနှိပ်ဘဲ စမ်း")
    parser.add_argument("--force", action="store_true", help="enabled=false ဖြစ်နေရင်လည်း စတင်")
    parser.add_argument("--interval", type=float, help="poll interval (စက္ကန့်)")
    parser.add_argument("--click-mode", choices=["auto", "uia", "background", "foreground"],
                        help="နှိပ်တဲ့နည်းလမ်း")
    parser.add_argument("--labels", help="label တွေကို comma နဲ့ ခွဲပြီး အစားထိုး (ဥပမာ: allow,submit)")
    parser.add_argument("--discover", action="store_true", help="လက်ရှိ button တွေကို dump လုပ်ပြီး ထွက်")
    parser.add_argument("--watch", type=float, metavar="SECONDS", help="discover ကို အချိန်ပြီး ထပ်ခါထပ်ခါ dump")
    parser.add_argument("--list-windows", dest="list_windows", action="store_true", help="target window တွေကို ပြ")
    parser.add_argument("--grab", action="store_true", help="Antigravity screenshot ရိုက်ပြီး သိမ်း")
    parser.add_argument("--diagnose", action="store_true",
                        help="Antigravity ကို ရှာတွေ့လား + content ပေါ်လား စစ်ပြီး အဖြေပေး")
    parser.add_argument("--watch-any", dest="watch_any", action="store_true",
                        help="process name မစစ်ဘဲ window title ပါတဲ့ window အားလုံးကို စစ်")
    parser.add_argument("--window-title", dest="window_title",
                        help="window title regex (process name အစား)")
    parser.add_argument("--hidden-elements", dest="hidden_elements", action="store_true",
                        help="discover မှာ element အားလုံး ပြမယ်")
    parser.add_argument("--relaunch-agy", dest="relaunch_agy", action="store_true",
                        help="Antigravity ကို --force-renderer-accessibility နဲ့ ပြန်ဖွင့် (button တွေ မတွေ့ရင် သုံး)")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    config_file = core.config_path(args.config)
    config_existed = config_file.exists()
    try:
        cfg = core.load_config(args.config)
    except Exception as exc:
        print("config error: %s" % exc)
        return 2
    cfg = apply_overrides(cfg, args)

    logger = core.setup_logging(cfg, console=bool(args.console or args.no_tray or args.discover
                                                  or args.list_windows or args.watch or args.grab))
    logger.info("=== %s စတင် (config=%s) ===" % (APP_NAME, config_file))
    if not config_existed:
        logger.info("config.json အသစ် ဖန်တီးပြီး: %s", config_file)

    engine = core.Engine(cfg, logger)

    if args.list_windows:
        print_windows(engine)
        return 0

    if getattr(args, "relaunch_agy", False):
        return relaunch_antigravity(logger=logger)

    if getattr(args, "diagnose", False):
        return run_diagnose(cfg, logger)

    if args.discover:
        print_discover(engine, show_all=args.hidden_elements)
        return 0

    if args.watch:
        interval = max(1.0, float(args.watch))
        print("watch mode — %.0f စက္ကန့်တစ်ခါ dump လုပ်မယ် (Ctrl+C ရပ်)" % interval)
        try:
            while True:
                print_discover(engine, save=False, show_all=args.hidden_elements)
                time.sleep(interval)
        except KeyboardInterrupt:
            return 0

    if args.grab:
        do_grab(engine)
        return 0

    # hotkeys (tray mode)

    if args.no_tray:
        try:
            import pystray  # noqa: F401
            has_tray = True
        except Exception:
            has_tray = False
        if not has_tray:
            logger.warning("pystray မရှိပါ — console mode နဲ့ ဆက်လုပ်မယ်")
        run_console(engine, logger)
        return 0

    try:
        import pystray  # noqa: F401
    except Exception as exc:
        logger.warning("pystray မရှိလို့ console mode သုံးမယ် (%s)", exc)
        run_console(engine, logger)
        return 0

    tray = TrayApp(engine, logger, config_file)

    bindings = {}
    for name, spec in (cfg.get("hotkeys", {}) or {}).items():
        if name == "toggle":
            bindings[name] = (spec, lambda: tray.on_toggle())
        elif name == "discover":
            bindings[name] = (spec, lambda: tray.on_discover())
        elif name == "open_log":
            bindings[name] = (spec, lambda: tray.on_open_log())
        elif name == "quit":
            bindings[name] = (spec, lambda: tray.on_quit())
    if bindings:
        hotkey_manager = core.HotkeyManager(
            bindings, logger,
            on_error=lambda message: (logger.warning(message), tray.notify(message, force=True)),
        )
        tray.hotkeys = hotkey_manager
        hotkey_manager.start()

    try:
        tray.run()
    except KeyboardInterrupt:
        tray.on_quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
