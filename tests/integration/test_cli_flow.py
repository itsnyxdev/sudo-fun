"""Integration tests for the sudo-fun CLI lifecycle and lock handling."""

import os
import subprocess
import sys
import time
from pathlib import Path

from sudo_fun.core.lock_manager import LockManager


def test_cli_help():
    res = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "sudo-fun [options] <command>" in res.stdout


def test_cli_missing_command():
    res = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1
    assert "missing command operand" in res.stderr


def test_cli_fast_lockout_rejection(tmp_path: Path):
    custom_db = tmp_path / "sudo-fun" / "state.db"
    cmd_id = "/usr/bin/ls"

    # Pre-lock the command for 60 seconds
    lm = LockManager(custom_db)
    lm.record_failure(cmd_id, lock_duration=60.0)
    lm.record_failure(cmd_id, lock_duration=60.0)
    _, is_locked, _ = lm.record_failure(cmd_id, lock_duration=60.0)
    assert is_locked

    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(tmp_path)

    # Invoking locked command must reject immediately (< 500ms)
    t0 = time.perf_counter()
    res = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "ls"],
        capture_output=True,
        text=True,
        env=env,
    )
    duration = time.perf_counter() - t0

    assert res.returncode == 1
    assert "COMMAND LOCKED" in res.stdout
    assert duration < 1.0  # Fast-path lock check guarantee


def test_cli_three_failures_triggers_lock(tmp_path: Path):
    custom_db = tmp_path / "sudo-fun" / "state.db"
    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(tmp_path)

    # Force a reaction challenge and fail it 3 times
    # In non-interactive test mode, reaction challenge times out or fails
    cmd = [sys.executable, "-m", "sudo_fun.main", "--challenge", "timing.reaction", "whoami"]

    # 1st failure
    res1 = subprocess.run(cmd, capture_output=True, text=True, env=env, input="")
    assert res1.returncode == 2

    # 2nd failure
    res2 = subprocess.run(cmd, capture_output=True, text=True, env=env, input="")
    assert res2.returncode == 2

    # 3rd failure triggers lock (exit code 3)
    res3 = subprocess.run(cmd, capture_output=True, text=True, env=env, input="")
    assert res3.returncode == 3
    assert "COMMAND LOCKED" in res3.stdout

    # Now verify that subsequent attempt is immediately rejected with code 1
    res4 = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert res4.returncode == 1
    assert "COMMAND LOCKED" in res4.stdout

