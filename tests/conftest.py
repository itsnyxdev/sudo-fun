"""Pytest configuration and teardown fixtures."""

from __future__ import annotations

import os
import signal
import subprocess
import time
import pytest


def kill_failure_audio_processes() -> int:
    """Finds and terminates any running sudo-fun audio player daemon processes."""
    my_pid = os.getpid()
    killed = 0

    try:
        res = subprocess.run(
            ["pgrep", "-f", "sudo_fun.audio_player.daemon"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if not line.isdigit():
                    continue
                pid = int(line)
                if pid != my_pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        killed += 1
                    except (ProcessLookupError, PermissionError):
                        pass

        # Brief pause and force-kill any lingering processes if still alive
        if killed > 0:
            time.sleep(0.1)
            res2 = subprocess.run(
                ["pgrep", "-f", "sudo_fun.audio_player.daemon"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res2.returncode == 0:
                for line in res2.stdout.strip().splitlines():
                    line = line.strip()
                    if line.isdigit():
                        pid = int(line)
                        if pid != my_pid:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except (ProcessLookupError, PermissionError):
                                pass

    except Exception:
        pass

    return killed


@pytest.fixture(scope="session", autouse=True)
def cleanup_audio_daemons_session():
    """Ensures all background audio daemons are killed before and after test session."""
    kill_failure_audio_processes()
    yield
    kill_failure_audio_processes()


def pytest_sessionfinish(session, exitstatus):
    """Pytest hook executed after all tests have completed."""
    kill_failure_audio_processes()
