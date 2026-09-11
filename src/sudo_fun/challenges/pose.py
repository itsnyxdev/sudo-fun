"""Pose imitation challenge using body landmarks and geometric angles."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional, Tuple

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)

# Target pose definitions based on joint angles and relative positions
TARGET_POSES = {
    "hands_above_head": {
        "title": "Hands Above Head!",
        "desc": "Raise both of your hands high above your head!",
        "check": lambda angles: (angles.get("left_hand_up", 0) > 0.5 and angles.get("right_hand_up", 0) > 0.5),
        "demo_skeleton": [("left_arm", "up"), ("right_arm", "up")],
    },
    "t_pose": {
        "title": "Assert Dominance (T-Pose)!",
        "desc": "Stretch both arms straight out sideways horizontally!",
        "check": lambda angles: (
            70.0 <= angles.get("left_shoulder", 0) <= 120.0
            and 70.0 <= angles.get("right_shoulder", 0) <= 120.0
            and angles.get("left_elbow", 0) >= 140.0
            and angles.get("right_elbow", 0) >= 140.0
        ),
        "demo_skeleton": [("left_arm", "side"), ("right_arm", "side")],
    },
    "one_arm_raised": {
        "title": "Hail Sudo (One Arm Up)!",
        "desc": "Raise your RIGHT hand high into the air, keep your left hand down!",
        "check": lambda angles: (angles.get("right_hand_up", 0) > 0.5 and angles.get("left_hand_up", 0) < 0.5),
        "demo_skeleton": [("left_arm", "down"), ("right_arm", "up")],
    },
    "superhero": {
        "title": "Superhero Pose!",
        "desc": "Bend both elbows and place your hands on your hips!",
        "check": lambda angles: (
            angles.get("left_elbow", 180) < 110.0
            and angles.get("right_elbow", 180) < 110.0
            and angles.get("left_hand_up", 1) == 0.0
            and angles.get("right_hand_up", 1) == 0.0
        ),
        "demo_skeleton": [("left_arm", "hip"), ("right_arm", "hip")],
    },
}


class PoseChallenge(BaseChallenge):
    """Challenge requiring user to reproduce and hold a target pose."""

    def __init__(self):
        self._target_key: str = "hands_above_head"
        self._target_info: dict = TARGET_POSES["hands_above_head"]
        self._hold_time_required = 1.2
        self._current_hold_time = 0.0

    @property
    def id(self) -> str:
        return "vision.pose_match"

    @property
    def name(self) -> str:
        return f"Pose: {self._target_info['title']}"

    @property
    def description(self) -> str:
        return self._target_info["desc"]

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.CAMERA

    @property
    def timeout_seconds(self) -> float:
        return 20.0

    def initialize(self, difficulty: str = "normal") -> None:
        self._target_key = random.choice(list(TARGET_POSES.keys()))
        self._target_info = TARGET_POSES[self._target_key]
        if difficulty == "easy":
            self._hold_time_required = 0.8
        elif difficulty == "hard":
            self._hold_time_required = 1.8
        else:
            self._hold_time_required = 1.2
        self._current_hold_time = 0.0

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        angles = context.get("pose_angles")
        if not angles:
            self._current_hold_time = max(0.0, self._current_hold_time - delta_time * 0.5)
            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message="Looking for person in camera frame...",
                metadata={"hold_ratio": 0.0, "target": self._target_key},
            )

        matches = self._target_info["check"](angles)

        if matches:
            self._current_hold_time += delta_time
            hold_ratio = min(1.0, self._current_hold_time / self._hold_time_required)
            if self._current_hold_time >= self._hold_time_required:
                return ChallengeResult(
                    state=ChallengeState.SUCCESS,
                    message=f"Pose matched perfectly! Held for {self._hold_time_required:.1f}s.",
                    score=1.0,
                    metadata={"hold_ratio": 1.0, "target": self._target_key},
                )
            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message=f"[bold green]HOLD IT![/bold green] ({int(hold_ratio * 100)}%)",
                metadata={"hold_ratio": hold_ratio, "target": self._target_key},
            )
        else:
            self._current_hold_time = max(0.0, self._current_hold_time - delta_time * 1.5)
            hold_ratio = self._current_hold_time / self._hold_time_required
            return ChallengeResult(
                state=ChallengeState.RUNNING,
                message=f"{self._target_info['desc']} (Adjust your pose)",
                metadata={"hold_ratio": hold_ratio, "target": self._target_key},
            )

    def render_demo(self) -> Optional[Any]:
        return {
            "type": "pose_skeleton",
            "pose_id": self._target_key,
            "title": self._target_info["title"],
            "parts": self._target_info["demo_skeleton"],
        }
