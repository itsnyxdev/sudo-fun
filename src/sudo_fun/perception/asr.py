"""Offline speech recognition using Vosk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
import numpy as np
from vosk import KaldiRecognizer, Model, SetLogLevel

from sudo_fun.core.assets import get_model_path, get_models_dir

SetLogLevel(-1)  # Suppress verbose Vosk C++ logs


def get_default_model_dir() -> Path:
    found = get_model_path("vosk-model-small-en-us-0.15")
    if found and found.is_dir():
        return found
    return get_models_dir() / "vosk-model-small-en-us-0.15"


class SpeechRecognizer:
    """Local offline speech recognition with optional grammar restriction."""

    def __init__(self, model_path: Optional[Path] = None, grammar: Optional[List[str]] = None):
        path = model_path or get_default_model_dir()
        if not path.is_dir():
            raise FileNotFoundError(f"Vosk model directory not found at {path}")

        self.model = Model(str(path))
        self.sample_rate = 16000.0
        self.grammar = grammar
        self._init_recognizer()

    def _init_recognizer(self) -> None:
        if self.grammar:
            # Grammar constrained decoding ensures zero hallucination & ultra-low latency
            grammar_json = json.dumps(self.grammar + ["[unk]"])
            self.rec = KaldiRecognizer(self.model, self.sample_rate, grammar_json)
        else:
            self.rec = KaldiRecognizer(self.model, self.sample_rate)

    def reset(self) -> None:
        """Resets the internal KaldiRecognizer state between rounds."""
        self._init_recognizer()

    def process_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """Feeds audio float32 [-1, 1] and returns recognized text if an utterance finished."""
        if len(audio_data) == 0:
            return None

        # Convert float32 to int16 PCM bytes
        int16_data = (audio_data * 32767).astype(np.int16).tobytes()

        if self.rec.AcceptWaveform(int16_data):
            res = json.loads(self.rec.Result())
            return res.get("text", "").strip().lower()
        else:
            partial = json.loads(self.rec.PartialResult())
            return partial.get("partial", "").strip().lower()
