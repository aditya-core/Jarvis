"""
jarvis.core.permissions
=======================
Safety gate: risky actions (deleting, formatting, running unknown shell
commands...) must be explicitly confirmed by the user first.
"""

from __future__ import annotations

_RISKY_WORDS = (
    "delete", "remove", "format", "rm ", "del ", "uninstall", "install",
    "shutdown", "restart", "reboot", "wipe", "diskpart", "mkfs",
)


class Permissions:
    def __init__(self, confirm_cb=None):
        # confirm_cb(action_description) -> bool
        self.confirm_cb = confirm_cb or self._default_confirm

    @staticmethod
    def _default_confirm(desc: str) -> bool:
        try:
            return input(f"⚠️  {desc} — allow? [y/N] ").strip().lower() == "y"
        except EOFError:
            return False

    def is_risky(self, text: str) -> bool:
        t = text.lower()
        return any(p in t for p in _RISKY_WORDS)

    def confirm(self, desc: str) -> bool:
        return self.confirm_cb(desc)
