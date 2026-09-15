"""Command identity resolution and canonicalization."""

from __future__ import annotations

import os
import shutil
from typing import Sequence


SUDO_OPTS_WITH_ARGS = {"-u", "-g", "-D", "-C", "-p", "-T", "-U", "-h", "-r", "-t"}
SUDO_LONG_OPTS_WITH_ARGS = {
    "--user", "--group", "--chdir", "--close-from", "--prompt",
    "--command-timeout", "--other-user", "--host", "--role", "--type",
}


def resolve_command_identity(args: Sequence[str]) -> tuple[str, list[str]]:
    """Resolves the target binary canonical path and separates sudo arguments.

    Handles:
    - Separate flags: -u nobody whoami
    - Attached flags: -unobody whoami
    - Long options: --user=nobody whoami or --user nobody whoami
    - Option terminator: sudo-fun -- -u whoami (executes binary named '-u')

    Returns:
        tuple[str, list[str]]:
            - canonical_identity: Absolute, symlink-resolved path to the target command binary,
              or a fallback identifier if no executable was provided.
            - original_args: The unmodified argument list to be passed verbatim to sudo.
    """
    if not args:
        return "empty", []

    original_args = list(args)

    target_cmd: str | None = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--":
            # Option terminator: the next argument is the command regardless of leading hyphens
            if idx + 1 < len(args):
                target_cmd = args[idx + 1]
            break

        if arg.startswith("-"):
            # Check long options
            if arg.startswith("--"):
                base_opt = arg.split("=", 1)[0]
                if base_opt in SUDO_LONG_OPTS_WITH_ARGS:
                    if "=" not in arg and idx + 1 < len(args):
                        idx += 2
                        continue
                idx += 1
                continue

            # Check short option with attached arg (e.g. -uadmin) or separate arg (-u admin)
            prefix = arg[:2]
            if prefix in SUDO_OPTS_WITH_ARGS:
                if len(arg) > 2:
                    # Attached argument like -uadmin
                    idx += 1
                    continue
                elif idx + 1 < len(args):
                    # Separate argument like -u admin
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
