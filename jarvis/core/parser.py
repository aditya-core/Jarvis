"""
jarvis.core.parser
==================
Jarvis's offline intent parser. Turns messy, typo-ridden human input into
structured commands WITHOUT any AI — fuzzy matching tolerates spelling
mistakes and unclear phrasing. When confidence is low, the orchestrator
can hand the input to the local LLM to straighten it out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher


def similar(a: str, b: str) -> float:
    """Fuzzy similarity between two strings (0.0 .. 1.0)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on",
    "me", "my", "i", "is", "it", "please", "pls", "plz", "plese", "can", "you",
    "would", "could", "will", "do", "does", "that", "this", "want",
    "need", "get", "now", "some", "thing", "things", "up", "down",
    "there", "here", "about",
}

# Words that should route to "open a file" rather than "open an app"
_FILE_WORDS = ["file", "document", "doc", "folder", "directory", "pdf"]

# Common app aliases -> canonical program names (extend as you like)
APP_ALIASES = {
    "chrome": "chrome", "google chrome": "chrome", "chromium": "chrome",
    "vscode": "code", "vs code": "code", "visual studio code": "code",
    "firefox": "firefox",
    "spotify": "spotify",
    "vlc": "vlc",
    "discord": "discord",
    "slack": "slack",
    "notepad": "notepad",
    "calc": "calc", "calculator": "calc",
    "paint": "mspaint",
    "terminal": "wt", "cmd": "cmd", "powershell": "powershell",
    "word": "WINWORD", "excel": "EXCEL", "powerpoint": "POWERPT",
    "onenote": "ONENOTE",
    "explorer": "explorer",
    "settings": "settings",
    "teams": "teams",
    "steam": "steam",
}

# Verbs that mean "do something to the system" -> permission-gated shell
_RISKY_VERBS = (r"\b(delete|remove|del|rm|format|uninstall|install|"
                r"shutdown|restart|reboot|wipe|erase)\b")


@dataclass
class ParsedCommand:
    intent_id: str = "unknown"
    intent_name: str = "unknown"
    entity: str = ""
    raw_text: str = ""
    confidence: float = 0.0
    matched: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.confidence >= 0.55


# Order matters: earlier intents win ties (more specific first).
INTENT_SPECS = [
    {
        "id": "note",
        "name": "Take a note",
        "keywords": [
            ("take a note", 2.6), ("note that", 2.4), ("save a note", 2.2),
            ("write a note", 2.2), ("remember that", 2.2), ("jot", 1.4),
            ("note", 1.6),
        ],
    },
    {
        "id": "show_notes",
        "name": "Show my notes",
        "keywords": [
            ("show notes", 2.6), ("my notes", 2.4), ("list notes", 2.4),
            ("what are my notes", 2.6), ("notes", 1.4),
        ],
    },
    {
        "id": "reminder",
        "name": "Set a reminder",
        "keywords": [
            ("remind me", 3.0), ("reminder", 2.2), ("alarm", 1.8),
        ],
    },
    {
        "id": "screenshot",
        "name": "Take a screenshot",
        "keywords": [
            ("screenshot", 3.0), ("screen shot", 3.0), ("take a photo", 3.0),
            ("take a picture", 3.0), ("capture", 2.0), ("photo", 1.8),
            ("picture", 1.6),
        ],
    },
    {
        "id": "web_search",
        "name": "Search the web",
        "keywords": [
            ("search google for", 2.6), ("look up", 2.2), ("find online", 2.2),
            ("on the web", 2.2), ("search", 2.0), ("google", 2.0),
            ("browse", 1.8), ("web", 1.2),
        ],
    },
    {
        "id": "run_cmd",
        "name": "Run a shell command",
        "keywords": [
            ("run command", 3.5), ("execute command", 3.5), ("run this", 2.2),
        ],
    },
    {
        "id": "open_file",
        "name": "Open a file",
        "keywords": [
            ("open the file", 2.6), ("open file", 2.4),
        ],
    },
    {
        "id": "open_app",
        "name": "Open an app",
        "keywords": [
            ("open", 1.8), ("launch", 1.8), ("start", 1.2), ("run", 1.0),
            ("open app", 2.2), ("start app", 2.2),
        ],
    },
    {
        "id": "system_info",
        "name": "System status",
        "keywords": [
            ("system", 1.8), ("disk", 2.2), ("battery", 2.2), ("memory", 2.0),
            ("ram", 2.0), ("pc status", 2.4), ("computer status", 2.4),
            ("how am i doing", 2.4), ("storage", 2.0),
        ],
    },
    {
        "id": "time",
        "name": "Time & date",
        "keywords": [
            ("what time", 2.6), ("current time", 2.6), ("what day", 2.2),
            ("time", 2.2), ("date", 2.2), ("clock", 2.0),
        ],
    },
    {
        "id": "greet",
        "name": "Greeting",
        "keywords": [
            ("good morning", 2.4), ("good afternoon", 2.4), ("good evening", 2.4),
            ("how are you", 2.2), ("hello", 2.2), ("hi", 2.0), ("hey", 1.8),
            ("jarvis", 1.0),
        ],
    },
    {
        "id": "help",
        "name": "Help",
        "keywords": [
            ("what can you do", 3.0), ("help", 2.2), ("commands", 1.8),
        ],
    },
    {
        "id": "exit",
        "name": "Goodbye",
        "keywords": [
            ("good night", 2.4), ("bye", 2.4), ("exit", 2.2), ("quit", 2.2),
        ],
    },
]


