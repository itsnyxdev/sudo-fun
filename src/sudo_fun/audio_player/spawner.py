"""Process spawner for detached background audio playback."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sudo_fun.core.lock_manager import LockManager


def spawn_failure_audio(
    command_identity: str,
    duration: float = 600.0,
    lock_mgr: LockManager | None = None,
) -> int | None:
    """Spawns an independent detached audio playback daemon if not already running.

    Returns:
        int | None: The spawned worker PID, or None if already running or failed.
    """
    if lock_mgr is None:
        lock_mgr = LockManager()

    # Check if a process is already running for this command identity
    existing_pid = lock_mgr.get_active_audio_pid(command_identity)
    if existing_pid:
        return existing_pid

    # Build command to launch daemon using current python interpreter
    python_bin = sys.executable
    cmd = [
        python_bin,
        "-m",
        "sudo_fun.audio_player.daemon",
        "--command-id",
        command_identity,
        "--duration",
        str(duration),
    ]
    if str(lock_mgr.db_path):
        cmd.extend(["--db-path", str(lock_mgr.db_path)])

    env = dict(os.environ)

    try:
        # Detach child completely from parent session, tty, and stdio
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # setsid()
            close_fds=True,
            env=env,
        )
        lock_mgr.set_active_audio_pid(command_identity, proc.pid)
        return proc.pid
    except Exception:
        return None
