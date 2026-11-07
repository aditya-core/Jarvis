"""
jarvis.plugins.web
==================
Web search via DuckDuckGo (free, no API key, no account).
"""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup


class WebPlugin:
    name = "web"
    intents = ["web_search"]

    def __init__(self, web_cfg: dict | None = None):
        web_cfg = web_cfg or {}
        self.backend = web_cfg.get("backend", "duckduckgo")

    def run(self, cmd, ctx) -> str:
        q = cmd.entity.strip()
        if not q:
            return "🔍 What should I search for?"
        try:
            return self.search(q)
        except Exception as e:
            return (f"⚠️ Web search unavailable: {e}\n"
                    f"   Try manually: https://www.google.com/search?q={unquote(q)}")

    @staticmethod
    def _unwrap(href: str) -> str:
        """DDG redirect links -> real URL."""
        try:
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            if "uddg" in qs:
                return unquote(qs["uddg"][0])
        except Exception:
            pass
        return href

    def search(self, q: str, n: int = 5) -> str:
        if self.backend != "duckduckgo":
            return f"⚠️ Unknown backend: {self.backend}"
        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0 Safari/537.36"),
        }
        results = []
        try:
            resp = requests.post("https://html.duckduckgo.com/html/",
                                 data={"q": q}, headers=headers, timeout=15)
            resp.raise_for_status()
            results = self._parse(resp.text, n)
        except Exception:
            # fallback: DDG lite (simpler, fewer blocks)
            resp = requests.get("https://lite.duckduckgo.com/lite/",
                                params={"q": q}, headers=headers, timeout=15)
            resp.raise_for_status()
            results = self._parse(resp.text, n)
        if not results:
            return "🔍 No results found."
        lines = [f"🔍 Results for \"{q}\":"]
        for i, (title, url, snip) in enumerate(results, 1):
            lines.append(f"{i}. {title}\n   {url}\n   {snip[:180]}")
        return "\n".join(lines)

    def _parse(self, html: str, n: int) -> list:
        """Parse DDG HTML (.result__a) or lite (.result-link) results."""
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for a in soup.select(".result__a")[:n]:
            res = a.find_parent(".result")
            snip = res.select_one(".result__snippet") if res else None
            results.append((a.get_text(" ", strip=True),
                            self._unwrap(a.get("href") or ""),
                            snip.get_text(" ", strip=True) if snip else ""))
        if not results:  # lite layout
            for a in soup.select("a.result-link")[:n]:
                snip = a.find_next(class_="result-snippet")
                results.append((a.get_text(" ", strip=True),
                                self._unwrap(a.get("href") or ""),
                                snip.get_text(" ", strip=True) if snip else ""))
        return results
