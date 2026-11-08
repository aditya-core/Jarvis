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
3. **Install a local AI brain** (optional but recommended — offline AI chat).
   Two options, pick ONE:

   **Option A — llama.cpp standalone (lightest — best for old/weak PCs) ⭐**
   No pip, no compiler, no installer, no CUDA — just a zip:
   1. Download the **Windows CPU build** from GitHub:
      https://github.com/ggml-org/llama.cpp/releases/latest
      (file like `llama-bXXXX-bin-win-cpu-x64.zip`), extract anywhere
   2. Download a small GGUF model, e.g.:
      ```
      qwen2.5-1.5b-instruct-q4_k_m.gguf  ~1 GB   good balance
      qwen2.5-0.5b-instruct-q4_k_m.gguf  ~0.4 GB  ultra-light
      ```
      from https://huggingface.co/Qwen (pick the GGUF file)
   3. Tell Jarvis where the files are — edit `config/jarvis.yaml`:
      ```yaml
      llamaserver:
        exe_path: C:\llamacpp\llama-server.exe
        model_path: C:\models\qwen2.5-1.5b-instruct-q4_k_m.gguf
      ```
      (use the folders you actually used)
   4. Start the brain server:
      ```
      python main.py --start-server
      ```
      (keep this window open while using Jarvis)
   5. Start Jarvis — BRAIN goes ONLINE automatically:
      ```
      python main.py --ui
      ```

   > ⚠️ `llama-cpp-python` (pip) builds from source and needs a C++
   > compiler — advanced users only. The standalone binary above is the
   > light path.

   **Option B — Ollama**
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

## 🗣️ Personality & phrases (local 'training')

Jarvis learns its greetings & canned replies from **`config/phrases.yaml`**.
Edit it, restart, done — no code changes needed. This is your local
training library.

```yaml
phrases:
  wake: "Yes, sir?"
  wake_launch: "Yes, sir. Jarvis online — what's your command?"
  welcome: ["Good morning, sir.", "Good afternoon, sir.", "Good evening, sir."]
  opening_app: "🚀 Opening {app}, sir..."
  reminder_set: "⏰ Reminder set, sir. {summary}"
```

Available keys: `address, wake, wake_launch, welcome, goodbye, note_saved,
notes_empty, opening_app, app_not_found, opening_file, file_not_found,
screenshot_saved, screenshot_fail, reminder_set, reminder_no_time, time,
system_header, search_results, search_unavailable, fallback, help` —
placeholders like `{app}`, `{file}`, `{summary}`, `{time}` get filled
automatically.

## 🎬 Wake → launch (instant)

Saying the wake word launches Jarvis immediately — **no dead time, no
second command needed**:

1. Wake word heard → Jarvis UI opens in your browser
2. Jarvis speaks: *"Yes, sir. Jarvis online — what's your command?"*
3. You speak your command (or type it in the HUD)

That's it. Configure the wake word in `config/jarvis.yaml`:

```yaml
jarvis:
  name: Jarvis
  wake_word: "Hey Jarvis"
```

## 🧪 Quick examples

```
> hej jarvis
Good morning, sir.

> take a note buy milk and eggs
📝 Noted, sir. "buy milk and eggs"

> opn chrome pls          ← typo? no problem
🚀 Opening chrome, sir...

> remind me to call mom at 9pm
⏰ Reminder set, sir. Call mom — at 21:00 on Monday

> seach gogle best laptop 2025
🔍 Results for "best laptop 2025": ...
```

## 🛠️ Troubleshooting

**`ollama is not recognized`** — Ollama not installed or terminal is stale:
open a **new** terminal window, or reinstall from ollama.com.

**"error installing cudav_12 / msvcp140.dll"** — GPU (CUDA) support failing.
You don't need GPU acceleration — Ollama falls back to **CPU mode** automatically.
Just test: `ollama run qwen2.5:3b`. If it still fails, install the MSVC
runtime: download https://aka.ms/vs/17/release/vc_redist.x64.exe → run →
reboot → retry.

**SmartScreen "Windows protected your PC"** — normal for Ollama (it installs
a background service). Only install from ollama.com, then click
**More info → Run anyway**.

**Jarvis says "Local brain offline"** — Ollama isn't running. Start it from
the system tray icon, or launch `ollama serve` once.

**Voice mode missing libraries** — `pip install faster-whisper sounddevice pyttsx3`.
Chat + UI work without them.

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
