"""Challenge registry and hardware pre-flight selection."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Type

from sudo_fun.challenges.animal import AnimalChallenge
from sudo_fun.challenges.base import BaseChallenge, RequiredDevice
from sudo_fun.challenges.blink import BlinkChallenge
from sudo_fun.challenges.color import ColorChallenge
from sudo_fun.challenges.dance import DanceChallenge
from sudo_fun.challenges.pose import PoseChallenge
from sudo_fun.challenges.reaction import ReactionChallenge
from sudo_fun.core.assets import verify_model_exists
from sudo_fun.perception.audio import is_microphone_available
from sudo_fun.perception.camera import is_camera_available

# Model dependencies per challenge ID
REQUIRED_CHALLENGE_MODELS: Dict[str, List[str]] = {
    "vision.pose_match": ["pose_landmarker_lite.task"],
    "vision.dance": ["pose_landmarker_lite.task"],
    "vision.dont_blink": ["face_landmarker.task"],
    "audio.stroop_color": ["vosk-model-small-en-us-0.15"],
    "audio.animal_sound": ["yamnet.onnx", "yamnet_class_map.csv"],
}


class ChallengeRegistry:
    """Registry maintaining available challenges, device filters, and model readiness."""

    def __init__(self):
        self._challenges: Dict[str, Type[BaseChallenge]] = {}
        self.register(ReactionChallenge)
        self.register(PoseChallenge)
        self.register(DanceChallenge)
        self.register(BlinkChallenge)
        self.register(ColorChallenge)
        self.register(AnimalChallenge)

    def register(self, challenge_cls: Type[BaseChallenge]) -> None:
        inst = challenge_cls()
        self._challenges[inst.id] = challenge_cls

    def are_required_models_available(self, challenge_id: str) -> bool:
        """Checks if all required offline ML models for a challenge are present on disk."""
        req_models = REQUIRED_CHALLENGE_MODELS.get(challenge_id, [])
        for m in req_models:
            if not verify_model_exists(m):
                return False
        return True

    def get_available_devices(self) -> RequiredDevice:
        """Probes system hardware to determine active input devices."""
        dev = RequiredDevice.KEYBOARD
        if is_camera_available():
            dev |= RequiredDevice.CAMERA
        if is_microphone_available():
            dev |= RequiredDevice.MICROPHONE
        return dev

    def select_random_challenge(
        self,
        specific_id: Optional[str] = None,
        available_devices: Optional[RequiredDevice] = None,
    ) -> BaseChallenge:
        """Selects a challenge compatible with available hardware and downloaded models."""
        if specific_id and specific_id in self._challenges:
            return self._challenges[specific_id]()

        if available_devices is None:
            available_devices = self.get_available_devices()

        candidates: List[Type[BaseChallenge]] = []
        for cls in self._challenges.values():
            inst = cls()
            req = inst.required_devices
            # Check both hardware device compatibility AND model availability
            if (req & available_devices) == req and self.are_required_models_available(inst.id):
                candidates.append(cls)

        if not candidates:
            # Fallback to Reaction challenge which only needs keyboard and zero ML models
            return ReactionChallenge()

        chosen_cls = random.choice(candidates)
        return chosen_cls()
