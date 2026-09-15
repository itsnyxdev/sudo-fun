"""Unit tests for administrative CLI tools and LockManager management."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from sudo_fun.core.lock_manager import LockManager


def test_is_pid_alive_permission_error():
    # EPERM means process exists but owned by someone else
    with patch("os.kill", side_effect=PermissionError):
        assert LockManager._is_pid_alive(12345)


def test_lock_manager_admin_operations(tmp_path: Path):
    db_path = tmp_path / "test_admin.db"
    lm = LockManager(db_path)

    cmd1 = "/usr/bin/apt"
    cmd2 = "/usr/bin/systemctl"

    # Create failures and a lock
    lm.record_failure(cmd1, lock_duration=60.0)
    lm.record_failure(cmd1, lock_duration=60.0)
    lm.record_failure(cmd1, lock_duration=60.0)
    lm.set_active_audio_pid(cmd1, 999999)

    lm.record_failure(cmd2, lock_duration=60.0)

    states = lm.get_all_states()
    assert len(states) == 2

    # Clear single lock
    lm.clear_lock(cmd1, kill_audio=False)
    assert lm.get_lock_remaining(cmd1) is None

    # Clear all locks
    count = lm.clear_all_locks()
    assert count >= 1
    assert lm.get_lock_remaining(cmd2) is None


def test_cli_admin_flags(tmp_path: Path):
    env = dict(os.environ)
    env["XDG_STATE_HOME"] = str(tmp_path)

    # 1. Test --status on clean database
    res = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "--status"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res.returncode == 0
    assert "No tracked commands" in res.stdout or "Command Status" in res.stdout

    # 2. Record a failure and check --status table output
    lm = LockManager(tmp_path / "sudo-fun" / "state.db")
    lm.record_failure("/usr/bin/ls")

    res2 = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "--status"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res2.returncode == 0
    assert "/usr/bin/ls" in res2.stdout

    # 3. Test --unlock
    res3 = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "--unlock", "ls"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res3.returncode == 0
    assert "Unlocked" in res3.stdout

    # 4. Test --kill-audio
    res4 = subprocess.run(
        [sys.executable, "-m", "sudo_fun.main", "--kill-audio"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert res4.returncode == 0
