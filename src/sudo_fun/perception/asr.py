"""Offline speech recognition using Vosk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)  # Suppress verbose Vosk C++ logs


def get_default_model_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "assets" / "models" / "vosk-model-small-en-us-0.15",
        Path.home() / ".local" / "share" / "sudo-fun" / "models" / "vosk-model-small-en-us-0.15",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


class SpeechRecognizer:
    """Local offline speech recognition with optional grammar restriction."""

    def __init__(self, model_path: Optional[Path] = None, grammar: Optional[List[str]] = None):
        path = model_path or get_default_model_dir()
        if not path.is_dir():
            raise FileNotFoundError(f"Vosk model directory not found at {path}")

        self.model = Model(str(path))
        self.sample_rate = 16000.0

        if grammar:
            # Grammar constrained decoding ensures zero hallucination & ultra-low latency
            grammar_json = json.dumps(grammar + ["[unk]"])
            self.rec = KaldiRecognizer(self.model, self.sample_rate, grammar_json)
        else:
            self.rec = KaldiRecognizer(self.model, self.sample_rate)

    def process_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Feeds audio float32 [-1, 1] and returns recognized text if an utterance finished."""
        # Convert float32 to int16 PCM bytes
        int16_data = (audio_data * 32767).astype(np.int16).tobytes()

        if self.rec.AcceptWaveform(int16_data):
            res = json.loads(self.rec.Result())
            return res.get("text", "").strip().lower()
        else:
            partial = json.loads(self.rec.PartialResult())
            return partial.get("partial", "").strip().lower()
