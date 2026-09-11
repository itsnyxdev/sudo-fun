"""Dance and temporal body movement challenge."""

from __future__ import annotations

import collections
import random
from typing import Any, Dict, Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)


class DanceChallenge(BaseChallenge):
    """Challenge requiring user to perform a repetitive rhythmic movement."""

    def __init__(self):
        self._target_cycles = 4
        self._target_duration = 5.0
        self._elapsed_time = 0.0
        self._cycle_count = 0
        self._movement_phase = "down"  # "up" or "down"

    @property
    def id(self) -> str:
        return "vision.dance"

    @property
    def name(self) -> str:
        return "Dance: Wave Your Arms!"

    @property
    def description(self) -> str:
        return f"Wave both arms up and down rhythmically! Complete {self._target_cycles} full waves."

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.CAMERA

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    def initialize(self, difficulty: str = "normal") -> None:
        if difficulty == "easy":
            self._target_cycles = 3
        elif difficulty == "hard":
            self._target_cycles = 6
        else:
            self._target_cycles = 4

        self._elapsed_time = 0.0
        self._cycle_count = 0
        self._movement_phase = "down"

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        self._elapsed_time += delta_time
        angles = context.get("pose_angles")

        if not angles:
            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message="Camera waiting for dancer...",
                metadata={"cycles": self._cycle_count, "target_cycles": self._target_cycles},
            )

        # Average elbow/shoulder vertical state
        left_up = angles.get("left_hand_up", 0.0)
        right_up = angles.get("right_hand_up", 0.0)
        current_val = (left_up + right_up) / 2.0  # 1.0 when up, 0.0 when down

        # Hysteresis state machine for cycle counting
        if current_val >= 0.6 and self._movement_phase == "down":
            self._movement_phase = "up"
        elif current_val <= 0.4 and self._movement_phase == "up":
            self._movement_phase = "down"
            self._cycle_count += 1

        if self._cycle_count >= self._target_cycles:
            return ChallengeResult(
                state=ChallengeState.SUCCESS,
                message=f"Awesome groove! Completed {self._cycle_count} waves in {self._elapsed_time:.1f}s!",
                score=1.0,
            )

        return ChallengeResult(
            state=ChallengeState.RUNNING,
            message=f"[bold cyan]KEEP DANCING![/bold cyan] Waves: {self._cycle_count}/{self._target_cycles}",
            metadata={"cycles": self._cycle_count, "target_cycles": self._target_cycles},
        )

    def render_demo(self) -> Optional[Any]:
        return {
            "type": "dance_animation",
            "title": "Wave Both Arms",
            "cycle": int((self._elapsed_time * 2) % 2),
        }
