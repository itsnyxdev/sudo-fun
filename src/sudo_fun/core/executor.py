"""Secure command execution through /usr/bin/sudo."""

from __future__ import annotations

import os
import sys
from typing import Sequence

SUDO_BINARY = "/usr/bin/sudo"


def execute_sudo(args: Sequence[str], dry_run: bool = False) -> int:
    """Executes the real /usr/bin/sudo with preserved argument boundaries.

    In production mode, this replaces the current process via os.execv.
    In dry-run mode (or for testing), it returns 0 without replacing the process.

    Args:
        args: Full argument list to pass to sudo.
        dry_run: When True, simulates execution without calling os.execv.

    Returns:
        int: Only returns in dry_run mode or on execution failure.
    """
    if not os.path.exists(SUDO_BINARY):
        sys.stderr.write(f"sudo-fun error: {SUDO_BINARY} not found on this system.\n")
        return 1

    if not os.access(SUDO_BINARY, os.X_OK):
        sys.stderr.write(f"sudo-fun error: {SUDO_BINARY} is not executable.\n")
        return 1

    cmd_vector = [SUDO_BINARY] + list(args)

    if dry_run:
        return 0

    # Ensure stdio buffers are flushed before replacing process
    sys.stdout.flush()
    sys.stderr.flush()

    try:
        # Replaces the current process with sudo.
        # This preserves TTY allocation, password prompt, and exit status.
        os.execv(SUDO_BINARY, cmd_vector)
    except OSError as err:
        sys.stderr.write(f"sudo-fun error: Failed to execute {SUDO_BINARY}: {err}\n")
        return 1
