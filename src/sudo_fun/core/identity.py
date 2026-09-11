"""Command identity resolution and canonicalization."""

from __future__ import annotations

import os
import shutil
from typing import Sequence


def resolve_command_identity(args: Sequence[str]) -> tuple[str, list[str]]:
    """Resolves the target binary canonical path and separates sudo arguments.

    Returns:
        tuple[str, list[str]]:
            - canonical_identity: Absolute, symlink-resolved path to the target command binary,
              or a fallback identifier if no executable was provided.
            - original_args: The unmodified argument list to be passed verbatim to sudo.
    """
    if not args:
        return "empty", []

    original_args = list(args)

    # Find the target executable in the argument list.
    # Flags intended for sudo itself (e.g. -u user, -i, -s, -E) might precede the target command.
    target_cmd: str | None = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg.startswith("-"):
            # If flag takes a parameter, e.g. -u user, -g group, -D dir
            if arg in {"-u", "-g", "-D", "-C", "-p", "-T"} and idx + 1 < len(args):
                idx += 2
                continue
            idx += 1
            continue
        # First non-flag argument is the target executable
        target_cmd = arg
        break

    if target_cmd is None:
        # User passed flags only (e.g., `sudo-fun -i` or `sudo-fun -s`)
        return "builtin:shell_or_flags", original_args

    # Resolve executable location and dereference any symlinks
    which_path = shutil.which(target_cmd)
    if which_path:
        canonical_path = os.path.realpath(which_path)
    else:
        canonical_path = os.path.realpath(os.path.abspath(target_cmd))

    return canonical_path, original_args
