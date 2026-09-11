"""Independent background audio player daemon that loops failed.mp3."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from sudo_fun.core.lock_manager import LockManager


def find_audio_asset() -> Path | None:
    """Locates the failed audio asset."""
    # First look in package assets relative to source
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "assets" / "failed.mp3",
        Path(__file__).resolve().parent.parent.parent.parent / "assets" / "failed.wav",
        Path.home() / ".local" / "share" / "sudo-fun" / "assets" / "failed.mp3",
        Path.home() / ".local" / "share" / "sudo-fun" / "assets" / "failed.wav",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def play_audio_file(audio_path: Path) -> bool:
    """Plays audio file using native Linux tools with fallback."""
    # PipeWire native player
    if shutil.which("pw-play"):
        try:
            res = subprocess.run(
                ["pw-play", str(audio_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            pass

    # PulseAudio native player
    if shutil.which("paplay"):
        try:
            res = subprocess.run(
                ["paplay", str(audio_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            pass

    # Fallback to python sounddevice if wav available
    wav_path = audio_path.with_suffix(".wav")
    if wav_path.is_file():
        try:
            from scipy.io import wavfile
            import sounddevice as sd

            rate, data = wavfile.read(str(wav_path))
            sd.play(data, rate)
            sd.wait()
            return True
        except Exception:
            pass

    # ALSA aplay fallback
    if shutil.which("aplay") and wav_path.is_file():
        try:
            subprocess.run(
                ["aplay", "-q", str(wav_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except Exception:
            pass

    return False


def run_daemon(command_id: str, duration: float, db_path: str | None = None) -> None:
    """Detached playback loop."""
    lock_mgr = LockManager(Path(db_path) if db_path else None)

    running = True

    def _sig_handler(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    audio_asset = find_audio_asset()
    if not audio_asset:
        sys.exit(0)

    end_time = time.time() + duration

    while running and time.time() < end_time:
        # Check if lock has been cleared or expired
        remaining = lock_mgr.get_lock_remaining(command_id)
        if remaining is None or remaining <= 0:
            break

        play_audio_file(audio_asset)

        # Brief pause between loops
        for _ in range(10):
            if not running or time.time() >= end_time:
                break
            time.sleep(0.1)

    # Clean up PID in DB
    active_pid = lock_mgr.get_active_audio_pid(command_id)
    if active_pid == os.getpid():
        lock_mgr.set_active_audio_pid(command_id, 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="sudo-fun failure audio daemon")
    parser.add_argument("--command-id", required=True, help="Command identity string")
    parser.add_argument(
        "--duration",
        type=float,
        default=600.0,
        help="Maximum playback duration in seconds",
    )
    parser.add_argument("--db-path", default=None, help="Custom SQLite DB path")
    args = parser.parse_args()

    run_daemon(args.command_id, args.duration, args.db_path)


if __name__ == "__main__":
    main()
