"""Unified asset and model path resolution for sudo-fun."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_assets_dir() -> Path:
    """Resolves the root directory containing audio assets and models.

    Lookup priority:
    1. Environment variable SUDO_FUN_ASSETS_DIR
    2. User local share: ~/.local/share/sudo-fun/assets
    3. Package-relative assets directory
    4. Fallback default to ~/.local/share/sudo-fun/assets
    """
    env_dir = os.environ.get("SUDO_FUN_ASSETS_DIR")
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        if p.is_dir():
            return p

    candidates = [
        Path.home() / ".local" / "share" / "sudo-fun" / "assets",
        Path(__file__).resolve().parent.parent.parent.parent / "assets",
    ]
    for c in candidates:
        if c.is_dir():
            return c

    # Default fallback
    return candidates[0]


def get_models_dir() -> Path:
    """Resolves the directory containing offline ML models."""
    assets = get_assets_dir()
    models_dir = assets / "models"
    if models_dir.is_dir():
        return models_dir

    # Check alternative user share path without assets/ subfolder
    alt = Path.home() / ".local" / "share" / "sudo-fun" / "models"
    if alt.is_dir():
        return alt

    return models_dir


def get_asset_path(filename: str) -> Optional[Path]:
    """Finds an asset file (e.g. failed.mp3, failed.wav)."""
    assets = get_assets_dir()
    p = assets / filename
    if p.is_file():
        return p
    # Fallback to direct check in repo if assets_dir was redirected
    repo_asset = Path(__file__).resolve().parent.parent.parent.parent / "assets" / filename
    if repo_asset.is_file():
        return repo_asset
    return None


def get_model_path(model_filename: str) -> Optional[Path]:
    """Finds an ML model file or model directory."""
    models_dir = get_models_dir()
    p = models_dir / model_filename
    if p.exists():
        return p
    # Check alternative user share path
    alt = Path.home() / ".local" / "share" / "sudo-fun" / "models" / model_filename
    if alt.exists():
        return alt
    # Check repo root
    repo_model = Path(__file__).resolve().parent.parent.parent.parent / "assets" / "models" / model_filename
    if repo_model.exists():
        return repo_model
    return None


def verify_model_exists(model_filename: str) -> bool:
    """Returns True if the specified model file or directory exists and is accessible."""
    path = get_model_path(model_filename)
    if path is None:
        return False
    if path.is_file() and path.stat().st_size > 0:
        return True
    if path.is_dir():
        # Directory model (e.g. Vosk) - ensure it is not empty
        return any(path.iterdir())
    return False
