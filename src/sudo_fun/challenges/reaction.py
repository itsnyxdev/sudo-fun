"""Reaction timing challenge (zero-ML)."""

from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)


class ReactionChallenge(BaseChallenge):
    """Challenge requiring user to react quickly to a sudden visual signal."""

    def __init__(self):
        self._target_rounds = 2
        self._current_round = 0
        self._threshold_sec = 0.40
        self._phase = "idle"  # "wait", "signal", "round_success"
        self._phase_timer = 0.0
        self._signal_start_time = 0.0
        self._wait_delay = 0.0
        self._reaction_times: list[float] = []

    @property
    def id(self) -> str:
        return "timing.reaction"

    @property
    def name(self) -> str:
        return "Lightning Reflexes"

    @property
    def description(self) -> str:
        return (
            f"Wait for the GREEN signal, then press SPACE immediately! "
            f"Pass {self._target_rounds} rounds. Don't press early!"
        )

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.KEYBOARD

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    def initialize(self, difficulty: str = "normal") -> None:
        if difficulty == "easy":
            self._threshold_sec = 0.50
            self._target_rounds = 1
        elif difficulty == "hard":
            self._threshold_sec = 0.28
            self._target_rounds = 3
        else:
            self._threshold_sec = 0.40
            self._target_rounds = 2

        self._current_round = 0
        self._reaction_times = []
        self._start_new_round()

    def _start_new_round(self) -> None:
        self._phase = "wait"
        self._phase_timer = 0.0
        # Random delay between 2.0 and 5.0 seconds
        self._wait_delay = random.uniform(2.0, 4.5)
        self._signal_start_time = 0.0

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        self._phase_timer += delta_time
        key_event = context.get("key_event")

        if self._phase == "wait":
            # If user pressed space or enter too early, it's a false start
            if key_event in (" ", "space", "enter"):
                return ChallengeResult(
                    state=ChallengeState.FAILED,
                    message="False start! You pressed before the signal!",
                    score=0.0,
                )

            if self._phase_timer >= self._wait_delay:
                self._phase = "signal"
                self._signal_start_time = time.time()
                self._phase_timer = 0.0
                return ChallengeResult(
                    state=ChallengeState.RUNNING,
                    message="[bold green on black]>>> PRESS SPACE NOW! <<<[/bold green on black]",
                    metadata={"phase": "signal", "round": self._current_round + 1},
                )

            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message="[bold yellow]WAIT FOR GREEN...[/bold yellow] (Hands ready!)",
                metadata={"phase": "wait", "round": self._current_round + 1},
            )

        elif self._phase == "signal":
            elapsed = time.time() - self._signal_start_time

            if key_event in (" ", "space", "enter"):
                reaction_time = elapsed
                self._reaction_times.append(reaction_time)

                if reaction_time <= self._threshold_sec:
                    self._current_round += 1
                    if self._current_round >= self._target_rounds:
                        avg = sum(self._reaction_times) / len(self._reaction_times)
                        return ChallengeResult(
                            state=ChallengeState.SUCCESS,
                            message=f"Success! Fast reaction: {reaction_time:.3f}s (Avg: {avg:.3f}s)",
                            score=1.0,
                        )
                    else:
                        self._start_new_round()
                        return ChallengeResult(
                            state=ChallengeState.RUNNING,
                            message=f"Nice! {reaction_time:.3f}s. Round {self._current_round}/{self._target_rounds} complete!",
                            metadata={"phase": "round_complete"},
                        )
                else:
                    return ChallengeResult(
                        state=ChallengeState.FAILED,
                        message=f"Too slow! Reaction was {reaction_time:.3f}s (Threshold: {self._threshold_sec:.2f}s)",
                        score=0.0,
                    )

            # Timeout on the reaction signal if user doesn't press within 2 seconds
            if elapsed > 1.8:
                return ChallengeResult(
                    state=ChallengeState.FAILED,
                    message="Time's up! You missed the signal.",
                    score=0.0,
                )

            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message="[bold green on black]>>> PRESS SPACE NOW! <<<[/bold green on black]",
                metadata={"phase": "signal", "round": self._current_round + 1},
            )

        return ChallengeResult(
            state=ChallengeState.RUNNING,
            message="Ready...",
        )
