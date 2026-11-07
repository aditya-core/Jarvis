"""
jarvis.core.memory
==================
Simple local memory: conversation log + user profile facts.
Notes/reminders/screenshots are stored by their plugins in data/.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime


class Memory:
    def __init__(self, data_dir: str):
        self.dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "memory.jsonl")
        self.profile_path = os.path.join(data_dir, "profile.json")
        self.profile = self._load_profile()

    def _load_profile(self) -> dict:
        try:
            with open(self.profile_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"facts": []}

    def _save_profile(self) -> None:
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=2, ensure_ascii=False)

    def remember(self, role: str, text: str) -> None:
        """Append one conversation turn to the log."""
        entry = {"ts": datetime.now().isoformat(timespec="seconds"),
                 "role": role, "text": text}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def recall(self, query: str, k: int = 5) -> list:
        """Keyword-overlap search over past conversation (simple but works)."""
        q = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not q or not os.path.exists(self.path):
            return []
        scored = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                tokens = set(re.findall(r"[a-z0-9]+", e.get("text", "").lower()))
                score = len(q & tokens)
                if score:
                    scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:k]]

    def profile_fact(self, fact: str) -> None:
        """Store a fact about the user (e.g. 'I am a student')."""
        fact = fact.strip().rstrip(".")
        if fact and fact not in self.profile["facts"]:
            self.profile["facts"].append(fact)
            self._save_profile()
