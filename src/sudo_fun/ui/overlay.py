"""OpenCV companion window for camera challenges and demo guides."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np


class CompanionOverlay:
    """Renders mirror camera feed with overlaid landmark skeleton and target demo."""

    def __init__(self, window_name: str = "sudo-fun: Mirror & Pose Guide"):
        self.window_name = window_name
        self._enabled = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def show(
        self,
        frame: np.ndarray,
        landmarks: Optional[List[Tuple[float, float, float, float]]] = None,
        demo_info: Optional[Dict[str, Any]] = None,
        status_text: str = "",
    ) -> Optional[str]:
        """Draws overlay and displays window. Returns key pressed if any."""
        if not self._enabled:
            return None

        h, w, _ = frame.shape
        display = frame.copy()

        # Draw detected skeleton landmarks if present
        if landmarks:
            # Draw key joints
            for lm in landmarks:
                cx, cy = int(lm[0] * w), int(lm[1] * h)
                cv2.circle(display, (cx, cy), 4, (0, 255, 0), -1)

            # Draw basic arm connections
            connections = [
                (11, 13), (13, 15),  # Left arm
                (12, 14), (14, 16),  # Right arm
                (11, 12),           # Shoulders
                (11, 23), (12, 24),  # Torso
            ]
            for idx1, idx2 in connections:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    p1 = (int(landmarks[idx1][0] * w), int(landmarks[idx1][1] * h))
                    p2 = (int(landmarks[idx2][0] * w), int(landmarks[idx2][1] * h))
                    cv2.line(display, p1, p2, (0, 255, 255), 2)

        # Draw demo box in top-right corner
        box_w, box_h = 160, 160
        cv2.rectangle(display, (w - box_w - 10, 10), (w - 10, 10 + box_h), (40, 40, 40), -1)
        cv2.rectangle(display, (w - box_w - 10, 10), (w - 10, 10 + box_h), (0, 200, 255), 2)
        cv2.putText(
            display,
            "TARGET POSE",
            (w - box_w + 10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
        )

        # Draw simple stylized target stick figure
        cx = w - box_w // 2 - 10
        cy = 85
        # Head
        cv2.circle(display, (cx, cy - 25), 10, (255, 255, 255), 2)
        # Body
        cv2.line(display, (cx, cy - 15), (cx, cy + 20), (255, 255, 255), 2)
        # Legs
        cv2.line(display, (cx, cy + 20), (cx - 15, cy + 50), (255, 255, 255), 2)
        cv2.line(display, (cx, cy + 20), (cx + 15, cy + 50), (255, 255, 255), 2)

        # Arms based on demo info
        if demo_info and demo_info.get("type") == "pose_skeleton":
            pose_id = demo_info.get("pose_id")
            if pose_id == "hands_above_head":
                cv2.line(display, (cx, cy - 10), (cx - 20, cy - 40), (0, 255, 0), 2)
                cv2.line(display, (cx, cy - 10), (cx + 20, cy - 40), (0, 255, 0), 2)
            elif pose_id == "t_pose":
                cv2.line(display, (cx, cy - 10), (cx - 30, cy - 10), (0, 255, 0), 2)
                cv2.line(display, (cx, cy - 10), (cx + 30, cy - 10), (0, 255, 0), 2)
            elif pose_id == "one_arm_raised":
                cv2.line(display, (cx, cy - 10), (cx - 20, cy + 10), (0, 255, 0), 2)
                cv2.line(display, (cx, cy - 10), (cx + 20, cy - 40), (0, 255, 0), 2)
            elif pose_id == "superhero":
                cv2.line(display, (cx, cy - 10), (cx - 20, cy + 5), (0, 255, 0), 2)
                cv2.line(display, (cx, cy - 10), (cx + 20, cy + 5), (0, 255, 0), 2)
        else:
            # Default arms
            cv2.line(display, (cx, cy - 10), (cx - 20, cy + 10), (255, 255, 255), 2)
            cv2.line(display, (cx, cy - 10), (cx + 20, cy + 10), (255, 255, 255), 2)

        # Status text footer
        if status_text:
            cv2.putText(
                display,
                status_text,
                (20, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

        try:
            cv2.imshow(self.window_name, display)
            k = cv2.waitKey(1) & 0xFF
            if k == ord(" "):
                return " "
            elif k == 27:  # Esc
                return "esc"
            elif k == ord("q"):
                return "q"
        except Exception:
            pass

        return None

    def close(self) -> None:
        if self._enabled:
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass
