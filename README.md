# 🤖 Jarvis

Your **offline-first** personal assistant for Windows. Runs on your machine,
understands messy input (typos and unclear phrasing are fine), works fully
offline for core tasks, and speaks if you want it to.

## ✨ What it does today

| Command | Example |
|---|---|
| 📝 Notes | `take a note buy milk` · `show notes` |
| 🚀 Apps | `open chrome` · `launch vs code` (aliases + fuzzy names) |
| 📂 Files | `open report.pdf` (fuzzy search in Desktop/Documents) |
| 📸 Photos | `screenshot` · `take a photo` |
| 🔍 Web | `search python tutorials` (DuckDuckGo, no key) |
| ⏰ Reminders | `remind me to call mom at 9pm` · `in 5 minutes` · `tomorrow at 3pm` |
| 💻 System | `system status` · `what time is it` |
| 💬 Chat | ask anything — via local Ollama model |
| 🎤 Voice | wake word (configurable) → speech recognition → speech |
| ⚙️ Shell | `run command ...` (risky commands ask permission first) |

## 🚀 Setup (Windows)

1. **Install Python 3.10+** — https://python.org
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Install Ollama** (optional but recommended — offline AI chat):
   - Download the Windows installer: https://ollama.com/download/windows
   - Run `OllamaSetup.exe` — it installs & starts Ollama automatically
     (icon appears in the system tray)
   - **Open a NEW terminal window** so it finds the `ollama` command
   - Pick your model size (old PC? go small!):
     ```
     qwen2.5:1.5b   ~1 GB   ultra-light, old/weak PCs
     qwen2.5:3b     ~2 GB   balanced (recommended default)
     qwen2.5:7b     ~5 GB   best chat, strong machines only
     ```
   - Example: `ollama pull qwen2.5:3b`
   - Verify: `ollama list`
   - ⚠️ Don't want AI at all? Skip this — core commands work without it.
   - Switch models later: `ollama pull <model>` + edit `model:` in
     `config/jarvis.yaml`; free space with `ollama rm <model>`.
   - **"ollama not recognized"?** → reinstall from the link above, then
     open a fresh terminal window.
4. **Voice (optional):**
   ```
   pip install faster-whisper sounddevice pyttsx3
   ```
5. **Configure:** edit `config/jarvis.yaml`
   - `wake_word` — your 3-word wake phrase (any words you like)
   - `model` — any model you pulled with `ollama pull`
6. **Run:**
   ```
   python main.py              # chat mode
   python main.py --voice      # voice mode
   python main.py --selftest   # built-in tests
   ```

## 🖥️ Web UI — movie-style HUD

```
python main.py --ui
```

Opens a cinematic interface in your browser (http://localhost:8765):
- 🌀 Animated arc reactor, particle field, ripple wake effect, boot sequence
- 📊 **Activity feed** — every command/reply, always recorded
- 🧠 **AI thinking** panel — intent, confidence %, matched keywords, plugin, LLM used
- 💾 **Memory usage** — conversations, notes, profile facts, memory file size
- 💻 **System meters** — live CPU / RAM / disk bars
- 🎤 Voice button (browser) + fullscreen mode (press F)

With `--voice`, saying the wake word launches this UI in your browser
with the full boot animation — your own Iron Man moment. 🦾

## 🧪 Quick examples

```
> take a note buy milk and eggs
📝 Noted: "buy milk and eggs"  saved to data/notes/...

> opn chrome pls          ← typo? no problem
🚀 Opening chrome...

> remind me to call mom at 9pm
⏰ Reminder set: call mom — at 21:00 on Monday

> seach gogle best laptop 2025
🔍 Results for "best laptop 2025": ...
```

## 🛡️ Safety

- Destructive commands (delete, format, install...) require explicit `y`
- Nothing is sent to any cloud — Ollama runs locally, web search is via
  DuckDuckGo only

## 🗂️ Data

All your data stays in `data/`: notes, reminders, conversation memory,
screenshots. Delete it anytime — nothing else is affected.

## 🚧 Roadmap (next phases)

- Email (read/draft), calendar, more apps & smart-home hooks
- RAG over personal documents (answer questions from your files)
- Chrome/Edge extension, desktop overlay widget
- Cloud model fallback for heavy reasoning
