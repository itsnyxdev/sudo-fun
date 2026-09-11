"""Terminal User Interface using Rich live rendering."""

from __future__ import annotations

import sys
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.text import Text


class TerminalUI:
    """Rich-based live terminal UI for sudo-fun challenges."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._live: Optional[Live] = None

    def start(self) -> None:
        self._live = Live(
            console=self.console,
            auto_refresh=False,
            transient=True,  # Disappears cleanly when sudo executes
        )
        self._live.start()

    def update(
        self,
        command: str,
        challenge_name: str,
        instructions: str,
        status_message: str,
        time_ratio: float,
        time_text: str,
        fail_count: int = 0,
        max_fails: int = 3,
    ) -> None:
        if not self._live:
            return

        # Failure indicators: e.g. ● ○ ○
        dots = []
        for i in range(max_fails):
            if i < fail_count:
                dots.append("[bold red]●[/bold red]")
            else:
                dots.append("[dim white]○[/dim white]")
        dots_str = " ".join(dots)

        content = Text()
        content.append(f"Target Command: ", style="bold cyan")
        content.append(f"{command}\n", style="white")
        content.append(f"Consecutive Failures: ", style="bold")
        content.append_text(Text.from_markup(f"{dots_str} ({fail_count}/{max_fails})\n\n"))

        content.append(f"CHALLENGE: ", style="bold magenta")
        content.append(f"{challenge_name}\n", style="bold white")
        content.append(f"Mission: ", style="bold yellow")
        content.append(f"{instructions}\n\n", style="italic")

        # Add visual progress bar for timeout
        pbar = ProgressBar(total=1.0, completed=max(0.0, min(1.0, time_ratio)), width=40)

        grid = Text()
        grid.append_text(content)
        grid.append(f"Status: ", style="bold")
        grid.append_text(Text.from_markup(f"{status_message}\n"))
        grid.append(f"Timer:  {time_text} ")

        panel = Panel(
            grid,
            title="[bold yellow]⚡ sudo-fun: Proof of Fun Authentication ⚡[/bold yellow]",
            subtitle=f"[dim]Press Ctrl+C to cancel[/dim]",
            border_style="bright_blue",
        )
        self._live.update(panel, refresh=True)

    def stop(self) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def print_success(self, message: str) -> None:
        self.console.print(Panel(
            f"[bold green]✔ CHALLENGE PASSED![/bold green]\n{message}\n[dim]Delegating to /usr/bin/sudo...[/dim]",
            border_style="green",
        ))

    def print_failure(self, message: str, fails: int, max_fails: int) -> None:
        remaining_attempts = max_fails - fails
        self.console.print(Panel(
            f"[bold red]✘ CHALLENGE FAILED![/bold red]\n{message}\n"
            f"[yellow]Attempts remaining before 10-minute lockout: {remaining_attempts}[/yellow]",
            border_style="red",
        ))

    def print_locked(self, remaining_seconds: float) -> None:
        mins = int(remaining_seconds // 60)
        secs = int(remaining_seconds % 60)
        time_fmt = f"{mins:02d}:{secs:02d}"
        self.console.print(Panel(
            f"[bold red]🔒 COMMAND LOCKED[/bold red]\n"
            f"Too many consecutive challenge failures.\n"
            f"Please calm down, stretch, and try again in [bold yellow]{time_fmt}[/bold yellow].",
            border_style="bold red",
        ))