def _tokens(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


def _phrase_hit(phrase: str, text: str) -> float:
    """1.0 = exact word-bounded match, ~0.8 = all words fuzzy-match,
    ~0.7 = single word fuzzy-match (tolerates typos), 0 = no hit.
    Fuzzy matching only considers content words (not stopwords)."""
    p = phrase.lower()
    t = text.lower()
    if re.search(r"\b" + re.escape(p) + r"\b", t):
        return 1.0
    words = p.split()
    toks = [w for w in _tokens(t) if w not in _STOPWORDS]
    if not toks:
        return 0.0
    if len(words) == 1:
        kw = words[0]
        best_tok = max(toks, key=lambda t: similar(t, kw))
        best = similar(best_tok, kw)
        if best >= 0.8:
            return 0.85
        # 0.65–0.8 only for real typos: lengths comparable AND >= 3 chars
        if best >= 0.65 and min(len(best_tok), len(kw)) >= 3 and \
           min(len(best_tok), len(kw)) / max(len(best_tok), len(kw)) >= 0.6:
            return 0.7
        return 0.0
    if all(max(similar(tok, w) for tok in toks) >= 0.75 for w in words):
        return 0.8
    return 0.0


def _extract_entity(intent_id: str, text: str) -> str:
    """Strip the command phrase (exact + fuzzy) and stopwords; keep entity."""
    t = text.strip()
    strip_words: set = set()
    if intent_id == "note":
        t = re.sub(r"^(?:take a note|note that|save a note|write a note|"
                   r"remember that|note|jot)\b[:.]?\s+", "", t, flags=re.I)
        strip_words |= {"take", "note", "save", "write", "remember", "jot"}
    elif intent_id == "web_search":
        for p in ("search google for", "search the web for", "search for",
                  "look up", "find online", "on the web", "search", "google",
                  "browse for", "browse", "web"):
            t = re.sub(r"\b" + re.escape(p) + r"\b", "", t, flags=re.I)
        strip_words |= {"search", "google", "look", "up", "find", "online",
                        "web", "browse", "for", "on", "the"}
    elif intent_id == "open_app":
        strip_words |= {"open", "launch", "start", "run", "app", "application",
                        "the", "my"}
    elif intent_id == "open_file":
        strip_words |= {"open", "file", "the", "my"}
    elif intent_id == "reminder":
        t = re.sub(r"^(?:remind me to|remind me|set a reminder to|reminder)\b"
                   r"[:.]?\s+", "", t, flags=re.I)
        strip_words |= {"remind", "set", "reminder", "me", "to"}
    elif intent_id == "run_cmd":
        strip_words |= {"run", "command", "execute", "this"}

    # fuzzy-strip any token that matches a command word (typo-tolerant)
    kept = [w for w in re.findall(r"[A-Za-z0-9_\.\-]+", t)
            if not any(similar(w, sw) >= 0.7 for sw in strip_words)]
    kept = [w for w in kept if w.lower() not in _STOPWORDS]
    return " ".join(kept).strip()


def parse(text: str) -> ParsedCommand:
    raw = text.strip()
    if not raw:
        return ParsedCommand(raw_text=raw)

    scores: dict = {}
    matched: dict = {}
    for spec in INTENT_SPECS:
        total = 0.0
        hits = []
        for phrase, weight in spec["keywords"]:
            hit = _phrase_hit(phrase, raw)
            if hit:
                total += weight * hit
                hits.append(phrase)
        scores[spec["id"]] = total
        matched[spec["id"]] = hits

    # risky verbs -> route through the permission-gated shell handler
    if re.search(_RISKY_VERBS, raw, re.I):
        scores["run_cmd"] += 2.0

    # --- find the base leader (earliest spec wins ties) ----------------
    leader = "unknown"
    best_base = 0.0
    for spec in INTENT_SPECS:
        if scores[spec["id"]] > best_base + 0.15:
            leader, best_base = spec["id"], scores[spec["id"]]

    # --- file/app context adjustments (only when opening is intended) --
    if leader in ("open_app", "open_file"):
        toks = _tokens(raw)
        if re.search(r"\b\w+\.(pdf|txt|docx?|xlsx?|pptx?|png|jpe?g|gif|mp4|"
                     r"mp3|zip|rar|py|js|html?|csv|md|lnk|exe)\b", raw, re.I):
            scores["open_file"] += 3.0
        if any(similar(t, w) >= 0.8 for t in toks for w in _FILE_WORDS):
            scores["open_file"] += 1.0
        if any(similar(t, alias) >= 0.8 for t in toks for alias in APP_ALIASES):
            scores["open_app"] += 1.2

    # --- pick winner -----------------------------------------------------
    best_id, best_score, best_hits = "unknown", 0.0, []
    for spec in INTENT_SPECS:
        total = scores[spec["id"]]
        if total > best_score + 0.15:
            best_id, best_score, best_hits = spec["id"], total, matched[spec["id"]]

    confidence = min(1.0, best_score / 2.4) if best_id != "unknown" else 0.0
    entity = _extract_entity(best_id, raw) if best_id != "unknown" else ""
    name = next((s["name"] for s in INTENT_SPECS if s["id"] == best_id), "unknown")
    return ParsedCommand(intent_id=best_id, intent_name=name, entity=entity,
                         raw_text=raw, confidence=confidence, matched=best_hits)
