"""Utilities for locating and safely downloading offline ML model assets."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

MODEL_URLS = {
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/latest/face_landmarker.task"
    ),
    "pose_landmarker_lite.task": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
    ),
}


def get_model_path(filename: str) -> Path:
    """Return an existing model path, downloading it when necessary."""
    if filename not in MODEL_URLS:
        raise ValueError(f"Unknown model: {filename}")

    install_root = Path(__file__).resolve().parents[3]
    candidates = [
        install_root / "assets" / "models" / filename,
        Path.home() / ".local" / "share" / "sudo-fun" / "models" / filename,
    ]

    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate

    target = candidates[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".download")

    if os.environ.get("SUDO_FUN_OFFLINE") == "1":
        raise FileNotFoundError(
            f"ML model is missing: {target}. "
            "Install the model first or unset SUDO_FUN_OFFLINE."
        )

    try:
        with urlopen(MODEL_URLS[filename], timeout=30) as response, tmp.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    except (OSError, URLError) as exc:
        tmp.unlink(missing_ok=True)
        raise FileNotFoundError(
            f"Unable to obtain ML model {filename!r}. "
            f"Expected it at {target}. Check your network connection or install it manually."
        ) from exc

    if not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise FileNotFoundError(f"Downloaded ML model is empty: {target}")

    tmp.replace(target)
    return target
