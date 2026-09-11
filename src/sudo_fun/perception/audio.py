"""Threaded microphone recording service using sounddevice."""

from __future__ import annotations

import collections
import threading
from typing import Optional
import numpy as np
import sounddevice as sd


def is_microphone_available() -> bool:
    """Checks if a usable audio input device is present and accessible."""
    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        if default_input is not None and default_input >= 0:
            return True
        # Check if any input device exists
        for d in devices:
            if d.get("max_input_channels", 0) > 0:
                return True
        return False
    except Exception:
        return False


class AudioService:
    """Non-blocking background audio capture with a thread-safe circular buffer."""

    def __init__(self, sample_rate: int = 16000, buffer_duration_sec: float = 5.0):
        self.sample_rate = sample_rate
        self.buffer_size = int(sample_rate * buffer_duration_sec)

        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._buffer: collections.deque = collections.deque(maxlen=self.buffer_size)
        self._running = False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            pass  # Overflow/underflow ignorable in games
        # indata is shape (frames, channels)
        mono = indata[:, 0].astype(np.float32)
        with self._lock:
            self._buffer.extend(mono)

    def start(self) -> bool:
        """Starts audio input stream."""
        if self._running:
            return True

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            return True
        except Exception:
            return False

    def get_audio_window(self, duration_sec: float) -> np.ndarray:
        """Returns the most recent N seconds of audio as float32 array."""
        num_samples = int(duration_sec * self.sample_rate)
        with self._lock:
            if len(self._buffer) == 0:
                return np.zeros(num_samples, dtype=np.float32)
            arr = np.array(self._buffer, dtype=np.float32)

        if len(arr) < num_samples:
            # Pad with leading zeros
            pad = np.zeros(num_samples - len(arr), dtype=np.float32)
            return np.concatenate([pad, arr])
        return arr[-num_samples:]

    def stop(self) -> None:
        """Stops audio stream and frees resources."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        with self._lock:
            self._buffer.clear()

    def __enter__(self) -> AudioService:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
