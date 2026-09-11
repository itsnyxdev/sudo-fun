"""Stroop effect color voice challenge using offline speech recognition."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)

COLOR_PALETTE = {
    "red": "bold red",
    "green": "bold green",
    "blue": "bold blue",
    "yellow": "bold yellow",
    "white": "bold white",
    "purple": "bold magenta",
}


class ColorChallenge(BaseChallenge):
    """Stroop challenge: Say the DISPLAY color, NOT the written word."""

    def __init__(self):
        self._target_rounds = 2
        self._current_round = 0
        self._word: str = "RED"
        self._rendered_color: str = "blue"
        self._round_timer = 0.0
        self._round_timeout = 6.0

    @property
    def id(self) -> str:
        return "audio.stroop_color"

    @property
    def name(self) -> str:
        return "Stroop Color Challenge"

    @property
    def description(self) -> str:
        return "SAY the DISPLAY COLOR into your mic, NOT the written word!"

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.MICROPHONE

    @property
    def timeout_seconds(self) -> float:
        return 18.0

    def initialize(self, difficulty: str = "normal") -> None:
        if difficulty == "easy":
            self._target_rounds = 1
            self._round_timeout = 7.0
        elif difficulty == "hard":
            self._target_rounds = 3
            self._round_timeout = 4.5
        else:
            self._target_rounds = 2
            self._round_timeout = 5.5

        self._current_round = 0
        self._pick_next_pair()

    def _pick_next_pair(self) -> None:
        colors = list(COLOR_PALETTE.keys())
        word_color = random.choice(colors)
        remaining = [c for c in colors if c != word_color]
        rendered = random.choice(remaining)

        self._word = word_color.upper()
        self._rendered_color = rendered
        self._round_timer = 0.0

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        self._round_timer += delta_time
        speech_text = context.get("speech_text", "")

        if self._round_timer >= self._round_timeout:
            return ChallengeResult(
                state=ChallengeState.FAILED,
                message=f"Timeout! Expected rendered color was '{self._rendered_color}'.",
                score=0.0,
            )

        if speech_text:
            spoken_words = speech_text.split()
            # If user spoke the actual rendered color
            if self._rendered_color in spoken_words:
                self._current_round += 1
                if self._current_round >= self._target_rounds:
                    return ChallengeResult(
                        state=ChallengeState.SUCCESS,
                        message=f"Correct! You said '{self._rendered_color}'. Sudo access granted!",
                        score=1.0,
                    )
                else:
                    self._pick_next_pair()
                    return ChallengeResult(
                        state=ChallengeState.RUNNING,
                        message=f"Correct! Next round ({self._current_round}/{self._target_rounds})...",
                    )
            # If user got tricked and spoke the written word!
            elif self._word.lower() in spoken_words:
                return ChallengeResult(
                    state=ChallengeState.FAILED,
                    message=f"Tricked! You read the word '{self._word}' instead of the display color '{self._rendered_color}'!",
                    score=0.0,
                )

        style = COLOR_PALETTE[self._rendered_color]
        rich_display = f"[{style}]{self._word}[/{style}]"

        rem = max(0.0, self._round_timeout - self._round_timer)
        return ChallengeResult(
            state=ChallengeState.RUNNING,
            message=f"Say color: {rich_display}  (Remaining: {rem:.1f}s)",
            metadata={
                "word": self._word,
                "rendered_color": self._rendered_color,
                "display": rich_display,
                "round": self._current_round + 1,
            },
        )
