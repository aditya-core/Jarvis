"""
jarvis.core.phrases
==================
Jarvis's personality — canned phrases loaded from config/phrases.yaml.
This is how you 'train' Jarvis locally: edit phrases, restart, done.
No code changes needed.
"""

from __future__ import annotations

import os
from datetime import datetime

import yaml

DEFAULTS = {
    "address": "sir",
    "wake": "Yes, sir?",
    "wake_launch": "Yes, sir. Jarvis online — what's your command?",
    "welcome": [
        "Good morning, sir. What can I do for you?",
        "Good afternoon, sir. What can I do for you?",
        "Good evening, sir. What can I do for you?",
    ],
    "goodbye": "Goodbye, sir. See you soon. 👋",
    "note_saved": '📝 Noted, sir. "{content}"\n   saved to {path}',
    "notes_empty": "📭 No notes yet, sir — say \"take a note ...\"",
    "opening_app": "🚀 Opening {app}, sir...",
    "app_not_found": '🚀 Couldn\'t find "{app}", sir. Try another name.',
    "opening_file": "📂 Opening {file}, sir...",
    "file_not_found": '📂 Couldn\'t find "{file}", sir. Try the full path.',
    "screenshot_saved": "📸 Screenshot saved, sir: {path}",
    "screenshot_fail": "⚠️ Screenshot failed: {err}",
    "reminder_set": "⏰ Reminder set, sir. {summary}",
    "reminder_no_time": '⏰ Sure, sir — but when? Example: "remind me to call mom at 9pm"',
    "time": "🕒 {time}, sir",
    "system_header": "💻 System status:",
    "search_results": '🔍 Results for "{q}":',
    "search_unavailable": "⚠️ Web search unavailable: {err}",
    "fallback": ("😕 I didn't quite catch that, sir. I can help with: notes, "
                 "opening apps/files, screenshots, web search, reminders, "
                 "system info and time. Try \"take a note ...\", \"open "
                 "chrome\", \"screenshot\", \"search ...\", \"remind me to "
                 "... at 9pm\" — or type \"help\"."),
    "help": ("🤖 I can do a lot locally — try:\n"
             "   📝  \"take a note buy milk\" / \"show notes\"\n"
             "   🚀  \"open chrome\" / \"open report.pdf\"\n"
             "   📸  \"screenshot\" / \"take a photo\"\n"
             "   🔍  \"search python tutorials\"\n"
             "   ⏰  \"remind me to call mom at 9pm\"\n"
             "   💻  \"system status\" / \"what time is it\"\n"
             "   (spell mistakes are fine — I figure them out)"),
}


def load_phrases(path: str) -> dict:
    """Load phrases from yaml, merging over the defaults."""
    ph = dict(DEFAULTS)
    try:
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        for k, v in loaded.items():
            if k == "phrases" and isinstance(v, dict):
                ph.update(v)
            else:
                ph[k] = v
    except Exception:
        pass
    return ph


def P(phrases: dict, key: str, default: str | None = None, **kw) -> str:
    """Get a phrase and fill its {placeholders}."""
    ph = (phrases or {}).get(key) or default or DEFAULTS.get(key, key)
    try:
        return str(ph).format(**kw)
    except Exception:
        return str(ph)


def welcome_phrase(phrases: dict) -> str:
    """Time-based welcome message (morning/afternoon/evening)."""
    w = (phrases or {}).get("welcome")
    if isinstance(w, list) and w:
        h = datetime.now().hour
        idx = 0 if h < 12 else (1 if h < 18 else 2)
        return str(w[min(idx, len(w) - 1)])
    return DEFAULTS["welcome"][0]
