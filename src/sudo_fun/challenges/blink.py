"""Don't Blink endurance challenge using Eye Aspect Ratio (EAR)."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)


class BlinkChallenge(BaseChallenge):
    """Challenge requiring user to keep their eyes wide open without blinking."""

    def __init__(self):
        self._target_duration = 6.0
        self._elapsed_open_time = 0.0
        self._closed_consecutive_frames = 0
        self._ear_threshold = 0.20
        self._min_blink_frames = 3  # ~100ms to avoid camera noise triggers

    @property
    def id(self) -> str:
        return "vision.dont_blink"

    @property
    def name(self) -> str:
        return "Don't Blink!"

    @property
    def description(self) -> str:
        return f"Stare into the camera and DO NOT blink for {self._target_duration:.1f} seconds!"

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.CAMERA

    @property
    def timeout_seconds(self) -> float:
        return 18.0

    def initialize(self, difficulty: str = "normal") -> None:
        if difficulty == "easy":
            self._target_duration = random.uniform(4.0, 5.5)
        elif difficulty == "hard":
            self._target_duration = random.uniform(7.5, 9.5)
        else:
            self._target_duration = random.uniform(5.5, 7.5)

        self._elapsed_open_time = 0.0
        self._closed_consecutive_frames = 0

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        ear = context.get("ear")

        if ear is None:
            # Face briefly lost (head movement, lighting) -> pause timer, do not fail
            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message="Face camera directly...",
                metadata={"remaining": max(0.0, self._target_duration - self._elapsed_open_time)},
            )

        # Check if eyes are closed
        if ear < self._ear_threshold:
            self._closed_consecutive_frames += 1
            if self._closed_consecutive_frames >= self._min_blink_frames:
                return ChallengeResult(
                    state=ChallengeState.FAILED,
                    message="Blink detected! You closed your eyes!",
                    score=0.0,
                )
        else:
            self._closed_consecutive_frames = 0
            self._elapsed_open_time += delta_time

        if self._elapsed_open_time >= self._target_duration:
            return ChallengeResult(
                state=ChallengeState.SUCCESS,
                message=f"Impressive focus! Stared down the sudo gate for {self._target_duration:.1f}s!",
                score=1.0,
            )

        remaining = max(0.0, self._target_duration - self._elapsed_open_time)
        return ChallengeResult(
            state=ChallengeState.RUNNING,
            message=f"[bold yellow]KEEP EYES OPEN![/bold yellow] Remaining: {remaining:.1f}s (EAR: {ear:.2f})",
            metadata={"remaining": remaining, "ear": ear},
        )
