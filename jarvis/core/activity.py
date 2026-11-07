"""
jarvis.core.activity
====================
Persistent activity log — every command Jarvis processes is recorded
with timestamp, intent, plugin and confidence. The web UI reads it.
"""

from __future__ import annotations

import json
import os
from datetime import datetime


class ActivityLog:
    def __init__(self, data_dir: str):
        self.dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "activity.jsonl")

    def append(self, entry: dict) -> None:
        entry = dict(entry)
        entry.setdefault("ts", datetime.now().isoformat(timespec="seconds"))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def recent(self, n: int = 50) -> list:
        if not os.path.exists(self.path):
            return []
        entries = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(entries[-n:]))

    def count(self) -> int:
        if not os.path.exists(self.path):
            return 0
        with open(self.path, encoding="utf-8") as f:
            return sum(1 for _ in f)
