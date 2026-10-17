# -*- coding: utf-8 -*-
"""
AgyAutoAllow - core engine
==========================

Antigravity (Electron/VSCode fork) ရဲ့ window ကို UI Automation နဲ့ ဖတ်ပြီး
"Allow / Submit / Accept ..." စတဲ့ button တွေ ပေါ်လာရင် နောက်ကွယ်ကနေ
အလိုအလျောက် နှိပ်ပေးတဲ့ engine။

အဓိက အချက်များ
  * UIA (Invoke pattern) နဲ့ နှိပ်တာမလို့ focus မခိုးဘူး၊ app တခြားတွေ သုံးနေလို့ရတယ်။
  * Invoke pattern မရှိရင် ရွေးချယ်နိုင်တဲ့ fallback (background message click / foreground click)
  * အန္တရာယ်ရှိတဲ့ label (Cancel/Reject/Deny/No/Stop ...) တွေကို blocklist နဲ့ တားထားတယ်။
  * နှိပ်ပြီးသား button ကို ထပ်မနှိပ်အောင် dedupe + attempt limit ရှိတယ်။
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import uiautomation as auto

try:  # uiautomation ရဲ့ raw client (conditions / FindAll အတွက်) ကို ယူတယ်
    import uiautomation.uiautomation as uiacore
except Exception as exc:  # pragma: no cover - ပတ်ဝန်းကျင် ပြဿနာ
    raise RuntimeError("uiautomation ကို import လုပ်လို့မရပါ: %s" % exc)

BASE_DIR = Path(__file__).resolve().parent
TREE_SCOPE_DESCENDANTS = 4

# --------------------------------------------------------------------------
# UIA thread ownership
#
# အရေးကြီး: UIA Control/Pattern တွေကို ဖန်တီးတဲ့ thread မှာပဲ ပြန်သုံးရမယ်
# (library ရဲ့ docstring မှာ ရှင်းရှင်းလင်းလင်း ဖော်ပြထားတယ်)။ ဒါကြောင့်
# thread တစ်ခုချင်းစီအတွက် client အသစ် ဖန်တီးပေးတဲ့ helper ထားတယ်။
# --------------------------------------------------------------------------
_thread_state = threading.local()
_client_keepalive: List[Any] = []


def ensure_uia_in_current_thread() -> None:
    """လက်ရှိ thread အတွက် UIAutomation client ကို အသစ်ပြန်ဖန်တီးတယ်။"""
    if getattr(_thread_state, "ready", False):
        return
    try:
        old = getattr(uiacore._AutomationClient, "_instance", None)
        if old is not None:
            _client_keepalive.append(old)   # ရှိပြီးသား element တွေ မပျက်အောင် ချုပ်ထားတယ်
        uiacore._AutomationClient._instance = None
        uiacore._AutomationClient.instance()
    except Exception as exc:
        raise RuntimeError("UIAutomation client ကို မဖန်တီးနိုင်ပါ: %s" % exc)
    _thread_state.ready = True


def uia_client():
    """လက်ရှိ thread ရဲ့ IUIAutomation client။"""
    ensure_uia_in_current_thread()
    return uiacore._AutomationClient.instance().IUIAutomation

# --------------------------------------------------------------------------
# Win32 helpers
# --------------------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetForegroundWindow.restype = wt.HWND
user32.WindowFromPoint.restype = wt.HWND
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.BringWindowToTop.argtypes = [wt.HWND]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.IsIconic.argtypes = [wt.HWND]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.EnumChildWindows.argtypes = [wt.HWND, ctypes.c_void_p, wt.LPARAM]
user32.EnumChildWindows.restype = wt.BOOL
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindow.argtypes = [wt.HWND]

kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)
]
kernel32.GetCurrentThreadId.restype = wt.DWORD
kernel32.CloseHandle.argtypes = [wt.HANDLE]

SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
WM_GETOBJECT = 0x003D
OBJID_CLIENT = 0xFFFFFFFC
SMTO_ABORTIFHUNG = 0x0002

LOGGER_NAME = "agyautoallow"


def process_name(pid: int) -> str:
    """PID ကနေ exe နာမည်ကို ယူတယ် (cache လုပ်ထားတယ်)။"""
    if pid <= 0:
        return ""
    cached = _PROC_NAME_CACHE.get(pid)
    if cached is not None:
        return cached
    name = ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        try:
            buf = ctypes.create_unicode_buffer(4096)
            size = wt.DWORD(len(buf))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                name = os.path.basename(buf.value)
        except Exception:
            name = ""
        finally:
            kernel32.CloseHandle(handle)
    _PROC_NAME_CACHE[pid] = name
    return name


_PROC_NAME_CACHE: Dict[int, str] = {}


def _virtual_screen_rect() -> Tuple[int, int, int, int]:
    x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return (x, y, x + w, y + h)


_ENUM_CHILD_PROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def child_windows(hwnd: int, max_children: int = 80) -> List[int]:
    """Window တစ်ခုရဲ့ child HWND အားလုံး (အနက်အထိ) ကို ပြန်ပေးတယ်။

    Chromium/Electron ရဲ့ တကယ့် web content (Allow/Submit button တွေ ပါတဲ့
    accessibility tree) က top-level window မဟုတ်ဘဲ
    `Chrome_RenderWidgetHostHWND` ဆိုတဲ့ child HWND ထဲမှာ ရှိတယ်။
    """
    found: List[int] = []
    if not hwnd:
        return found

    def callback(child, _lparam):
        if len(found) < max_children:
            found.append(int(child))
        return True

    try:
        user32.EnumChildWindows(wt.HWND(hwnd), _ENUM_CHILD_PROC(callback), 0)
    except Exception:
        return []
    return found


def window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    try:
        user32.GetClassNameW(wt.HWND(hwnd), buf, 256)
    except Exception:
        return ""
    return buf.value


def _window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    rect = wt.RECT()
    if not user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(rect)):
        return (0, 0, 0, 0)
    return (rect.left, rect.top, rect.right, rect.bottom)


def _force_foreground(hwnd: int) -> None:
    """Target window ကို foreground ရောက်အောင် လုပ်တယ် (click အတွက်ပဲ သုံးတယ်)။"""
    try:
        fg = user32.GetForegroundWindow()
        if fg == hwnd:
            return
        fg_tid = user32.GetWindowThreadProcessId(fg, None)
        my_tid = kernel32.GetCurrentThreadId()
        attached = bool(user32.AttachThreadInput(my_tid, fg_tid, True))
        try:
            user32.ShowWindow(wt.HWND(hwnd), SW_SHOW)
            user32.BringWindowToTop(wt.HWND(hwnd))
            user32.SetForegroundWindow(wt.HWND(hwnd))
        finally:
            if attached:
                user32.AttachThreadInput(my_tid, fg_tid, False)
    except Exception:
        pass


def _send_left_click(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.012)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.012)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def nudge_renderer_accessibility(hwnd: int) -> Dict[str, bool]:
    """Chromium/Electron ကို 'assistive technology ရှိတယ်' လို့ ခံစားစေပြီး
    accessibility tree ကို restart မလိုဘဲ ဖွင့်စေဖို့ ကြိုးစားတယ်။

    နည်းလမ်း ၂ ခု —
      1. `WM_GETOBJECT`/`OBJID_CLIENT` ပို့ခြင်း (MSAA client အနေနဲ့ မိတ်ဆက်)
      2. `oleacc.AccessibleObjectFromWindow` ခေါ်ခြင်း (တကယ် MSAA client ဖြစ်ကြောင်း ပြ)

    ပြန်ပေးတာက 'ကြိုးစားချက် အောင်မြင်/မမြင်' မဟုတ်ဘဲ ဘယ်နည်းလမ်း ပို့ပြီးလဲ
    ဆိုတာပါ — tree ပြန်ပြည့်လား ဆိုတာကို နောက် scan တွေမှာ ပြန်စစ်တယ်။
    """
    result: Dict[str, bool] = {"wm_getobject": False, "msaa": False}
    if not hwnd:
        return result

    try:
        user32.SendMessageTimeoutW.argtypes = [
            wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        user32.SendMessageTimeoutW.restype = wt.LPARAM
        out = ctypes.c_size_t(0)
        user32.SendMessageTimeoutW(
            wt.HWND(hwnd), WM_GETOBJECT, 0, wt.LPARAM(OBJID_CLIENT),
            SMTO_ABORTIFHUNG, 250, ctypes.byref(out),
        )
        result["wm_getobject"] = True
    except Exception:
        pass

    try:
        import comtypes

        oleacc = ctypes.oledll.oleacc
        oleacc.AccessibleObjectFromWindow.argtypes = [
            wt.HWND, wt.DWORD, ctypes.POINTER(comtypes.GUID),
            ctypes.POINTER(ctypes.POINTER(comtypes.IUnknown)),
        ]
        oleacc.AccessibleObjectFromWindow.restype = ctypes.HRESULT
        iid_ia = comtypes.GUID("{618736E0-3C3D-11CF-810C-00AA00389B71}")  # IAccessible
        ptr = ctypes.POINTER(comtypes.IUnknown)()
        oleacc.AccessibleObjectFromWindow(
            wt.HWND(hwnd), OBJID_CLIENT, ctypes.byref(iid_ia), ctypes.byref(ptr),
        )
        result["msaa"] = bool(ptr)
    except Exception:
        pass

    return result



# --------------------------------------------------------------------------
# Screen sleep prevention (keep display awake while Auto-Allow is ON)
# --------------------------------------------------------------------------
_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001
_ES_DISPLAY_REQUIRED = 0x00000002


def set_keep_awake(enabled: bool) -> None:
    """Auto-Allow が ON の間、画面が sleep しないようにする (Windows)。"""
    try:
        if enabled:
            ctypes.windll.kernel32.SetThreadExecutionState(
                _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_DISPLAY_REQUIRED)
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Label matching
# --------------------------------------------------------------------------
DEFAULT_LABELS: List[str] = [
    "allow", "allow once", "allow always", "always allow", "allow all",
    "allow for this session", "accept", "accept all", "approve", "approve once",
    "always approve", "yes", "yes allow", "yes, allow", "ok", "okay",
    "continue", "resume", "run", "run command", "run anyway", "retry",
    "submit", "confirm", "proceed", "trust", "grant", "apply", "keep",
    "keep changes", "do it", "go ahead", "agree",
    # Antigravity ရဲ့ "Allow running ...?" dialog အတွက် အထူး
    "allow this time", "yes, allow this time", "yes, and always allow",
    "allow for this conversation", "allow for this project", "always allow this",
]

DEFAULT_BLOCK_LABELS: List[str] = [
    "cancel", "reject", "reject all", "deny", "deny once", "decline", "no",
    "no thanks", "stop", "abort", "quit", "exit", "close", "dismiss", "skip",
    "delete", "discard", "undo", "revert", "remove", "disable", "ignore",
    "later", "never", "not now", "don't allow", "dont allow", "don't save",
    "dont save", "no, don't", "block",
    # Antigravity dialog: "No (tell the agent what to do instead)" / "Skip"
    "no (tell the agent", "tell the agent what to do instead",
]


def normalize_label(text: Optional[str]) -> str:
    """Name ကို နှိုင်းယှဉ်လို့ရတဲ့ ပုံစံပြောင်းတယ် (mnemonic &, ellipsis, နံပါတ်ရှေ့ဆုံး စသည်)။"""
    if not text:
        return ""
    t = text.replace("\u2026", "...").replace("\u00a0", " ")
    t = t.replace("\u200b", "")
    t = re.sub(r"\.{2,}\s*$", "", t)          # နောက်ဆုံး ... ကို ဖြုတ်
    t = t.replace("&", "")                     # mnemonic ampersand
    t = re.sub(r"\s+", " ", t).strip()
    # "1  Yes, allow this time" လို ရှေ့ဆုံး နံပါတ်ကို ဖြုတ် (numbered choice list)
    t = re.sub(r"^\d{1,2}\s*[\.\):\-\u2013\u2014]?\s+(?=[^\d])", "", t)
    t = t.strip(" \t:.\u2013-\u2014")
    return t.lower()


def label_matches(name: str, labels: Sequence[str], mode: str = "smart") -> Optional[str]:
    """name က labels ထဲက တစ်ခုနဲ့ ကိုက်ရင် အဲဒီ label ကို ပြန်ပေးတယ်။"""
    normalized = normalize_label(name)
    if not normalized:
        return None
    norm_labels = [(normalize_label(l), l) for l in labels]
    for nl, original in norm_labels:
        if nl and normalized == nl:
            return original
    if mode == "exact":
        return None
    for nl, original in norm_labels:
        if not nl:
            continue
        if re.match(r"^%s\b" % re.escape(nl), normalized):
            return original
    if mode == "contains":
        for nl, original in norm_labels:
            if nl and nl in normalized:
                return original
    return None


def is_blocked(name: str, block_labels: Sequence[str]) -> Optional[str]:
    return label_matches(name, block_labels, mode="smart")


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "dry_run": False,
    "prevent_screen_sleep": True,   # ON の間、画面が sleep しないようにする

    "process_names": ["Antigravity.exe"],
    "window_title_regex": "",
    "include_minimized": False,
    "scan_child_windows": True,
    "max_child_windows": 80,
    "min_child_window_size": 80,

    "labels": list(DEFAULT_LABELS),
    "block_labels": list(DEFAULT_BLOCK_LABELS),
    "match_mode": "smart",
    "control_types": [
        "ButtonControl", "HyperlinkControl", "MenuItemControl", "SplitButtonControl",
        "CheckBoxControl", "RadioButtonControl", "ListItemControl",
    ],

    "poll_interval_seconds": 0.5,
    "max_poll_interval_seconds": 2.0,
    "min_seconds_between_clicks": 0.8,
    "max_clicks_per_minute": 40,
    "dedupe_seconds": 3.0,
    "max_attempts_per_button": 3,
    "suppress_seconds_after_failed_attempts": 30.0,
    "same_label_group_cooldown": 10.0,

    "click_mode": "auto",            # auto | uia | background | foreground
    "restore_foreground_after_click": True,
    "restore_cursor_after_click": True,

    # --- Antigravity accessibility စောင့်ကြည့်စစ်ဆေးမှု ---
    # Chromium/Electron က UIA tree ကို `--force-renderer-accessibility` မပါဘဲ
    # မပေးတာမို့ tree ဗလာဖြစ်နေရင် သတိပေးပြီး (လိုရင်) ပြန်ဖွင့်ပေးတယ်။
    "accessibility_check": True,
    "accessibility_min_elements": 10,
    "accessibility_empty_streak": 4,
    "accessibility_nudge": True,
    "accessibility_nudge_cooldown_seconds": 60.0,
    "auto_relaunch_on_empty": False,
    "auto_relaunch_cooldown_seconds": 180.0,

    "max_name_length": 250,
    "min_rect_width": 10,
    "max_rect_width": 1200,
    "min_rect_height": 8,
    "max_rect_height": 300,
    "require_on_screen": True,
    "max_elements_per_scan": 4000,

    "notify_on_click": True,
    "notify_min_seconds": 4.0,

    "log_file": "logs/agy_auto_allow.log",
    "log_level": "INFO",
    "log_max_bytes": 1000000,
    "log_backup_count": 3,

    "hotkeys": {
        "toggle": "ctrl+alt+a",
        "discover": "ctrl+alt+d",
        "open_log": "ctrl+alt+l",
        "quit": "ctrl+alt+q",
    },

    "image_fallback": {
        "enabled": False,
        "templates_dir": "assets/templates",
        "threshold": 0.90,
        "max_matches": 5,
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def config_path(user_path: Optional[str] = None) -> Path:
    if user_path:
        return Path(user_path).expanduser().resolve()
    return BASE_DIR / "config.json"


def load_config(user_path: Optional[str] = None, create: bool = True) -> Dict[str, Any]:
    path = config_path(user_path)
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeError("config.json ဖတ်လို့မရပါ (%s): %s" % (path, exc))
    cfg = _deep_merge(DEFAULT_CONFIG, data)
    if create and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg


def resolve_path(value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (BASE_DIR / p)


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
def setup_logging(cfg: Dict[str, Any], console: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, str(cfg.get("log_level", "INFO")).upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    log_file = resolve_path(str(cfg.get("log_file", "logs/agy_auto_allow.log")))
    try:
        from logging.handlers import RotatingFileHandler

        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=int(cfg.get("log_max_bytes", 1000000)),
            backupCount=int(cfg.get("log_backup_count", 3)),
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as exc:
        logger.addHandler(logging.NullHandler())
        print("warning: log file မဖွင့်နိုင်ပါ (%s)" % exc)

    if console:
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    return logger


# --------------------------------------------------------------------------
# Candidate / scan results
# --------------------------------------------------------------------------
@dataclass
class Candidate:
    element: Any                  # raw IUIAutomationElement
    name: str
    control_type: str
    label: str
    rect: Tuple[int, int, int, int]
    window_title: str
    window_hwnd: int
    pid: int
    signature: Tuple[Any, ...] = field(default=())

    @property
    def width(self) -> int:
        return max(0, self.rect[2] - self.rect[0])

    @property
    def height(self) -> int:
        return max(0, self.rect[3] - self.rect[1])

    @property
    def center(self) -> Tuple[int, int]:
        return ((self.rect[0] + self.rect[2]) // 2, (self.rect[1] + self.rect[3]) // 2)

    def describe(self) -> str:
        return "%s [%s] at %s" % (self.name, self.control_type, self.rect)


@dataclass
class ClickResult:
    candidate: Candidate
    ok: bool
    method: str
    detail: str = ""


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------
class Engine:
    """Antigravity window ကို စောင့်ကြည့်ပြီး Allow/Submit ကို နှိပ်ပေးတဲ့ engine။"""

    def __init__(self, cfg: Dict[str, Any], logger: logging.Logger,
                 on_event: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.cfg = cfg
        self.log = logger
        self.on_event = on_event
        self._lock = threading.RLock()
        self._stop = threading.Event()

        self.enabled: bool = bool(cfg.get("enabled", True))
        self.dry_run: bool = bool(cfg.get("dry_run", False))
        self._apply_keep_awake()

        self._attempts: Dict[Tuple[Any, ...], Tuple[int, float]] = {}
        self._clicked_at: Dict[Tuple[Any, ...], float] = {}
        self._label_group_clicked: Dict[Tuple[Any, ...], float] = {}
        self._click_times: deque = deque(maxlen=500)

        self.stats: Dict[str, Any] = {
            "clicks_total": 0,
            "clicks_this_run": 0,
            "scans": 0,
            "last_label": None,
            "last_method": None,
            "last_time": None,
            "last_time_ts": None,
            "last_scan_ms": None,
            "poll_interval": None,
        }
        self.recent: deque = deque(maxlen=8)
        self.status: str = "starting"
        self.hotkey_error: Optional[str] = None
        self._idle_streak = 0
        self._active_until = 0.0

        self._commands: "queue.Queue[Tuple[Callable[[], Any], threading.Event, Dict[str, Any]]]" = queue.Queue()
        self._runner_alive = threading.Event()
        self._condition = None
        self._condition_owner: Optional[int] = None
        self._templates: Optional[List[Tuple[str, Any]]] = None

        # accessibility health (Chromium UIA tree ဗလာ/မဗလာ စစ်ဖို့)
        self.tree_element_count = 0
        self._tree_probe: Dict[str, Any] = {
            "windows": 0, "max_elements": 0, "hwnd": 0, "title": "",
        }
        self._a11y_empty_streak = 0
        self._a11y_empty_active = False
        self._a11y_nudged_at = 0.0

    # -------------------------------------------------- conditions
    def _build_condition(self):
        client = uia_client()
        types = []
        for name in self.cfg.get("control_types", []):
            value = getattr(auto.ControlType, str(name), None)
            if isinstance(value, int):
                types.append(value)
        if not types:
            types = [auto.ControlType.ButtonControl]
        cond = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, types[0])
        for ct in types[1:]:
            other = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, ct)
            cond = client.CreateOrCondition(cond, other)
        return cond

    def _get_condition(self):
        with self._lock:
            me = threading.get_ident()
            if self._condition is None or self._condition_owner != me:
                # thread တစ်ခုက ဖန်တီးထားတဲ့ condition ကို တခြား thread မှာ မသုံးရ
                self._condition = self._build_condition()
                self._condition_owner = me
            return self._condition

    def rebuild_condition(self) -> None:
        with self._lock:
            self._condition = None
            self._condition_owner = None

    # -------------------------------------------------- state
    def set_enabled(self, value: bool) -> None:
        with self._lock:
            self.enabled = bool(value)
        self._apply_keep_awake()
        self._emit("toggle", {"enabled": self.enabled})

    def toggle(self) -> bool:
        with self._lock:
            self.enabled = not self.enabled
            value = self.enabled
        self._apply_keep_awake()
        self._emit("toggle", {"enabled": value})
        return value

    def _apply_keep_awake(self) -> None:
        if self.cfg.get("prevent_screen_sleep", False):
            set_keep_awake(bool(self.enabled))
        else:
            set_keep_awake(False)

    def request_stop(self) -> None:
        self._stop.set()

    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        if self.on_event:
            try:
                self.on_event(kind, payload)
            except Exception:
                pass

    def _note(self, text: str) -> None:
        with self._lock:
            self.recent.appendleft(time.strftime("%H:%M:%S ") + text)
            self.status = text

    # -------------------------------------------------- window discovery
    def find_windows(self) -> Tuple[List[Any], int]:
        """Target app ရဲ့ top-level windows တွေကို ရှာတယ်။ (windows, total_top_level)"""
        wanted = {str(p).lower() for p in self.cfg.get("process_names", [])}
        title_re = None
        pattern = str(self.cfg.get("window_title_regex") or "").strip()
        if pattern:
            try:
                title_re = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                self.log.warning("window_title_regex မမှန်ပါ: %s", exc)

        windows: List[Any] = []
        total = 0
        match_all = not wanted and title_re is None
        try:
            children = auto.GetRootControl().GetChildren()
        except Exception as exc:
            self.log.debug("root children ဖတ်လို့မရပါ: %s", exc)
            return [], 0

        for child in children:
            total += 1
            try:
                if child.ControlTypeName != "WindowControl":
                    continue
                name = child.Name or ""
                if title_re is not None and title_re.search(name):
                    windows.append(child)
                    continue
                if match_all:
                    windows.append(child)
                    continue
                if not wanted:
                    continue
                if process_name(child.ProcessId).lower() in wanted:
                    windows.append(child)
            except Exception:
                continue
        return windows, total

    # -------------------------------------------------- scanning
    _CHILD_CLASS_HINT = re.compile(r"chrome|render|widget|electron|webview|mozilla", re.IGNORECASE)

    def _search_roots(self, window, hwnd: int) -> List[Any]:
        """Window ကိုယ်တိုင် + child HWND တွေကို search root အနေနဲ့ ပြန်ပေးတယ်။

        Chromium/Electron ရဲ့ တကယ့် web content (Allow/Submit button တွေ ပါတဲ့
        accessibility tree) က top-level window မဟုတ်ဘဲ `Chrome_RenderWidgetHostHWND`
        ဆိုတဲ့ child HWND ထဲမှာ ရှိတာမို့ အဲဒါတွေကိုပါ ရှာရတယ်။
        (သေးငယ်တဲ့ widget တွေကို ကျော်ပြီး အလုပ်အများကြီး မဖြစ်အောင် ထိန်းတယ်)
        """
        roots = [window]
        if not self.cfg.get("scan_child_windows", True) or not hwnd:
            return roots
        min_size = int(self.cfg.get("min_child_window_size", 80))
        seen = {hwnd}
        for child in child_windows(hwnd, int(self.cfg.get("max_child_windows", 80))):
            if child in seen:
                continue
            seen.add(child)
            cls = window_class(child)
            hint = bool(self._CHILD_CLASS_HINT.search(cls))
            if not hint:
                try:
                    if not user32.IsWindowVisible(wt.HWND(child)):
                        continue
                except Exception:
                    continue
                left, top, right, bottom = _window_rect(child)
                if (right - left) < min_size or (bottom - top) < min_size:
                    continue
            try:
                roots.append(auto.ControlFromHandle(child))
            except Exception:
                continue
        if len(roots) > 1:
            self.log.debug("'%s' search root %d ခု (child HWND အပါ)", (window.Name or "")[:30], len(roots))
        return roots

    def scan(self, limit: Optional[int] = None) -> Tuple[List[Candidate], List[Dict[str, Any]]]:
        """တစ်ခါ scan လုပ်တယ်။ (click လုပ်သင့်တဲ့ candidates, debug rows)"""
        cfg = self.cfg
        candidates: List[Candidate] = []
        debug_rows: List[Dict[str, Any]] = []
        windows, total_windows = self.find_windows()
        if not windows:
            self._note("Antigravity window မတွေ့ပါ (top-level %d ခု ရှိတယ်)" % total_windows)
            self.tree_element_count = 0
            self._tree_probe = {"windows": 0, "max_elements": 0, "hwnd": 0, "title": ""}
            return [], debug_rows

        max_elements = int(cfg.get("max_elements_per_scan", 4000))
        screen = _virtual_screen_rect() if cfg.get("require_on_screen", True) else None
        limit = limit or max_elements
        condition = self._get_condition()
        seen_signatures: set = set()
        max_elements_seen = 0
        probe_hwnd = 0
        probe_title = ""

        for window in windows:
            try:
                title = window.Name or ""
                hwnd = int(window.NativeWindowHandle or 0)
                pid = int(window.ProcessId or 0)
            except Exception:
                continue

            if not cfg.get("include_minimized", False) and hwnd and user32.IsIconic(wt.HWND(hwnd)):
                self._note("'%s' က minimize ဖြစ်နေလို့ ကျော်လိုက်တယ်" % title[:40])
                continue

            if not probe_hwnd:
                probe_hwnd = hwnd
                probe_title = title

            for root in self._search_roots(window, hwnd):
                try:
                    array = root.Element.FindAll(TREE_SCOPE_DESCENDANTS, condition)
                    count = int(array.Length)
                except Exception as exc:
                    self.log.debug("FindAll မအောင်မြင်ပါ (%s): %s", title[:30], exc)
                    continue

                if count > max_elements_seen:
                    max_elements_seen = count

                for index in range(min(count, limit)):
                    try:
                        element = array.GetElement(index)
                        name = element.CurrentName or ""
                        ctrl_type_id = int(element.CurrentControlType)
                        ctrl_type = auto.ControlTypeNames.get(ctrl_type_id, str(ctrl_type_id))
                        bound = element.CurrentBoundingRectangle
                        rect = (int(bound.left), int(bound.top), int(bound.right), int(bound.bottom))
                        enabled = bool(element.CurrentIsEnabled)
                        offscreen = bool(element.CurrentIsOffscreen)
                    except Exception:
                        continue

                    debug_rows.append({
                        "window": title, "name": name, "type": ctrl_type,
                        "rect": rect, "enabled": enabled, "offscreen": offscreen,
                    })

                    label = label_matches(name, cfg.get("labels", []), cfg.get("match_mode", "smart"))
                    if not label:
                        continue
                    blocked = is_blocked(name, cfg.get("block_labels", []))
                    if blocked:
                        self.log.debug("blocklist: %r (%s)", name, blocked)
                        continue
                    if not enabled or offscreen:
                        continue
                    if len(name) > int(cfg.get("max_name_length", 60)):
                        continue
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width < int(cfg.get("min_rect_width", 10)) or height < int(cfg.get("min_rect_height", 8)):
                        continue
                    if width > int(cfg.get("max_rect_width", 1200)) or height > int(cfg.get("max_rect_height", 300)):
                        continue
                    if screen is not None:
                        if rect[2] <= screen[0] or rect[0] >= screen[2]:
                            continue
                        if rect[3] <= screen[1] or rect[1] >= screen[3]:
                            continue

                    try:
                        runtime_id = tuple(element.GetRuntimeId())
                    except Exception:
                        runtime_id = ()
                    if not runtime_id or runtime_id == (0,):
                        runtime_id = ("rect",) + rect
                    signature = (pid, normalize_label(name)) + tuple(runtime_id)
                    if signature in seen_signatures:
                        continue          # root တစ်ခုထက်ပိုပြီး တွေ့နိုင်တာမို့ ထပ်မထည့်
                    seen_signatures.add(signature)

                    candidates.append(Candidate(
                        element=element, name=name, control_type=ctrl_type, label=label,
                        rect=rect, window_title=title, window_hwnd=hwnd, pid=pid,
                        signature=signature,
                    ))

        candidates.sort(key=lambda c: (c.rect[1], c.rect[0]))

        self.tree_element_count = max_elements_seen
        self._tree_probe = {
            "windows": len(windows), "max_elements": max_elements_seen,
            "hwnd": probe_hwnd, "title": probe_title,
        }

        # ---- optional image-template fallback (UIA က ဘာမှ မတွေ့ရင်) ----
        image_cfg = cfg.get("image_fallback", {}) or {}
        if not candidates and image_cfg.get("enabled"):
            for window in windows:
                for label, point, score in self._image_scan(window, float(image_cfg.get("threshold", 0.9))):
                    if is_blocked(label, cfg.get("block_labels", [])):
                        continue
                    try:
                        hwnd = int(window.NativeWindowHandle or 0)
                        pid = int(window.ProcessId or 0)
                        title = window.Name or ""
                    except Exception:
                        continue
                    box = (point[0] - 12, point[1] - 8, point[0] + 12, point[1] + 8)
                    candidates.append(Candidate(
                        element=None, name="%s (image)" % label, control_type="ImageTemplate",
                        label=label, rect=box, window_title=title, window_hwnd=hwnd, pid=pid,
                        signature=("image", pid, label, point[0] // 4, point[1] // 4),
                    ))
                    self.log.info("image match: %s score=%.2f at %s", label, score, point)
            if candidates:
                candidates.sort(key=lambda c: (c.rect[1], c.rect[0]))
        return candidates, debug_rows

    # -------------------------------------------------- rate limit / dedupe
    def _rate_limit_ok(self) -> Tuple[bool, str]:
        cfg = self.cfg
        now = time.time()
        while self._click_times and now - self._click_times[0] > 60.0:
            self._click_times.popleft()
        if len(self._click_times) >= int(cfg.get("max_clicks_per_minute", 40)):
            return False, "minute limit"
        if self._click_times and now - self._click_times[-1] < float(cfg.get("min_seconds_between_clicks", 0.8)):
            return False, "interval limit"
        return True, ""

    def _should_skip(self, candidate: Candidate) -> str:
        """skip လုပ်ရမယ်ဆိုရင် အကြောင်းရင်း ပြန်ပေးတယ် (မဟုတ်ရင် '')။"""
        cfg = self.cfg
        now = time.time()
        sig = candidate.signature
        last = self._clicked_at.get(sig)
        if last is not None and now - last < float(cfg.get("dedupe_seconds", 3.0)):
            return "dedupe"
        # တူတူ label ကို window တစ်ခုတည်းမှာ ခဏပဲ နှိပ်မယ်။
        # ဥပမာ — "1 Yes, allow this time" နဲ့ "4 Yes, and always allow ..." နှစ်ခုလုံး
        # label "yes" ဖြစ်တာမို့ နှစ်ခုလုံး နှိပ်မိရင် ပိုကျယ်တဲ့ permission ကို
        # မရည်ရွယ်ဘဲ ရွေးမိသလို ဖြစ်တယ်။ ဒါကြောင့် အပေါ်ဆုံး (ကျဉ်းဆုံး) တစ်ခုပဲ နှိပ်တယ်။
        group_cooldown = float(cfg.get("same_label_group_cooldown", 10.0))
        if group_cooldown > 0:
            key = (candidate.window_hwnd, normalize_label(candidate.label))
            group_last = self._label_group_clicked.get(key)
            if group_last is not None and now - group_last < group_cooldown:
                return "label group"
        count, first_ts = self._attempts.get(sig, (0, now))
        if count >= int(cfg.get("max_attempts_per_button", 3)):
            if now - first_ts < float(cfg.get("suppress_seconds_after_failed_attempts", 30.0)):
                return "suppressed"
            self._attempts[sig] = (0, now)
        return ""

    # -------------------------------------------------- clicking
    def _click_with_uia(self, candidate: Candidate) -> Optional[str]:
        """UIA pattern နဲ့ နှိပ်တယ် (focus မလိုဘူး၊ app တခြား သုံးနေလို့ရတယ်)။"""
        wrapper = auto.Control(element=candidate.element)
        try:
            pattern = wrapper.GetPattern(auto.PatternId.InvokePattern)
            if pattern:
                if pattern.Invoke(0):
                    return "uia.Invoke"
        except Exception as exc:
            self.log.debug("Invoke မအောင်မြင်ပါ: %s", exc)
        try:
            pattern = wrapper.GetPattern(auto.PatternId.LegacyIAccessiblePattern)
            if pattern:
                pattern.DoDefaultAction(0)
                return "uia.DoDefaultAction"
        except Exception as exc:
            self.log.debug("DoDefaultAction မအောင်မြင်ပါ: %s", exc)
        try:
            pattern = wrapper.GetPattern(auto.PatternId.TogglePattern)
            if pattern:
                pattern.Toggle(0)
                return "uia.Toggle"
        except Exception:
            pass
        try:
            pattern = wrapper.GetPattern(auto.PatternId.SelectionItemPattern)
            if pattern:
                pattern.Select(0)
                return "uia.Select"
        except Exception:
            pass
        return None

    def _click_background(self, candidate: Candidate) -> Optional[str]:
        if not candidate.window_hwnd:
            return None
        # Chromium/Electron ရဲ့ web content က top-level window မဟုတ်ဘဲ
        # Chrome_RenderWidgetHostHWND ဆိုတဲ့ child HWND ထဲမှာ ရှိတယ်။
        # ဒါကြောင့် point ပါတဲ့ child HWND ကို ရှာပြီး အဲဒီကို PostMessage လုပ်တယ်
        # (top-level window ကို လုပ်ရင် Chromium က route မလုပ်တတ်ဘူး)။
        target_hwnd = candidate.window_hwnd
        for child in child_windows(candidate.window_hwnd):
            try:
                left, top, right, bottom = _window_rect(child)
            except Exception:
                continue
            cx, cy = candidate.center
            if left <= cx < right and top <= cy < bottom:
                target_hwnd = child
                break
        point = wt.POINT(candidate.center[0], candidate.center[1])
        if not user32.ScreenToClient(wt.HWND(target_hwnd), ctypes.byref(point)):
            return None
        lparam = ((point.y & 0xFFFF) << 16) | (point.x & 0xFFFF)
        user32.PostMessageW(wt.HWND(target_hwnd), WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        time.sleep(0.03)
        user32.PostMessageW(wt.HWND(target_hwnd), WM_LBUTTONUP, 0, lparam)
        time.sleep(0.03)
        return "background.PostMessage"

    def _click_foreground(self, candidate: Candidate) -> Optional[str]:
        cfg = self.cfg
        prev_fg = user32.GetForegroundWindow()
        cursor = wt.POINT()
        user32.GetCursorPos(ctypes.byref(cursor))
        try:
            if candidate.window_hwnd:
                _force_foreground(candidate.window_hwnd)
                time.sleep(0.05)
            x, y = candidate.center
            if candidate.element is not None:
                try:
                    point = auto.Control(element=candidate.element).GetClickablePoint()
                    if point[2]:
                        x, y = point[0], point[1]
                except Exception:
                    pass
            _send_left_click(x, y)
            time.sleep(0.06)
            return "foreground.SendInput"
        finally:
            if cfg.get("restore_cursor_after_click", True):
                user32.SetCursorPos(cursor.x, cursor.y)
            if cfg.get("restore_foreground_after_click", True) and prev_fg and prev_fg != candidate.window_hwnd:
                try:
                    if user32.IsWindow(prev_fg):
                        user32.SetForegroundWindow(prev_fg)
                except Exception:
                    pass

    def click(self, candidate: Candidate) -> ClickResult:
        cfg = self.cfg
        mode = str(cfg.get("click_mode", "auto")).lower()
        if self.dry_run:
            return ClickResult(candidate, True, "dry-run", "နှိပ်လိုက်တယ်လို့ ယူဆ")

        if candidate.element is None:
            # image template ကနေ ရတဲ့ နေရာ — UIA element မရှိလို့ coordinate click ပဲ ရတယ်
            try:
                used = self._click_foreground(candidate)
            except Exception as exc:
                return ClickResult(candidate, False, "none", str(exc))
            return ClickResult(candidate, bool(used), used or "none", "" if used else "click မဖြစ်ပါ")

        methods: List[Callable[[Candidate], Optional[str]]] = []
        if mode == "uia":
            methods = [self._click_with_uia]
        elif mode == "background":
            methods = [self._click_background]
        elif mode == "foreground":
            methods = [self._click_foreground]
        else:  # auto
            methods = [self._click_background, self._click_with_uia, self._click_foreground]

        last_error = ""
        for method in methods:
            try:
                used = method(candidate)
            except Exception as exc:
                last_error = str(exc)
                self.log.debug("%s မအောင်မြင်ပါ: %s", method.__name__, exc)
                continue
            if used:
                # auto mode မှာ UIA/Background က "success" ပြန်ပေမယ့် တကယ်တော့
                # Chromium က focus မရှိလို့ မနှိပ်ဖြစ်တာ ဖြစ်နိုင်တယ်။ ဒါကြောင့်
                # နှိပ်ပြီး ခဏစောင့်ပြီး button ပျောက်သွားလား စစ်တယ် — မပျောက်ရင်
                # နောက်နည်းလမ်း (foreground စသည်) ကို ဆက်စမ်းတယ်။
                if (mode == "auto" and method is not self._click_foreground):
                    time.sleep(0.35)
                    try:
                        new_candidates, _ = self.scan()
                    except Exception:
                        new_candidates = []
                    still_there = any(
                        (c.window_hwnd == candidate.window_hwnd
                         and normalize_label(c.name) == normalize_label(candidate.name))
                        for c in new_candidates
                    )
                    if still_there:
                        self.log.debug("%s က success ပြန်ပေမယ့် button မပျောက်သေး — "
                                       "နောက်နည်းလမ်း ဆက်စမ်းမယ်", used)
                        continue
                return ClickResult(candidate, True, used)
        return ClickResult(candidate, False, "none", last_error or "နည်းလမ်း မရှိပါ")

    # -------------------------------------------------- image fallback
    def _load_templates(self) -> List[Tuple[str, Any]]:
        if self._templates is not None:
            return self._templates
        cfg = self.cfg.get("image_fallback", {}) or {}
        folder = resolve_path(str(cfg.get("templates_dir", "assets/templates")))
        templates: List[Tuple[str, Any]] = []
        if folder.is_dir():
            try:
                import cv2  # type: ignore
            except Exception as exc:
                self.log.warning("image fallback အတွက် opencv မရှိပါ: %s", exc)
                self._templates = []
                return self._templates
            for file in sorted(folder.glob("*.png")):
                image = cv2.imread(str(file))
                if image is not None:
                    templates.append((file.stem, image))
            self.log.info("template %d ခု တင်ပြီး (%s)", len(templates), folder)
        self._templates = templates
        return templates

    def _image_scan(self, window, threshold: float) -> List[Tuple[str, Tuple[int, int], float]]:
        """Window ရဲ့ screen ပေါ်က ပုံနဲ့ template တွေ ယှဉ်တယ် (window က ပေါ်နေရမယ်)။"""
        try:
            import cv2  # type: ignore
            import numpy  # type: ignore
            from PIL import ImageGrab  # type: ignore
        except Exception:
            return []
        templates = self._load_templates()
        if not templates:
            return []
        left, top, right, bottom = _window_rect(int(window.NativeWindowHandle or 0))
        if right - left <= 0 or bottom - top <= 0:
            return []
        if user32.IsIconic(wt.HWND(int(window.NativeWindowHandle or 0))):
            return []
        try:
            shot = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
        except Exception as exc:
            self.log.debug("screenshot ရိုက်လို့မရပါ: %s", exc)
            return []
        haystack = cv2.cvtColor(numpy.array(shot), cv2.COLOR_RGB2BGR)
        results: List[Tuple[str, Tuple[int, int], float]] = []
        max_matches = int(self.cfg.get("image_fallback", {}).get("max_matches", 5))
        for label, template in templates:
            th, tw = template.shape[:2]
            if th > haystack.shape[0] or tw > haystack.shape[1]:
                continue
            try:
                res = cv2.matchTemplate(haystack, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
            except Exception:
                continue
            if max_val >= threshold:
                cx = left + max_loc[0] + tw // 2
                cy = top + max_loc[1] + th // 2
                results.append((label, (cx, cy), float(max_val)))
                if len(results) >= max_matches:
                    return results
        return results

    # -------------------------------------------------- accessibility health
    def _check_accessibility(self) -> None:
        """Target window ရဲ့ UIA tree ဗလာဖြစ်နေရင် — Chromium က accessibility ကို
        `--force-renderer-accessibility` မပါဘဲ မပေးတာမို့ — သတိပေးပြီး restart
        မလိုဘဲ ဖွင့်ဖို့ (nudge) ကြိုးစားတယ်။"""
        cfg = self.cfg
        if not cfg.get("accessibility_check", True):
            return

        probe = self._tree_probe
        windows = int(probe.get("windows", 0))
        maximum = int(probe.get("max_elements", 0))
        hwnd = int(probe.get("hwnd", 0))

        if not windows:
            self._a11y_empty_streak = 0
            self._a11y_empty_active = False
            return

        min_elements = int(cfg.get("accessibility_min_elements", 10))
        streak_needed = max(1, int(cfg.get("accessibility_empty_streak", 4)))
        healthy = maximum > min_elements

        if healthy:
            self._a11y_empty_streak = 0
        else:
            self._a11y_empty_streak += 1

        if not healthy and self._a11y_empty_streak >= streak_needed:
            if self._a11y_empty_active:
                return
            self._a11y_empty_active = True
            nudged = False
            if cfg.get("accessibility_nudge", True):
                now = time.time()
                cooldown = float(cfg.get("accessibility_nudge_cooldown_seconds", 60.0))
                if now - self._a11y_nudged_at >= cooldown:
                    self._a11y_nudged_at = now
                    try:
                        outcome = nudge_renderer_accessibility(hwnd)
                        nudged = bool(outcome.get("wm_getobject") or outcome.get("msaa"))
                        self.log.info("accessibility nudge စမ်း: %s", outcome)
                    except Exception as exc:
                        self.log.debug("accessibility nudge error: %s", exc)
            self.log.warning(
                "Antigravity UI tree မှာ element %d ခုပဲ တွေ့တယ် (min %d) — "
                "--force-renderer-accessibility မပါဘဲ ဖွင့်ထားလို့ ဖြစ်နိုင်တယ်",
                maximum, min_elements)
            self._note("UI tree ဗလာ — accessibility flag လိုနိုင်တယ်")
            self._emit("a11y_empty", {
                "hwnd": hwnd, "elements": maximum, "nudged": nudged,
                "window_title": probe.get("title", ""),
            })
        elif healthy and self._a11y_empty_active:
            self._a11y_empty_active = False
            self._note("UI tree ပြန်ကောင်းလာတယ် (element %d)" % maximum)
            self._emit("a11y_ok", {"elements": maximum})

    # -------------------------------------------------- one tick
    def tick(self) -> List[ClickResult]:
        with self._lock:
            if not self.enabled:
                return []
        ok, reason = self._rate_limit_ok()
        if not ok:
            return []

        results: List[ClickResult] = []
        started = time.perf_counter()
        candidates, _ = self.scan()
        self.stats["scans"] += 1
        self.stats["last_scan_ms"] = int((time.perf_counter() - started) * 1000)
        self._check_accessibility()

        if not candidates:
            self._idle_streak += 1
            return results
        self._idle_streak = 0

        for candidate in candidates:
            skip = self._should_skip(candidate)
            if skip:
                continue
            ok, reason = self._rate_limit_ok()
            if not ok:
                self.log.debug("rate limit (%s) - နောက်လှည့်မှ ဆက်လုပ်မယ်", reason)
                break

            result = self.click(candidate)
            now = time.time()
            self._click_times.append(now)
            signature = candidate.signature
            count, first_ts = self._attempts.get(signature, (0, now))
            self._attempts[signature] = (count + 1, first_ts)
            if len(self._attempts) > 5000:      # မှတ်ဉာဏ် မကြီးအောင် ရှင်းတယ်
                cutoff = now - 600.0
                self._attempts = {k: v for k, v in self._attempts.items() if v[1] >= cutoff}
                self._clicked_at = {k: v for k, v in self._clicked_at.items() if v >= cutoff}
                self._label_group_clicked = {k: v for k, v in self._label_group_clicked.items() if v >= cutoff}

            if result.ok:
                self._clicked_at[signature] = now
                self._label_group_clicked[(candidate.window_hwnd,
                                           normalize_label(candidate.label))] = now
                self._active_until = now + 5.0      # နောက်ထပ် prompt တွေ လျင်လျင်ပြန်စစ်ဖို့
                self.stats["clicks_total"] += 1
                self.stats["clicks_this_run"] += 1
                self.stats["last_label"] = candidate.name
                self.stats["last_method"] = result.method
                self.stats["last_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self.log.info(
                    "နှိပ်လိုက်တယ်: %r -> %s | window=%r | method=%s",
                    candidate.name, candidate.label, candidate.window_title[:40], result.method,
                )
                self._note("%r နှိပ်ပြီး (%s)" % (candidate.name, result.method))
                self._emit("click", {"candidate": candidate, "result": result})
            else:
                self.log.warning("နှိပ်လို့မရပါ: %r (%s)", candidate.name, result.detail)
            results.append(result)

        if not results and candidates:
            self._note("button %d ခု တွေ့ပေမယ့် နှိပ်လို့မရပါ" % len(candidates))
        elif not candidates:
            self._note("waiting - Allow/Submit မတွေ့ပါ")
        return results

    # -------------------------------------------------- main loop
    def _current_interval(self) -> float:
        """Idle ဖြစ်နေရင် ခြေလှမ်း အနည်းငယ် နှေးပေးတယ် (CPU သက်သာအောင်)။"""
        base = max(0.05, float(self.cfg.get("poll_interval_seconds", 0.5)))
        maximum = max(base, float(self.cfg.get("max_poll_interval_seconds", 2.0)))
        if time.time() < self._active_until:
            return base
        streak = self._idle_streak
        if streak >= 12:
            return maximum
        if streak >= 4:
            return min(base * 2.0, maximum)
        if streak >= 2:
            return min(base * 1.5, maximum)
        return base

    def run_forever(self) -> None:
        self.log.info("Engine စတင်ပြီး (poll=%.2fs, click_mode=%s, enabled=%s)",
                      float(self.cfg.get("poll_interval_seconds", 0.5)),
                      self.cfg.get("click_mode"), self.enabled)
        self._note("စတင်ပြီး")
        # UIA client နဲ့ element/pattern အားလုံးကို ဒီ thread ထဲမှာပဲ ဖန်တီး/သုံးတယ်
        # (thread ကနေ thread လွှဲသုံးရင် အလွန်နှေးတယ် - library ရဲ့ သတိပေးချက်)
        with auto.UIAutomationInitializerInThread(debug=False):
            ensure_uia_in_current_thread()
            self._get_condition()
            self._runner_alive.set()
            try:
                while not self._stop.is_set():
                    started = time.perf_counter()
                    interval = self._current_interval()
                    self.stats["poll_interval"] = round(interval, 2)
                    try:
                        self.tick()
                    except Exception as exc:
                        self.log.exception("tick မှာ error: %s", exc)
                    elapsed = time.perf_counter() - started
                    # command ရှိရင် ချက်ချင်း နိုး၊ မရှိရင် interval အထိ အိပ်
                    self._wait_or_run(max(0.02, interval - elapsed))
            finally:
                self._runner_alive.clear()
        self.log.info("Engine ရပ်သွားပြီ")

    # -------------------------------------------------- cross-thread commands
    def post(self, fn: Callable[[], Any], timeout: float = 20.0) -> Any:
        """UIA လုပ်ငန်းတွေကို engine thread ပေါ်မှာ run စေတယ်။"""
        if not self._runner_alive.is_set():
            return fn()
        event = threading.Event()
        box: Dict[str, Any] = {}
        self._commands.put((fn, event, box))
        if not event.wait(timeout):
            raise TimeoutError("engine thread က အချိန်မီ မပြီးပါ")
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def _wait_or_run(self, timeout: float) -> None:
        """timeout အထိ စောင့်တယ်။ command တစ်ခု ရောက်လာရင် ချက်ချင်း run တယ်။"""
        remaining = timeout
        first = True
        while True:
            try:
                fn, event, box = self._commands.get(timeout=remaining if first else 0)
            except queue.Empty:
                return
            first = False
            try:
                box["result"] = fn()
            except Exception as exc:
                box["error"] = exc
                self.log.exception("command error: %s", exc)
            finally:
                event.set()
            if self._stop.is_set():
                return
            remaining = 0

    def _discover_once(self) -> Dict[str, Any]:
        windows, total = self.find_windows()
        report: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "top_level_windows_seen": total,
            "target_processes": self.cfg.get("process_names"),
            "windows": [],
            "match_mode": self.cfg.get("match_mode"),
            "labels": self.cfg.get("labels"),
        }
        condition = self._get_condition()
        for window in windows:
            try:
                title = window.Name or ""
                pid = int(window.ProcessId or 0)
                hwnd = int(window.NativeWindowHandle or 0)
            except Exception:
                continue
            entry: Dict[str, Any] = {
                "title": title, "pid": pid, "hwnd": hwnd,
                "class": getattr(window, "ClassName", "") or "",
                "minimized": bool(hwnd and user32.IsIconic(wt.HWND(hwnd))),
                "roots": [],
                "elements": [],
            }
            seen_rows: set = set()
            for root in self._search_roots(window, hwnd):
                try:
                    root_hwnd = int(root.NativeWindowHandle or 0)
                    root_class = root.ClassName or ""
                except Exception:
                    root_hwnd, root_class = 0, ""
                try:
                    array = root.Element.FindAll(TREE_SCOPE_DESCENDANTS, condition)
                    root_count = int(array.Length)
                except Exception as exc:
                    entry["roots"].append({"class": root_class, "hwnd": root_hwnd, "error": str(exc)})
                    continue
                entry["roots"].append({"class": root_class, "hwnd": root_hwnd, "elements": root_count})

                for index in range(root_count):
                    try:
                        element = array.GetElement(index)
                        name = element.CurrentName or ""
                        ctrl = auto.ControlTypeNames.get(int(element.CurrentControlType), "?")
                        bound = element.CurrentBoundingRectangle
                        rect = (int(bound.left), int(bound.top), int(bound.right), int(bound.bottom))
                        row = {
                            "name": name, "type": ctrl, "rect": rect,
                            "enabled": bool(element.CurrentIsEnabled),
                            "offscreen": bool(element.CurrentIsOffscreen),
                            "matched_label": label_matches(name, self.cfg.get("labels", []),
                                                            self.cfg.get("match_mode", "smart")),
                            "blocked_by": is_blocked(name, self.cfg.get("block_labels", [])),
                        }
                    except Exception:
                        continue
                    key = (row["name"], row["type"], row["rect"])
                    if key in seen_rows:
                        continue
                    seen_rows.add(key)
                    entry["elements"].append(row)
            report["windows"].append(entry)
        return report

    def discover(self, save_dir: Optional[Path] = None, retries: int = 2,
                 retry_wait: float = 1.5) -> Dict[str, Any]:
        """လက်ရှိ Antigravity window ရဲ့ element တွေကို dump လုပ်တယ်။

        Chromium က accessibility tree ကို လိုအပ်မှ ဆောက်တာမို့ ပထမလှည့်မှာ
        content မပေါ်သေးရင် ခဏစောင့်ပြီး ပြန်စစ်တယ် (retries)။
        """
        report = None
        best_score = -1
        for attempt in range(max(1, int(retries))):
            current = self._discover_once()
            score = sum(len(w.get("elements", [])) for w in current["windows"])
            matched = sum(1 for w in current["windows"] for row in w.get("elements", [])
                          if row.get("matched_label"))
            if score > best_score:
                report, best_score = current, score
            if matched or score >= 12 or attempt + 1 >= max(1, int(retries)):
                break
            self.log.info("ပထမလှည့်မှာ element %d ခုပဲ ရတယ် — %.1fs စောင့်ပြီး ပြန်စစ်မယ် "
                          "(Chromium a11y tree ဆောက်ချိန်)", score, retry_wait)
            time.sleep(max(0.2, retry_wait))
        report = report or self._discover_once()

        if save_dir is not None:
            save_dir.mkdir(parents=True, exist_ok=True)
            out = save_dir / ("discover_%s.json" % time.strftime("%Y%m%d_%H%M%S"))
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            report["saved_to"] = str(out)
        return report


# --------------------------------------------------------------------------
# Global hotkeys (ctypes RegisterHotKey - extra dependency မလို)
# --------------------------------------------------------------------------
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]


def parse_hotkey(spec: str) -> Optional[Tuple[int, int]]:
    """'ctrl+alt+a' -> (modifiers, virtual key)"""
    if not spec:
        return None
    parts = [p.strip().lower() for p in str(spec).split("+") if p.strip()]
    if not parts:
        return None
    mods = 0
    key = None
    for part in parts:
        if part in ("ctrl", "control"):
            mods |= MOD_CONTROL
        elif part == "alt":
            mods |= MOD_ALT
        elif part == "shift":
            mods |= MOD_SHIFT
        elif part in ("win", "super", "cmd"):
            mods |= MOD_WIN
        else:
            key = part
    if key is None:
        return None
    if len(key) == 1:
        vk = ord(key.upper())
    else:
        names = {
            "space": 0x20, "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B,
            "tab": 0x09, "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
            "pageup": 0x21, "pagedown": 0x22, "up": 0x26, "down": 0x28,
            "left": 0x25, "right": 0x27,
        }
        if key in names:
            vk = names[key]
        elif re.fullmatch(r"f\d{1,2}", key):
            vk = 0x6F + int(key[1:])
        elif re.fullmatch(r"0x[0-9a-f]+", key):
            vk = int(key, 16)
        else:
            return None
    return (mods | MOD_NOREPEAT, vk)


class HotkeyManager:
    """Global hotkey တွေကို သီးသန့် thread မှာ နားထောင်တယ်။"""

    def __init__(self, bindings: Dict[str, Tuple[str, Callable[[], None]]],
                 logger: logging.Logger, on_error: Optional[Callable[[str], None]] = None):
        self.bindings = bindings
        self.log = logger
        self.on_error = on_error
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._actions: Dict[int, Callable[[], None]] = {}
        self._ids: List[int] = []
        self.registered: Dict[str, bool] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        next_id = 0xA000
        for name, (spec, action) in self.bindings.items():
            parsed = parse_hotkey(spec)
            if not parsed:
                self.registered[name] = False
                if self.on_error:
                    self.on_error("%s hotkey မမှန်ပါ: %r" % (name, spec))
                continue
            mods, vk = parsed
            hotkey_id = next_id
            next_id += 1
            if user32.RegisterHotKey(None, hotkey_id, mods, vk):
                self._actions[hotkey_id] = action
                self._ids.append(hotkey_id)
                self.registered[name] = True
                self.log.info("Hotkey တင်ပြီး: %s (%s)", name, spec)
            else:
                self.registered[name] = False
                error = ctypes.get_last_error()
                if self.on_error:
                    self.on_error("%s hotkey (%s) ကို တင်လို့မရပါ (err=%s) - app တခြားက ယူထားနိုင်တယ်"
                                  % (name, spec, error))
        message = wt.MSG()
        try:
            while True:
                ret = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if ret in (0, -1):
                    break
                if message.message == WM_HOTKEY:
                    action = self._actions.get(int(message.wParam))
                    if action:
                        try:
                            action()
                        except Exception as exc:
                            self.log.exception("hotkey action error: %s", exc)
        finally:
            for hotkey_id in self._ids:
                try:
                    user32.UnregisterHotKey(None, hotkey_id)
                except Exception:
                    pass

    def stop(self) -> None:
        if self._thread_id:
            try:
                user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
