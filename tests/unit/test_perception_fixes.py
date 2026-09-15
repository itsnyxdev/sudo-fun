"""Unit tests for perception fixes in v1.0.1: audio streaming and model fallback."""

from unittest.mock import patch
import numpy as np
import pytest

from sudo_fun.challenges.base import RequiredDevice
from sudo_fun.challenges.registry import ChallengeRegistry
from sudo_fun.perception.audio import AudioService


def test_audio_service_incremental_reading():
    svc = AudioService(sample_rate=16000, buffer_duration_sec=1.0)
    
    # Simulate feeding two 512-sample chunks via callback
    chunk1 = np.ones((512, 1), dtype=np.float32) * 0.5
    chunk2 = np.ones((512, 1), dtype=np.float32) * 0.8

    svc._audio_callback(chunk1, 512, None, None)
    
    # First read should yield chunk1
    read1 = svc.get_new_audio_samples()
    assert len(read1) == 512
    assert np.allclose(read1, 0.5)

    # Immediately reading again should return empty (no duplicate samples)
    read_empty = svc.get_new_audio_samples()
    assert len(read_empty) == 0

    # Feed second chunk
    svc._audio_callback(chunk2, 512, None, None)
    read2 = svc.get_new_audio_samples()
    assert len(read2) == 512
    assert np.allclose(read2, 0.8)


def test_registry_fallback_when_models_missing():
    registry = ChallengeRegistry()

    # Simulate camera and microphone being available, but no models found on disk
    with patch("sudo_fun.challenges.registry.verify_model_exists", return_value=False):
        chosen = registry.select_random_challenge(
            available_devices=RequiredDevice.CAMERA | RequiredDevice.MICROPHONE | RequiredDevice.KEYBOARD
        )
        # Because all ML models are missing, must fall back to Reaction challenge!
        assert chosen.id == "timing.reaction"
