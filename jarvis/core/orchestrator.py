"""
jarvis.core.orchestrator
========================
The brain's dispatcher. Parses input (fuzzy first, local LLM as backup),
routes to the right plugin, keeps memory, records activity + thinking
trace, and handles fallbacks.
"""

from __future__ import annotations

from datetime import datetime

from . import parser as P
from .activity import ActivityLog
from .brain import Brain
from .memory import Memory
from .permissions import Permissions

HELP_TEXT = (
    "🤖 I can do a lot locally — try:\n"
    "   📝  \"take a note buy milk\" / \"show notes\"\n"
    "   🚀  \"open chrome\" / \"open report.pdf\" / \"open the file report.pdf\"\n"
    "   📸  \"screenshot\" / \"take a photo\"\n"
    "   🔍  \"search python tutorials\"\n"
    "   ⏰  \"remind me to call mom at 9pm\"\n"
    "   💻  \"system status\" / \"what time is it\"\n"
    "   💬  ask me anything — with Ollama running I can chat too\n"
    "   (spell mistakes are fine — I figure them out)"
)


class Orchestrator:
    def __init__(self, cfg: dict, confirm_cb=None, notify_cb=None):
        self.cfg = cfg or {}
        self.data_dir = self.cfg.get("data_dir", "data")
        self.brain = Brain(self.cfg)
        self.memory = Memory(self.data_dir)
        self.activity = ActivityLog(self.data_dir)
        self.permissions = Permissions(confirm_cb)
        self.notify_cb = notify_cb
        self.plugins = {}
        self.last_thinking = {}

    def register(self, plugin) -> None:
        self.plugins[plugin.name] = plugin

    # ------------------------------------------------------------------
    def handle(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""

        llm_consulted = False
        cmd = P.parse(text)

        # Fuzzy parser unsure? Ask the local LLM to straighten it out.
        if cmd.confidence < 0.7 and self.brain.available():
            fixed = self.brain.classify(text)
            if fixed:
                llm_consulted = True
                cmd = P.parse(fixed.get("reply") or text)
                if fixed.get("intent"):
                    cmd.intent_id = fixed["intent"]
                if fixed.get("entity"):
                    cmd.entity = fixed["entity"]

        plugin = next((p for p in self.plugins.values()
                       if cmd.intent_id in p.intents), None)

        if plugin is not None:
            try:
                reply = plugin.run(cmd, self)
            except Exception as e:
                reply = f"⚠️  Something went wrong: {e}"
        elif cmd.intent_id == "help":
            reply = HELP_TEXT
        elif cmd.intent_id == "greet":
            reply = self._greet()
        elif cmd.intent_id == "exit":
            reply = "Goodbye! See you soon. 👋"
        elif self.brain.available():
            reply = self._llm_chat(text)
        else:
            reply = self._fallback(cmd)

        if reply is None:
            reply = self._fallback(cmd)

        self.memory.remember("user", text)
        self.memory.remember("jarvis", reply)

        # "AI thinking" trace — what the web UI shows
        self.last_thinking = {
            "intent": cmd.intent_id,
            "confidence": round(cmd.confidence, 2),
            "matched": cmd.matched,
            "entity": cmd.entity,
            "plugin": plugin.name if plugin else None,
            "llm_consulted": llm_consulted,
        }

        # Activity record — everything Jarvis does is logged
        self.activity.append({
            "user": text,
            "reply": reply,
            "intent": cmd.intent_id,
            "plugin": plugin.name if plugin else None,
            "confidence": round(cmd.confidence, 2),
        })
        return reply

    # ------------------------------------------------------------------
    def _greet(self) -> str:
        h = datetime.now().hour
        if h < 12:
            return "Good morning! ☀️ What can I do for you?"
        if h < 18:
            return "Good afternoon! 🌤️ What can I do for you?"
        return "Good evening! 🌙 What can I do for you?"

    def _llm_chat(self, text: str) -> str:
        facts = self.memory.profile.get("facts", [])
        mem = self.memory.recall(text, k=4)
        ctx_lines = [f"- {e['text']}" for e in mem]
        system = self.cfg.get("jarvis", {}).get("personality",
                "You are Jarvis, a helpful assistant.")
        if facts:
            system += "\nKnown facts about the user:\n" + "\n".join(facts)
        if ctx_lines:
            system += "\nRecent context:\n" + "\n".join(ctx_lines)
        reply = self.brain.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])
        if reply:
            return reply
        return self._fallback(P.parse(text))

    @staticmethod
    def _fallback(cmd) -> str:
        return (
            "😕 I didn't quite catch that. I can help with: notes, opening "
            "apps/files, screenshots, web search, reminders, system info and "
            "time. Try: \"take a note ...\", \"open chrome\", \"screenshot\", "
            "\"search ...\", \"remind me to ... at 9pm\" — or type \"help\"."
        )
