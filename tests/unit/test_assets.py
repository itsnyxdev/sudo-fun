"""Unit tests for unified asset and model resolution."""

import os
from pathlib import Path
import pytest

from sudo_fun.core.assets import (
    get_asset_path,
    get_assets_dir,
    get_model_path,
    get_models_dir,
    verify_model_exists,
)


def test_get_assets_dir_env_override(tmp_path: Path):
    custom_assets = tmp_path / "custom_assets"
    custom_assets.mkdir()
    os.environ["SUDO_FUN_ASSETS_DIR"] = str(custom_assets)
    try:
        resolved = get_assets_dir()
        assert resolved == custom_assets
    finally:
        del os.environ["SUDO_FUN_ASSETS_DIR"]


def test_get_model_path_existing():
    # Verify existing models in repo are resolved
    face_model = get_model_path("face_landmarker.task")
    assert face_model is not None
    assert face_model.is_file()
    assert verify_model_exists("face_landmarker.task")


def test_verify_model_exists_nonexistent():
    assert not verify_model_exists("nonexistent_model_12345.task")
