"""
jarvis.core.brain
=================
Local LLM access via Ollama. Everything runs on your machine — no data
leaves it. If Ollama is not running, Jarvis degrades gracefully to pure
rule-based mode (no AI needed for core commands).
"""

from __future__ import annotations

import json
import re

import requests


class Brain:
    def __init__(self, cfg: dict):
        llm = (cfg or {}).get("llm", {}) or {}
        self.enabled = llm.get("enabled", True)
        self.base_url = llm.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = llm.get("model", "qwen2.5:7b")
        self.timeout = llm.get("timeout", 60)
        self._available = None

    def available(self) -> bool:
        """True if a local Ollama server is reachable."""
        if not self.enabled:
            return False
        if self._available is None:
            try:
                r = requests.get(f"{self.base_url}/api/tags", timeout=3)
                self._available = r.status_code == 200
            except Exception:
                self._available = False
        return self._available

    def chat(self, messages: list, temperature: float = 0.3) -> str | None:
        """Send a chat request to the local model. Returns None if offline."""
        if not self.available():
            return None
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")

    def classify(self, text: str) -> dict | None:
        """Ask the local LLM to rewrite messy input into one of our intents.
        Returns {"intent", "entity", "reply"} or None if unavailable/failed."""
        if not self.available():
            return None
        prompt = (
            "Rewrite the user's message into one clear instruction.\n"
            "Allowed intents: note, show_notes, reminder, screenshot, "
            "web_search, open_app, open_file, system_info, time, greet, "
            "help, exit, run_cmd, chat.\n"
            "Reply with ONLY this JSON, no other text: "
            '{"intent": "...", "entity": "...", "reply": "..."}\n'
            "- intent: best matching intent id\n"
            "- entity: the key object (app name, note text, search query, ...)\n"
            "- reply: the full corrected instruction, ready to execute\n"
            f"User: {text}"
        )
        try:
            raw = self.chat([{"role": "user", "content": prompt}], temperature=0.0)
        except Exception:
            return None
        if not raw:
            return None
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        return data if data.get("intent") or data.get("reply") else None
