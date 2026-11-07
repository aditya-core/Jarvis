"""
jarvis.plugins.notes
====================
Take notes, show notes. Notes are saved as markdown files in data/notes/.
'I am ...' statements are also stored as user profile facts.
"""

from __future__ import annotations

import glob
import os
import re
from datetime import datetime


class NotesPlugin:
    name = "notes"
    intents = ["note", "show_notes"]

    def __init__(self, data_dir: str):
        self.dir = os.path.join(data_dir, "notes")
        os.makedirs(self.dir, exist_ok=True)

    def run(self, cmd, ctx) -> str:
        if cmd.intent_id == "note":
            return self._save(cmd, ctx)
        if cmd.intent_id == "show_notes":
            return self._show()
        return None

    def _save(self, cmd, ctx) -> str:
        content = cmd.entity.strip()
        if not content:
            return "📝 What should I note down?"
        now = datetime.now()
        title = " ".join(content.split()[:6])
        fname = os.path.join(self.dir, f"{now:%Y%m%d_%H%M%S}.md")
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}\n\n_Created: {now:%Y-%m-%d %H:%M}__\n")

        # Profile facts: "I am a student" -> remembered long-term
        m = re.match(r"^i (?:am|'m|is a) (.+)$", content.lower())
        if m:
            ctx.memory.profile_fact(m.group(1).strip())

        return f"📝 Noted: \"{content}\"\n   saved to {fname}"

    def _show(self) -> str:
        files = sorted(glob.glob(os.path.join(self.dir, "*.md")), reverse=True)[:8]
        if not files:
            return "📭 No notes yet — say \"take a note ...\""
        lines = ["📋 Recent notes:"]
        for f in files:
            try:
                with open(f, encoding="utf-8") as fh:
                    head = fh.read(200).split("\n")[0].lstrip("# ").strip()
            except Exception:
                head = os.path.basename(f)
            lines.append("  • " + head)
        return "\n".join(lines)
