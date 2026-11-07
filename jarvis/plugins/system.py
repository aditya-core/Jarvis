"""
jarvis.plugins.system
=====================
Local system control:
  - open apps (with fuzzy name resolution + common aliases)
  - open files (path, or fuzzy search in Desktop/Documents/Downloads)
  - screenshots ("take a photo")
  - reminders with background timer
  - system status (disk, memory, battery, CPU)
  - run shell commands (with permission gate)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta

import psutil

from ..core.parser import APP_ALIASES, similar


def _open_target(path: str) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 — user explicitly asked to open it
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError as e:
            raise RuntimeError("no desktop opener found") from e


class SystemPlugin:
    name = "system"
    intents = ["open_app", "open_file", "screenshot", "system_info",
               "time", "reminder", "run_cmd"]

    def __init__(self, data_dir: str, notify_cb=None):
        self.data_dir = data_dir
        self.reminders_path = os.path.join(data_dir, "reminders.json")
        self.notify_cb = notify_cb
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the reminder poller thread."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._poll_reminders,
                                            daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------
    def run(self, cmd, ctx) -> str:
        handler = {
            "open_app": self._open_app,
            "open_file": self._open_file,
            "screenshot": self._screenshot,
            "system_info": self._system_info,
            "time": self._time,
            "reminder": self._reminder,
            "run_cmd": self._run_cmd,
        }.get(cmd.intent_id)
        if handler is None:
            return None
        return handler(cmd, ctx)

    # ------------------------------------------------------------------
    def _resolve_app(self, name: str) -> str | None:
        name = name.strip().strip('"').strip("'")
        if not name:
            return None
        if os.path.exists(name):
            return name
        if re.search(r"\.(exe|lnk|bat|cmd|msi|app)$", name, re.I):
            return name if os.path.exists(name) else None
        lname = name.lower()
        if lname in APP_ALIASES:
            lname = APP_ALIASES[lname]
        found = shutil.which(lname)
        if found:
            return found
        return self._find_program(lname)

    def _find_program(self, name_l: str) -> str | None:
        """Fuzzy-search common install locations for a program."""
        search_dirs = []
        if sys.platform == "win32":
            for env in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
                d = os.environ.get(env)
                if d and os.path.isdir(d):
                    search_dirs.append(d)
            sm = os.path.join(os.environ.get("APPDATA", ""), "Microsoft",
                              "Windows", "Start Menu", "Programs")
            if os.path.isdir(sm):
                search_dirs.append(sm)
        else:
            search_dirs = ["/usr/bin", "/usr/local/bin", "/opt", "/Applications"]
        for d in search_dirs:
            for root, _, files in os.walk(d):
                for f in files:
                    base = f.lower()
                    if similar(base, name_l + ".exe") >= 0.8 or \
                       similar(base, name_l) >= 0.85:
                        return os.path.join(root, f)
        return None

    def _open_app(self, cmd, ctx) -> str:
        target = self._resolve_app(cmd.entity)
        if not target:
            return f"🚀 Couldn't find \"{cmd.entity or 'that app'}\". Try another name."
        try:
            _open_target(target)
        except Exception as e:
            return f"🚀 Couldn't launch {os.path.basename(target)}: {e}"
        return f"🚀 Opening {os.path.basename(target)}..."

    # ------------------------------------------------------------------
    def _find_file(self, name: str) -> str | None:
        if os.path.exists(name):
            return name
        lname = name.lower().strip()
        dirs = [os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Downloads")]
        for d in dirs:
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if similar(f.lower(), lname) >= 0.8:
                        return os.path.join(root, f)
        return None

    def _open_file(self, cmd, ctx) -> str:
        target = self._find_file(cmd.entity)
        if not target:
            return (f"📂 Couldn't find \"{cmd.entity or 'that file'}\". "
                    "Try the full path.")
        try:
            _open_target(target)
        except Exception as e:
            return f"📂 Couldn't open {os.path.basename(target)}: {e}"
        return f"📂 Opening {os.path.basename(target)}..."

    # ------------------------------------------------------------------
    def _screenshot(self, cmd, ctx) -> str:
        try:
            import mss
        except ImportError:
            return "⚠️ Screenshot module missing — run: pip install mss"
        out_dir = os.path.join(self.data_dir, "screenshots")
        os.makedirs(out_dir, exist_ok=True)
        try:
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[1])
            out = os.path.join(out_dir, f"shot_{datetime.now():%Y%m%d_%H%M%S}.png")
            mss.tools.to_png(shot.rgb, shot.size, output=out)
            return f"📸 Screenshot saved: {out}"
        except Exception as e:
            return f"⚠️ Screenshot failed: {e}"

    # ------------------------------------------------------------------
    def _system_info(self, cmd, ctx) -> str:
        lines = ["💻 System status:"]
        lines.append(f"  • OS: {sys.platform} ({os.name})")
        vm = psutil.virtual_memory()
        lines.append(f"  • RAM: {vm.used // (1024**2)} MB / "
                     f"{vm.total // (1024**2)} MB ({vm.percent}% used)")
        try:
            disk = psutil.disk_usage("/")
            lines.append(f"  • Disk: {disk.used // (1024**3)} GB / "
                         f"{disk.total // (1024**3)} GB ({disk.percent}% used)")
        except Exception:
            pass
        try:
            if psutil.sensors_battery() is not None:
                lines.append(f"  • Battery: {psutil.sensors_battery().percent}%")
        except Exception:
            pass
        lines.append(f"  • CPU: {psutil.cpu_percent(interval=0.5)}% busy")
        return "\n".join(lines)

    def _time(self, cmd, ctx) -> str:
        now = datetime.now()
        return f"🕒 {now:%H:%M} — {now:%A, %B %d, %Y}"

    # ------------------------------------------------------------------
    def _parse_when(self, text: str) -> datetime | None:
        """Parse 'at 9pm', 'at 14:30', 'in 5 minutes', 'tomorrow', ..."""
        t = text.lower()
        now = datetime.now()
        m = re.search(r"in\s+(\d+)\s*(min(?:ute)?s?|hr|hours?|h)\b", t)
        if m:
            n = int(m.group(1))
            unit = m.group(2)[0].lower()
            delta = timedelta(minutes=n) if unit in "mmin" else timedelta(hours=n)
            return now + delta
        day = None
        if re.search(r"\btomorrow\b", t):
            day = now.date() + timedelta(days=1)
        elif re.search(r"\btoday\b", t):
            day = now.date()
        m = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\b", t)
        if m:
            hh = int(m.group(1))
            mm = int(m.group(2) or 0)
            ampm = (m.group(3) or "").lower().replace(".", "")
            if ampm == "pm" and hh < 12:
                hh += 12
            if ampm == "am" and hh == 12:
                hh = 0
            base = day or now.date()
            dt = datetime(base.year, base.month, base.day, hh % 24, mm)
            if not day and dt <= now:
                dt += timedelta(days=1)
            return dt
        if day is not None:
            return datetime(day.year, day.month, day.day, 9, 0)
        return None

    def _reminder(self, cmd, ctx) -> str:
        raw = cmd.raw_text.strip()
        entity = cmd.entity.strip()
        if not entity:
            return "⏰ What should I remind you about?"
        # parse the time from the full sentence (keeps 'at'/'in' intact)
        dt = self._parse_when(raw)
        if dt is None:
            return ("⏰ Sure — but when? Example: "
                    "\"remind me to call mom at 9pm\"")
        # clean the message: drop the trailing time phrase
        content = entity
        content = re.sub(r"\s*\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?\s*"
                         r"(?:minutes?|mins?|hours?|hrs?|h|m)?\s*$",
                         "", content, flags=re.I).strip()
        content = re.sub(r"\s*(?:at|on|tomorrow|today)\s*$", "",
                         content, flags=re.I).strip()
        if not content:
            return "⏰ What should I remind you about?"
        reminder = {"text": content, "due": dt.isoformat(timespec="minutes"),
                    "done": False}
        data = []
        if os.path.exists(self.reminders_path):
            try:
                with open(self.reminders_path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = []
        data.append(reminder)
        with open(self.reminders_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return f"⏰ Reminder set: {content} — at {dt:%H:%M} on {dt:%A}"

    def _poll_reminders(self) -> None:
        while not self._stop.is_set():
            try:
                self._fire_due()
            except Exception:
                pass
            self._stop.wait(20)

    def _fire_due(self) -> None:
        if not os.path.exists(self.reminders_path):
            return
        try:
            with open(self.reminders_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        changed = False
        now = datetime.now()
        for r in data:
            if r.get("done"):
                continue
            try:
                due = datetime.fromisoformat(r["due"])
            except Exception:
                continue
            if now >= due:
                r["done"] = True
                changed = True
                msg = f"⏰ Reminder: {r['text']}"
                print("\n" + msg)
                if self.notify_cb:
                    self.notify_cb(msg)
        if changed:
            with open(self.reminders_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    def _run_cmd(self, cmd, ctx) -> str:
        cmd_text = cmd.entity.strip()
        if not cmd_text:
            return "⚙️ What command should I run?"
        if ctx.permissions.is_risky(cmd_text):
            if not ctx.permissions.confirm(f"Run command: {cmd_text}"):
                return "🚫 Cancelled — nothing was run."
        try:
            proc = subprocess.run(cmd_text, shell=True, capture_output=True,
                                  text=True, timeout=60)
            out = (proc.stdout or "") + (proc.stderr or "")
            out = out.strip()
            if not out:
                return "✅ Command finished (no output)."
            return "⚙️ Output:\n" + out[:1500] + ("\n... (truncated)" if len(out) > 1500 else "")
        except subprocess.TimeoutExpired:
            return "⚠️ Command timed out (60s limit)."
        except Exception as e:
            return f"⚠️ Command failed: {e}"
