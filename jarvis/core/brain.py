"""
jarvis.core.brain
=================
Local LLM access — fully offline. Two engines, chosen in config:

- **llamacpp**: llama.cpp via llama-cpp-python. In-process, CPU-only,
  no installer, no CUDA. LIGHTEST option — ideal for old PCs.
  Setup: `pip install llama-cpp-python` + one .gguf model file.
- **ollama**: Ollama HTTP server on localhost:11434.

If neither is available, Jarvis degrades gracefully to pure rule-based
mode (core commands need no AI at all).
"""

from __future__ import annotations

import json
import os
import re

import requests


def _classify_prompt(text: str) -> str:
    """Prompt that turns messy input into a structured instruction."""
    return (
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


def _parse_json_reply(raw: str) -> dict | None:
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


class Brain:
    """Ollama backend (HTTP server on localhost)."""

    def __init__(self, cfg: dict):
        llm = (cfg or {}).get("llm", {}) or {}
        self.enabled = llm.get("enabled", True)
        self.base_url = llm.get("base_url", "http://localhost:11434").rstrip("/")
        self.model = llm.get("model", "qwen2.5:3b")
        self.timeout = llm.get("timeout", 60)
        self._available = None

    def available(self) -> bool:
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
        if not self.available():
            return None
        try:
            raw = self.chat(
                [{"role": "user", "content": _classify_prompt(text)}],
                temperature=0.0,
            )
        except Exception:
            return None
        return _parse_json_reply(raw or "")


class LlamaCPPBrain:
    """llama.cpp backend (in-process, CPU-only).

    Lightest option: `pip install llama-cpp-python` + one .gguf model.
    No installer, no CUDA, no background server.
    """

    def __init__(self, cfg: dict):
        llm = (cfg or {}).get("llm", {}) or {}
        self.enabled = llm.get("enabled", True)
        self.model_path = llm.get("model_path", "")
        self.n_ctx = int(llm.get("n_ctx", 2048))
        self._llm = None
        self._available = None

    def available(self) -> bool:
        if not self.enabled:
            return False
        if self._available is None:
            try:
                from llama_cpp import Llama
                if not self.model_path or not os.path.exists(self.model_path):
                    self._available = False
                else:
                    self._llm = Llama(model_path=self.model_path,
                                      n_ctx=self.n_ctx)
                    self._available = True
            except Exception:
                self._available = False
        return self._available

    def chat(self, messages: list, temperature: float = 0.3) -> str | None:
        if not self.available():
            return None
        out = self._llm.create_chat_completion(
            messages=messages, max_tokens=512, temperature=temperature,
        )
        return out["choices"][0]["message"]["content"]

    def classify(self, text: str) -> dict | None:
        if not self.available():
            return None
        try:
            out = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": _classify_prompt(text)}],
                max_tokens=128, temperature=0.0,
            )
            raw = out["choices"][0]["message"]["content"]
        except Exception:
            return None
        return _parse_json_reply(raw or "")


class LlamaServerBrain:
    """llama.cpp llama-server backend (OpenAI-compatible HTTP API).

    Runs the standalone llama.cpp binary — no pip, no compiler, no
    installer. Steps:
      1) Download the Windows CPU build from
         https://github.com/ggml-org/llama.cpp/releases/latest
         (file like llama-bXXXX-bin-win-cpu-x64.zip), extract anywhere
      2) Download a small .gguf model (~1 GB) from huggingface.co/Qwen
      3) Start the server:
           llama-server.exe -m model.gguf --port 8080
    """

    def __init__(self, cfg: dict):
        llm = (cfg or {}).get("llm", {}) or {}
        self.enabled = llm.get("enabled", True)
        self.base_url = llm.get("base_url", "http://localhost:8080/v1").rstrip("/")
        self.model = llm.get("model", "local")
        self.timeout = llm.get("timeout", 60)
        self._available = None

    def available(self) -> bool:
        if not self.enabled:
            return False
        if self._available is None:
            try:
                r = requests.get(f"{self.base_url}/models", timeout=3)
                self._available = r.status_code == 200
            except Exception:
                self._available = False
        return self._available

    def chat(self, messages: list, temperature: float = 0.3) -> str | None:
        if not self.available():
            return None
        r = requests.post(
            f"{self.base_url}/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": 512,
                "temperature": temperature,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def classify(self, text: str) -> dict | None:
        if not self.available():
            return None
        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user",
                                  "content": _classify_prompt(text)}],
                    "max_tokens": 128,
                    "temperature": 0.0,
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"]
        except Exception:
            return None
        return _parse_json_reply(raw or "")


def make_brain(cfg: dict):
    """Pick the brain backend from config: llamaserver | llamacpp | ollama."""
    provider = (cfg or {}).get("llm", {}).get("provider", "ollama")
    if provider == "llamacpp":
        return LlamaCPPBrain(cfg)
    if provider == "llamaserver":
        return LlamaServerBrain(cfg)
    return Brain(cfg)
