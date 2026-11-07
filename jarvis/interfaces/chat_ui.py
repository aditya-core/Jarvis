"""
jarvis.interfaces.chat_ui
=========================
Rich terminal chat UI — for typing commands and chatting.
"""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt


class ChatUI:
    def __init__(self, name: str = "Jarvis"):
        self.console = Console()
        self.name = name

    def banner(self) -> None:
        self.console.print(Panel(
            f"[bold cyan]🤖 {self.name}[/] — your offline-first assistant\n\n"
            "[dim]Type anything, or use commands like:[/]\n"
            "  [green]take a note ...[/]   [green]open chrome[/]   "
            "[green]screenshot[/]\n"
            "  [green]search ...[/]       [green]remind me ... at 9pm[/]\n"
            "  [green]help[/]             [green]bye[/]",
            border_style="cyan",
        ))

    def user(self, text: str) -> None:
        self.console.print(f"[bold green]You:[/] {text}")

    def jarvis(self, text: str) -> None:
        self.console.print(Panel(Markdown(text),
                                 title=f"🤖 {self.name}", border_style="cyan"))

    def run(self, jarvis) -> None:
        self.banner()
        while True:
            try:
                line = Prompt.ask("[bold]You[/]")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            line = line.strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "bye", "good night"):
                self.jarvis("Goodbye! See you soon. 👋")
                break
            self.user(line)
            with self.console.status("[cyan]Jarvis is thinking...[/]"):
                try:
                    reply = jarvis.handle(line)
                except Exception as e:
                    reply = f"⚠️  Error: {e}"
            self.jarvis(reply)
