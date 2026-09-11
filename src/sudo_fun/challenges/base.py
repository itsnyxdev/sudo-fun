"""Abstract base class and definitions for sudo-fun challenges."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from typing import Any, Dict, Optional


class ChallengeState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RequiredDevice(Flag):
    NONE = 0
    KEYBOARD = auto()
    CAMERA = auto()
    MICROPHONE = auto()


@dataclass(frozen=True)
class ChallengeResult:
    state: ChallengeState
    message: str
    duration_seconds: float = 0.0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseChallenge(ABC):
    """Abstract base class defining the contract for all sudo-fun challenges."""

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique challenge identifier."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable challenge title."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Instructions displayed to the user."""
        pass

    @property
    @abstractmethod
    def required_devices(self) -> RequiredDevice:
        """Hardware devices required to run this challenge."""
        pass

    @property
    @abstractmethod
    def timeout_seconds(self) -> float:
        """Maximum allowable duration before timeout failure."""
        pass

    @abstractmethod
    def initialize(self, difficulty: str = "normal") -> None:
        """Initializes challenge state, random targets, and parameters."""
        pass

    @abstractmethod
    def update(self, delta_time: float, context: Dict[str, Any]) -> ChallengeResult:
        """Ticks the challenge logic with fresh perception inputs.

        Args:
            delta_time: Elapsed seconds since last tick.
            context: Dictionary containing current frame, audio chunks, and keyboard events:
                     - 'frame': numpy.ndarray | None
                     - 'pose_landmarks': list | None
                     - 'face_landmarks': list | None
                     - 'ear': float | None (eye aspect ratio)
                     - 'speech_text': str | None
                     - 'audio_classes': list[tuple[str, float]] | None
                     - 'key_event': str | None
        """
        pass

    def render_demo(self) -> Optional[Any]:
        """Provides demo data (e.g. skeleton points, target colors) for the UI overlay."""
        return None

    def cleanup(self) -> None:
        """Releases challenge-specific state."""
        pass
