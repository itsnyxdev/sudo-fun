"""Face mesh detector and Eye Aspect Ratio (EAR) blink calculation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np

LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]


def _euclidean_dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def calculate_ear(eye_points: List[Tuple[float, float]]) -> float:
    """Calculates Eye Aspect Ratio (EAR) given 6 normalized landmark coordinates."""
    d_v1 = _euclidean_dist(eye_points[1], eye_points[5])
    d_v2 = _euclidean_dist(eye_points[2], eye_points[4])
    d_h = _euclidean_dist(eye_points[0], eye_points[3])

    if d_h <= 1e-6:
        return 0.0
    return (d_v1 + d_v2) / (2.0 * d_h)


def _get_model_path() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "assets" / "models" / "face_landmarker.task",
        Path.home() / ".local" / "share" / "sudo-fun" / "models" / "face_landmarker.task",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(candidates[0])


class FaceDetector:
    """MediaPipe FaceLandmarker for real-time blink tracking."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        model_path = _get_model_path()
        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            min_face_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = FaceLandmarker.create_from_options(options)

    def process_ear(self, frame_bgr: np.ndarray) -> Optional[float]:
        """Returns the average Eye Aspect Ratio (EAR) across both eyes, or None if no face."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.landmarker.detect(mp_image)

        if not results.face_landmarks:
            return None

        landmarks = results.face_landmarks[0]

        left_pts = [(landmarks[i].x, landmarks[i].y) for i in LEFT_EYE_INDICES]
        right_pts = [(landmarks[i].x, landmarks[i].y) for i in RIGHT_EYE_INDICES]

        left_ear = calculate_ear(left_pts)
        right_ear = calculate_ear(right_pts)

        return (left_ear + right_ear) / 2.0

    def close(self) -> None:
        if hasattr(self, "landmarker"):
            self.landmarker.close()
