"""
jarvis.interfaces.voice
======================
Voice mode: wake word → listen → think → speak.

- Wake word: your phrase from config (any words, e.g. "Hey Jarvis").
  Fuzzy-matched, so slight mishears still trigger it.
- STT: faster-whisper (local, offline, GPU-friendly).
- TTS: pyttsx3 (offline on Windows).

All audio libs are optional — if missing, Jarvis prints install hints
and you can still use chat mode.
"""

from __future__ import annotations

import os
import re
import time

from rich.console import Console

from ..core.parser import similar
from ..core.phrases import P, welcome_phrase


class VoiceEngine:
    def __init__(self, cfg: dict, handle_command, name: str = "Jarvis",
                 on_wake=None, phrases: dict | None = None):
        vcfg = (cfg or {}).get("voice", {}) or {}
        self.cfg = vcfg
        self.wake_word = (cfg or {}).get("jarvis", {}).get("wake_word",
                                                           "Hey Jarvis")
        self.handle_command = handle_command
        self.on_wake = on_wake
        self.phrases = phrases or {}
        self.name = name
        self.console = Console()
        self.sd = None
        self.whisper = None
        self.tts = None
        self._input_dev = None
        self._loaded = False

    # ------------------------------------------------------------------
    def _ensure_libs(self) -> None:
        if self._loaded:
            return
        # Windows can't symlink the HuggingFace cache — silence the
        # "degraded caching" warning (harmless, just uses more disk)
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        try:
            import sounddevice as sd
            self.sd = sd
        except Exception:
            pass
        self._input_dev = self._find_input_device() if self.sd is not None else None
        if self.sd is not None:
            try:
                import numpy as np  # noqa: F401
                from faster_whisper import WhisperModel
                self.whisper = WhisperModel(self.cfg.get("stt_model", "base"),
                                            device="auto", compute_type="int8")
            except Exception as e:
                self.console.print(f"[yellow]faster-whisper not ready: {e}[/]")
        try:
            import pyttsx3
            self.tts = pyttsx3.init()
        except Exception:
            pass
        self._loaded = True

    # ------------------------------------------------------------------
    def _record(self, seconds: float) -> "object":
        sr = 16000
        n = int(seconds * sr)
        rec = self.sd.rec(n, samplerate=sr, channels=1, dtype="float32",
                          device=self._input_dev)
        self.sd.wait()
        return rec[:, 0]

    @staticmethod
    def _find_input_device():
        """Pick the first usable microphone (returns device index or None)."""
        try:
            import sounddevice as sd
            for i, d in enumerate(sd.query_devices()):
                if d.get("max_input_channels", 0) > 0:
                    return i
        except Exception:
            pass
        return None

    def _transcribe(self, audio) -> str:
        segments, _ = self.whisper.transcribe(audio, language="en", beam_size=1)
        return " ".join(seg.text.strip() for seg in segments).strip()

    def _is_wake(self, text: str) -> bool:
        t = text.strip().lower()
        if not t:
            return False
        if similar(t, self.wake_word) >= 0.75:
            return True
        # allow word-order changes: all wake words present (fuzzy)
        words = re.findall(r"[a-z]+", self.wake_word.lower())
        if len(words) >= 2:
            toks = re.findall(r"[a-z]+", t)
            if all(any(similar(tok, w) >= 0.8 for tok in toks) for w in words):
                return True
        return False

    def _listen_for_wake(self, timeout: float = 180.0) -> str:
        """Listen until the wake word is heard; returns what was heard."""
        deadline = time.time() + timeout
        last = ""
        errors = 0
        while time.time() < deadline:
            try:
                audio = self._record(2.5)
                errors = 0
            except Exception as e:
                errors += 1
                if errors >= 3:
                    self.console.print(f"[yellow]🎤 microphone error: {e}[/]")
                    self.console.print("   Check your mic in Windows Settings →")
                    self.console.print("   System → Sound → Input, then restart Jarvis.")
                    return ""
                time.sleep(0.5)
                continue
            try:
                text = self._transcribe(audio)
            except Exception:
                text = ""
            if text.strip():
                last = text.strip()
                self.console.print(f"[dim]heard: {text}[/]")
                if self._is_wake(text):
                    return text
        return last

    def _listen_command(self, max_seconds: float = 12.0) -> str:
        """Record after wake word until ~1.2s of silence, then transcribe."""
        import numpy as np
        sr = 16000
        chunks, silence_since = [], None
        start = time.time()
        while time.time() - start < max_seconds:
            rec = self._record(0.5)
            rms = float((rec ** 2).mean()) if len(rec) else 0.0
            chunks.append(rec)
            if rms < 0.005:
                if silence_since is None:
                    silence_since = time.time()
                if time.time() - silence_since > 1.2:
                    break
            else:
                silence_since = None
        audio = np.concatenate(chunks) if chunks else np.zeros(sr)
        try:
            return self._transcribe(audio)
        except Exception:
            return ""

    def speak(self, text: str) -> None:
        if self.tts is not None:
            self.tts.say(text)
            self.tts.runAndWait()
        else:
            self.console.print(f"[bold cyan]{self.name}:[/] {text}")

    # ------------------------------------------------------------------
    def run(self) -> None:
        self._ensure_libs()
        missing = []
        if self.sd is None:
            missing.append("sounddevice")
        if self.whisper is None:
            missing.append("faster-whisper")
        if missing:
            self.console.print(
                f"[yellow]⚠️ Voice libraries missing. Install:[/]\n"
                f"   pip install {' '.join(missing)}\n"
                f"[yellow](Chat mode still works without them)[/]")
            return

        if self._input_dev is None:
            self.console.print(
                "[yellow]🎤 No microphone found![/]\n"
                "   Plug in a mic (or enable your laptop's built-in one) and restart.\n"
                "   Check: Windows Settings → System → Sound → Input")
            return

        self.console.print(
            f"[bold cyan]🎤 Voice mode on — wake word: "
            f"\"{self.wake_word}\"[/]\n[dim]Ctrl+C to stop[/]")
        welcome = welcome_phrase(self.phrases)
        self.console.print(f"[bold cyan]{welcome}[/]")
        self.speak(welcome)
        try:
            while True:
                self.console.print(
                    f"[cyan]Listening for wake word...[/]")
                phrase = self._listen_for_wake()
                if self._is_wake(phrase):
                    self.console.print(
                        "[green]✓ wake word heard — launching Jarvis...[/]")
                    # Launch the full Jarvis experience right now:
                    # UI opens + spoken greeting, zero dead time
                    if self.on_wake:
                        try:
                            self.on_wake()
                        except Exception:
                            pass
                    launch = P(self.phrases, "wake_launch",
                               "Yes, sir. Jarvis online — what's your command?")
                    self.console.print(f"[bold cyan]{launch}[/]")
                    self.speak(launch)
                    text = self._listen_command()
                    if not text.strip():
                        self.console.print("[yellow]didn't catch that[/]")
                        continue
                    self.console.print(f"[bold green]You:[/] {text}")
                    try:
                        reply = self.handle_command(text)
                    except Exception as e:
                        reply = f"⚠️ Error: {e}"
                    self.speak(reply)
        except KeyboardInterrupt:
            self.console.print("\n[dim]Voice mode stopped.[/]")
