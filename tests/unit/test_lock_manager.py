"""Tests for persistent LockManager with SQLite."""

import concurrent.futures
import time
from pathlib import Path
from sudo_fun.core.lock_manager import LockManager


def test_lock_manager_failure_progression(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    lm = LockManager(db_file)
    cmd = "/usr/bin/test_cmd"

    # Initially unlocked
    assert lm.get_lock_remaining(cmd) is None

    # 1st failure
    fails, locked, remaining = lm.record_failure(cmd, lock_duration=10.0)
    assert fails == 1
    assert not locked
    assert lm.get_lock_remaining(cmd) is None

    # 2nd failure
    fails, locked, remaining = lm.record_failure(cmd, lock_duration=10.0)
    assert fails == 2
    assert not locked
    assert lm.get_lock_remaining(cmd) is None

    # 3rd failure triggers lock
    fails, locked, remaining = lm.record_failure(cmd, lock_duration=10.0)
    assert fails == 3
    assert locked
    assert remaining > 0.0

    rem = lm.get_lock_remaining(cmd)
    assert rem is not None
    assert 0 < rem <= 10.0


def test_lock_manager_success_resets(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    lm = LockManager(db_file)
    cmd = "/usr/bin/test_cmd2"

    lm.record_failure(cmd)
    lm.record_failure(cmd)

    # Success resets counter
    lm.record_success(cmd)

    # Next failure should be 1, not 3
    fails, locked, _ = lm.record_failure(cmd)
    assert fails == 1
    assert not locked


def test_lock_manager_expiration(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    lm = LockManager(db_file)
    cmd = "/usr/bin/test_cmd3"

    # Fail 3 times with a short 0.2s lockout
    lm.record_failure(cmd, lock_duration=0.2)
    lm.record_failure(cmd, lock_duration=0.2)
    _, locked, _ = lm.record_failure(cmd, lock_duration=0.2)
    assert locked

    time.sleep(0.3)
    # After expiration, should be unlocked
    assert lm.get_lock_remaining(cmd) is None


def test_lock_manager_concurrent_failures(tmp_path: Path):
    db_file = tmp_path / "test_state.db"
    lm = LockManager(db_file)
    cmd = "/usr/bin/concurrent_cmd"

    # Run 10 threads trying to record failure simultaneously
    def _fail():
        l_instance = LockManager(db_file)
        return l_instance.record_failure(cmd, lock_duration=5.0)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_fail) for _ in range(5)]
        results = [f.result() for f in futures]

    # At least 3 failures must have registered and locked the command
    assert any(r[1] is True for r in results)
    assert lm.get_lock_remaining(cmd) is not None
