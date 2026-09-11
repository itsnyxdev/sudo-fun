"""Animal sound imitation challenge using YAMNet audio classification."""

from __future__ import annotations

import random
from typing import Any, Dict, Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)

ANIMALS = [
    ("dog", "Bark like a dog! (Woof / Arf!)"),
    ("cat", "Meow like a cat!"),
    ("cow", "Moo like a cow!"),
    ("sheep", "Baa like a sheep!"),
    ("pig", "Oink like a pig!"),
    ("duck", "Quack like a duck!"),
    ("lion", "Roar like a lion!"),
    ("chicken", "Cluck like a chicken!"),
    ("frog", "Croak like a frog!"),
]


class AnimalChallenge(BaseChallenge):
    """Challenge requiring user to imitate an animal sound into the microphone."""

    def __init__(self):
        self._animal: str = "dog"
        self._prompt_text: str = ""
        self._elapsed: float = 0.0

    @property
    def id(self) -> str:
        return "audio.animal_sound"

    @property
    def name(self) -> str:
        return f"Imitate Animal: {self._animal.capitalize()}"

    @property
    def description(self) -> str:
        return self._prompt_text

    @property
    def required_devices(self) -> RequiredDevice:
        return RequiredDevice.MICROPHONE

    @property
    def timeout_seconds(self) -> float:
        return 12.0

    def initialize(self, difficulty: str = "normal") -> None:
        self._animal, self._prompt_text = random.choice(ANIMALS)
        self._elapsed = 0.0

    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        self._elapsed += delta_time
        detected = context.get("animal_detected", False)
        detected_label = context.get("detected_label", "")
        detected_score = context.get("detected_score", 0.0)

        if detected:
            return ChallengeResult(
                state=ChallengeState.SUCCESS,
                message=f"Spectacular {self._animal}! Audio matched '{detected_label}' ({detected_score*100:.1f}%)!",
                score=1.0,
            )

        rem = max(0.0, self.timeout_seconds - self._elapsed)
        return ChallengeResult(
            state=ChallengeState.RUNNING,
            message=f"[bold magenta]{self._prompt_text}[/bold magenta] (Listening... {rem:.1f}s remaining)",
            metadata={"animal": self._animal, "remaining": rem},
        )
