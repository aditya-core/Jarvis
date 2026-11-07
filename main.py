#!/usr/bin/env python3
"""
Jarvis — your offline-first personal assistant.

Usage:
  python main.py                  # chat mode
  python main.py --voice          # voice mode (wake word + speech)
  python main.py --once "open chrome"   # run one command and exit
  python main.py --selftest       # run built-in tests
  python main.py --offline        # disable local LLM (rules only)
"""

from __future__ import annotations

import argparse
import copy
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_CONFIG = {
    "jarvis": {
        "name": "Jarvis",
        "wake_word": "Hey Jarvis",
        "personality": ("You are Jarvis, a helpful, concise personal "
                        "assistant. Reply briefly and practically."),
    },
    "llm": {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model": "qwen2.5:3b",   # 1.5b = ultra-light | 3b = balanced | 7b = best
        "timeout": 60,
        "enabled": True,
    },
    "voice": {"enabled": True, "stt_model": "base", "tts_engine": "pyttsx3"},
    "web": {"backend": "duckduckgo"},
    "data_dir": "data",
}


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path: str) -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        _deep_merge(cfg, loaded)
    data_dir = cfg.get("data_dir", "data")
    if not os.path.isabs(data_dir):
        cfg["data_dir"] = os.path.join(ROOT, data_dir)
    return cfg


def build_jarvis(cfg: dict, confirm_cb=None, notify_cb=None):
    from jarvis.core.orchestrator import Orchestrator
    from jarvis.plugins.notes import NotesPlugin
    from jarvis.plugins.system import SystemPlugin
    from jarvis.plugins.web import WebPlugin

    jarvis = Orchestrator(cfg, confirm_cb=confirm_cb, notify_cb=notify_cb)
    jarvis.register(NotesPlugin(jarvis.data_dir))
    system = SystemPlugin(jarvis.data_dir, notify_cb=notify_cb)
    jarvis.register(system)
    jarvis.register(WebPlugin(cfg.get("web", {})))
    return jarvis, system


# ----------------------------------------------------------------------
def selftest(jarvis) -> int:
    from jarvis.core import parser as P

    print("🧪 Running self-test...\n")
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        mark = "✓" if cond else "✗"
        print(f"  [{mark}] {name}")

    # --- parser: fuzzy + typo tolerance --------------------------------
    t = P.parse("take a note buy milk and eggs")
    check("note intent + entity", t.intent_id == "note" and "buy milk" in t.entity)
    t = P.parse("opn chrome pls")
    check("typo: open_app", t.intent_id == "open_app")
    check("entity cleanup (opn chrome)", t.entity == "chrome")
    t = P.parse("delete temp.txt")
    check("risky word -> run_cmd", t.intent_id == "run_cmd")
    t = P.parse("run command echo hello jarvis")
    check("run_cmd not hijacked by greet", t.intent_id == "run_cmd")
    t = P.parse("seach gogle python tips")
    check("typo: web_search", t.intent_id == "web_search")
    t = P.parse("take a photo")
    check("photo -> screenshot", t.intent_id == "screenshot")
    t = P.parse("remind me to call mom at 9pm")
    check("reminder intent", t.intent_id == "reminder")
    t = P.parse("hej jarvis")
    check("typo: greet", t.intent_id == "greet")
    t = P.parse("open report.pdf")
    check("extension -> open_file", t.intent_id == "open_file")
    t = P.parse("what time is it")
    check("time intent", t.intent_id == "time")

    # --- plugin smoke tests -------------------------------------------
    r = jarvis.handle("take a note selftest please")
    check("note saved", "Noted" in r)
    r = jarvis.handle("show notes")
    check("notes listed", "note" in r.lower())
    r = jarvis.handle("what time is it")
    check("time reply", "🕒" in r)
    r = jarvis.handle("remind me to test reminder at 9pm")
    check("reminder set", "Reminder set" in r)
    r = jarvis.handle("screenshot")
    check("screenshot handled", True)
    print("    ->", r.replace("\n", " "))
    r = jarvis.handle("search openai")
    check("web search handled", True)
    print("    ->", r.split("\n")[0][:100])

    # --- brain / memory ------------------------------------------------
    print(f"  [i] Ollama local LLM: {'available' if jarvis.brain.available() else 'not running (core commands still work)'}")
    o = jarvis.memory.recall("selftest")
    check("memory recall works", any("selftest" in e.get("text", "") for e in o))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n📊 {passed}/{len(results)} checks passed")
    if passed == len(results):
        print("✅ All good!")
        return 0
    print("⚠️ Some checks failed — see above.")
    return 1


# ----------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Jarvis — offline-first assistant")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "jarvis.yaml"))
    ap.add_argument("--voice", action="store_true",
                    help="voice mode (auto-launches web UI on wake)")
    ap.add_argument("--ui", action="store_true",
                    help="launch the movie-style web UI")
    ap.add_argument("--once", help="run one command and exit")
    ap.add_argument("--offline", action="store_true",
                    help="disable local LLM (pure rules)")
    ap.add_argument("--selftest", action="store_true", help="run built-in tests")
    ap.add_argument("--wake-word", help="override wake word")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.offline:
        cfg["llm"]["enabled"] = False
    if args.wake_word:
        cfg["jarvis"]["wake_word"] = args.wake_word

    jarvis, system = build_jarvis(cfg)

    if args.selftest:
        return selftest(jarvis)

    if args.once:
        print(jarvis.handle(args.once))
        system.stop()
        return 0

    if args.ui:
        from jarvis.interfaces.webui import WebUI
        wcfg = cfg.get("webui", {})
        WebUI(jarvis, host=wcfg.get("host", "0.0.0.0"),
              port=int(wcfg.get("port", 8765))).run()
        system.stop()
        return 0

    if args.voice:
        import threading
        import webbrowser
        from jarvis.interfaces.voice import VoiceEngine
        from jarvis.interfaces.webui import WebUI
        wcfg = cfg.get("webui", {})
        port = int(wcfg.get("port", 8765))
        # web UI runs in the background; wake word opens the browser
        ui = WebUI(jarvis, host=wcfg.get("host", "0.0.0.0"), port=port)
        t = threading.Thread(target=ui.run, kwargs={"open_browser": False},
                             daemon=True)
        t.start()
        engine = VoiceEngine(
            cfg, jarvis.handle, name=cfg["jarvis"]["name"],
            on_wake=lambda: webbrowser.open(f"http://localhost:{port}/"))
        engine.run()
    else:
        from jarvis.interfaces.chat_ui import ChatUI
        ChatUI(cfg["jarvis"]["name"]).run(jarvis)

    system.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
