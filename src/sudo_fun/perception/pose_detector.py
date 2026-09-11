"""Pose estimation service and geometric joint calculations."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2
import mediapipe as mp
import numpy as np


class PoseLandmarkIndex:
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28


def calculate_angle_2d(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
) -> float:
    """Calculates angle in degrees between vectors (p1-p2) and (p3-p2).
    p2 is the vertex (e.g. elbow or shoulder).
    """
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])

    dot = v1[0] * v2[0] + v1[1] * v2[1]
    norm1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
    norm2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

    if norm1 * norm2 == 0:
        return 0.0

    cos_val = max(-1.0, min(1.0, dot / (norm1 * norm2)))
    return math.degrees(math.acos(cos_val))


def _get_model_path() -> str:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "assets" / "models" / "pose_landmarker_lite.task",
        Path.home() / ".local" / "share" / "sudo-fun" / "models" / "pose_landmarker_lite.task",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return str(candidates[0])


class PoseDetector:
    """MediaPipe Pose detection wrapper supporting Tasks API."""

    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        model_path = _get_model_path()
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            min_pose_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.landmarker = PoseLandmarker.create_from_options(options)

    def process(self, frame_bgr: np.ndarray) -> Optional[List[Tuple[float, float, float, float]]]:
        """Extracts 33 pose landmarks.

        Returns:
            List of (x, y, z, visibility) tuples, or None if no person detected.
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = self.landmarker.detect(mp_image)

        if not results.pose_landmarks:
            return None

        landmarks = []
        for lm in results.pose_landmarks[0]:
            vis = getattr(lm, "visibility", 1.0)
            landmarks.append((lm.x, lm.y, lm.z, vis))
        return landmarks

    def get_key_angles(
        self, landmarks: List[Tuple[float, float, float, float]]
    ) -> Dict[str, float]:
        """Computes key body joint angles invariant to body scale/position."""
        def pt(idx: int) -> Tuple[float, float]:
            return (landmarks[idx][0], landmarks[idx][1])

        left_elbow = calculate_angle_2d(
            pt(PoseLandmarkIndex.LEFT_SHOULDER),
            pt(PoseLandmarkIndex.LEFT_ELBOW),
            pt(PoseLandmarkIndex.LEFT_WRIST),
        )
        right_elbow = calculate_angle_2d(
            pt(PoseLandmarkIndex.RIGHT_SHOULDER),
            pt(PoseLandmarkIndex.RIGHT_ELBOW),
            pt(PoseLandmarkIndex.RIGHT_WRIST),
        )
        left_shoulder = calculate_angle_2d(
            pt(PoseLandmarkIndex.LEFT_HIP),
            pt(PoseLandmarkIndex.LEFT_SHOULDER),
            pt(PoseLandmarkIndex.LEFT_ELBOW),
        )
        right_shoulder = calculate_angle_2d(
            pt(PoseLandmarkIndex.RIGHT_HIP),
            pt(PoseLandmarkIndex.RIGHT_SHOULDER),
            pt(PoseLandmarkIndex.RIGHT_ELBOW),
        )

        return {
            "left_elbow": left_elbow,
            "right_elbow": right_elbow,
            "left_shoulder": left_shoulder,
            "right_shoulder": right_shoulder,
            "left_hand_up": 1.0 if pt(PoseLandmarkIndex.LEFT_WRIST)[1] < pt(PoseLandmarkIndex.NOSE)[1] else 0.0,
            "right_hand_up": 1.0 if pt(PoseLandmarkIndex.RIGHT_WRIST)[1] < pt(PoseLandmarkIndex.NOSE)[1] else 0.0,
        }

    def close(self) -> None:
        if hasattr(self, "landmarker"):
            self.landmarker.close()
