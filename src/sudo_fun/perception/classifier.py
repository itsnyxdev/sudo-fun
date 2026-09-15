"""Animal sound and general audio classification using YAMNet ONNX."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import onnxruntime as ort


from sudo_fun.core.assets import get_model_path, get_models_dir


def get_default_yamnet_paths() -> Tuple[Path, Path]:
    model_path = get_model_path("yamnet.onnx") or (get_models_dir() / "yamnet.onnx")
    csv_path = get_model_path("yamnet_class_map.csv") or (get_models_dir() / "yamnet_class_map.csv")
    return model_path, csv_path


# Mapping of animal names to AudioSet class substrings
ANIMAL_SOUND_MAP = {
    "dog": ["bark", "yip", "howl", "dog"],
    "cat": ["meow", "purr", "cat"],
    "cow": ["moo", "cattle", "bovinae"],
    "sheep": ["bleat", "sheep"],
    "pig": ["oink", "pig"],
    "duck": ["quack", "duck"],
    "chicken": ["cluck", "rooster", "fowl", "chicken"],
    "lion": ["roar", "roaring", "lion", "tiger"],
    "frog": ["croak", "ribbit", "frog"],
}


class AudioClassifier:
    """YAMNet ONNX inference engine for environmental and animal sounds."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        class_map_path: Optional[Path] = None,
    ):
        def_model, def_csv = get_default_yamnet_paths()
        m_path = model_path or def_model
        c_path = class_map_path or def_csv

        if not m_path.is_file():
            raise FileNotFoundError(f"YAMNet model not found at {m_path}")
        if not c_path.is_file():
            raise FileNotFoundError(f"YAMNet class map not found at {c_path}")

        # Load class map
        self.class_names: List[str] = []
        with open(c_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.class_names.append(row["display_name"])

        # Configure ONNX Runtime session
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(m_path), sess_options=opts)
        self.input_name = self.session.get_inputs()[0].name

    def classify(self, waveform: np.ndarray) -> List[Tuple[str, float]]:
        """Runs inference on 16kHz float32 mono waveform [-1.0, 1.0].

        Returns:
            Sorted list of (display_name, confidence) tuples.
        """
        if len(waveform) < 1600:  # Need at least 0.1s
            return []

        # Run model
        outputs = self.session.run(None, {self.input_name: waveform})
        # outputs[0] is prediction scores of shape (num_frames, 521)
        scores = outputs[0]

        # Mean across time frames
        mean_scores = np.mean(scores, axis=0)

        # Top 10 indices
        top_indices = np.argsort(mean_scores)[::-1][:10]
        results = []
        for idx in top_indices:
            name = self.class_names[idx] if idx < len(self.class_names) else f"class_{idx}"
            results.append((name, float(mean_scores[idx])))
        return results

    def is_animal_sound_detected(
        self, waveform: np.ndarray, target_animal: str, threshold: float = 0.08
    ) -> Tuple[bool, str, float]:
        """Evaluates if the waveform contains vocalizations matching the target animal."""
        keywords = ANIMAL_SOUND_MAP.get(target_animal.lower(), [target_animal.lower()])
        top_results = self.classify(waveform)

        for name, score in top_results:
            name_lower = name.lower()
            for kw in keywords:
                if kw in name_lower and score >= threshold:
                    return True, name, score

        best_name = top_results[0][0] if top_results else "silence"
        best_score = top_results[0][1] if top_results else 0.0
        return False, best_name, best_score
