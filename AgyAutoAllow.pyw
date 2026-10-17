# -*- coding: utf-8 -*-
"""
AgyAutoAllow.pyw
================
ဒီဖိုင်ကို double-click လုပ်ရင် console window မပေါ်ဘဲ tray app စတင်မယ်။
(pythonw.exe နဲ့ အလိုအလျောက် run ဖြစ်တာမို့ console မပေါ်ဘူး)
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

import agy_auto_allow  # noqa: E402

sys.argv = ["agy_auto_allow.py"]
sys.exit(agy_auto_allow.main())
