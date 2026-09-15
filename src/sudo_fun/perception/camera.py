"""Threaded non-blocking camera capture service."""

from __future__ import annotations

import threading
import time
from typing import Optional
import cv2
import numpy as np


_CAMERA_AVAILABLE_CACHE: Optional[bool] = None


def is_camera_available(device_index: int = 0, cached: bool = True) -> bool:
    """Checks if a usable webcam is present and accessible (cached by default)."""
    global _CAMERA_AVAILABLE_CACHE
    if cached and _CAMERA_AVAILABLE_CACHE is not None:
        return _CAMERA_AVAILABLE_CACHE

    cap = cv2.VideoCapture(device_index, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        _CAMERA_AVAILABLE_CACHE = False
        return False
    ret, frame = cap.read()
    cap.release()
    avail = bool(ret and frame is not None and frame.size > 0)
    _CAMERA_AVAILABLE_CACHE = avail
    return avail


class CameraService:
    """Non-blocking background frame grabber keeping only the freshest frame."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480):
        self.device_index = device_index
        self.width = width
        self.height = height

        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None

    def start(self) -> bool:
        """Opens camera and starts background reader thread."""
        if self._running:
            return True

        self._cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(self.device_index)

        if not self._cap.isOpened():
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _capture_loop(self) -> None:
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if ret and frame is not None:
                # Flip horizontally for intuitive mirror view
                frame = cv2.flip(frame, 1)
                with self._lock:
                    self._latest_frame = frame
            else:
                time.sleep(0.01)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns a copy of the freshest captured frame or None."""
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
            return None

    def stop(self) -> None:
        """Stops thread and closes camera device."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        with self._lock:
            self._latest_frame = None

    def __enter__(self) -> CameraService:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
