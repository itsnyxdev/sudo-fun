"""Main CLI entrypoint for sudo-fun."""

from __future__ import annotations

import argparse
import os
import sys

from sudo_fun import __version__
from sudo_fun.core.identity import resolve_command_identity
from sudo_fun.core.lock_manager import LockManager

# Preserve the pristine environment so mutations for OpenCV/Qt never leak to sudo
_PRISTINE_ENV = dict(os.environ)


def restore_pristine_environment() -> None:
    """Restores os.environ to its initial state before invoking sudo."""
    os.environ.clear()
    os.environ.update(_PRISTINE_ENV)


# Silence noisy Qt/OpenCV Wayland and font diagnostics on Linux desktops
os.environ.setdefault("QT_LOGGING_RULES", "qt.*=false;*.warning=false")
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
if os.environ.get("XDG_SESSION_TYPE") == "wayland":
    os.environ["XDG_SESSION_TYPE"] = "x11"


def _silence_qt_fonts() -> None:
    try:
        import cv2
        qt_fonts = os.path.join(os.path.dirname(cv2.__file__), "qt", "fonts")
        if not os.path.exists(qt_fonts):
            os.makedirs(qt_fonts, exist_ok=True)
    except Exception:
        pass


_silence_qt_fonts()


def parse_cli_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Separates sudo-fun internal flags from target sudo command and args."""
    parser = argparse.ArgumentParser(
        prog="sudo-fun",
        description="A playful gatekeeper around sudo that requires passing interactive challenges.",
        add_help=False,
    )
    parser.add_argument("--help", "-h", action="store_true", help="Show this help message and exit")
    parser.add_argument("--version", "-v", action="store_true", help="Show version and exit")
    parser.add_argument("--list-challenges", action="store_true", help="List all available challenges")
    parser.add_argument("--challenge", type=str, default=None, help="Force a specific challenge ID")
    parser.add_argument(
        "--difficulty",
        choices=["easy", "normal", "hard"],
        default="normal",
        help="Challenge difficulty",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke real sudo upon passing")

    sudo_fun_flags = []
    target_cmd_args = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--help", "-h", "--version", "-v", "--list-challenges", "--dry-run"):
            sudo_fun_flags.append(arg)
            i += 1
        elif arg in ("--challenge", "--difficulty"):
            if i + 1 < len(argv):
                sudo_fun_flags.extend([arg, argv[i + 1]])
                i += 2
            else:
                sudo_fun_flags.append(arg)
                i += 1
        else:
            target_cmd_args = argv[i:]
            break

    opts, _ = parser.parse_known_args(sudo_fun_flags)
    return opts, target_cmd_args


def main() -> None:
    opts, command_args = parse_cli_args(sys.argv[1:])

    if opts.help:
        print("Usage: sudo-fun [options] <command> [args...]")
        print("\nOptions:")
        print("  --help, -h               Show help message")
        print("  --version, -v            Show version")
        print("  --list-challenges        List all available challenges")
        print("  --challenge <id>         Test or force a specific challenge")
        print("  --difficulty <lvl>       Challenge difficulty: easy, normal, hard")
        print("  --dry-run                Simulate without executing real sudo")
        sys.exit(0)

    if opts.version:
        print(f"sudo-fun v{__version__}")
        sys.exit(0)

    if opts.list_challenges:
        from sudo_fun.challenges.registry import ChallengeRegistry
        registry = ChallengeRegistry()
        print("Available sudo-fun challenges:")
        for cid, cls in registry._challenges.items():
            inst = cls()
            print(f"  - {cid:<22} : {inst.name} ({inst.required_devices.name})")
        sys.exit(0)

    if not command_args:
        sys.stderr.write("sudo-fun: missing command operand\n")
        sys.stderr.write("Try 'sudo-fun --help' for more information.\n")
        sys.exit(1)

    # 1. Resolve canonical command identity
    canonical_id, original_args = resolve_command_identity(command_args)

    # 2. Fast-path persistent lock check (< 10ms, ZERO perception/ML imports)
    lock_mgr = LockManager()
    lock_remaining = lock_mgr.get_lock_remaining(canonical_id)
    if lock_remaining is not None and lock_remaining > 0:
        # Command is locked! Output message and exit immediately without loading models or UI
        mins = int(lock_remaining // 60)
        secs = int(lock_remaining % 60)
        print(f"🔒 COMMAND LOCKED")
        print(f"Too many failures for {canonical_id}.")
        print(f"Try again in {mins:02d}:{secs:02d}.")
        sys.exit(1)

    # Lazy-load UI, registry, and engine only when command is not locked
    from sudo_fun.audio_player.spawner import spawn_failure_audio
    from sudo_fun.challenges.base import ChallengeState
    from sudo_fun.challenges.registry import ChallengeRegistry
    from sudo_fun.core.engine import ChallengeEngine
    from sudo_fun.core.executor import execute_sudo
    from sudo_fun.ui.tui import TerminalUI

    tui = TerminalUI()
    registry = ChallengeRegistry()

    # 3. Select Challenge
    challenge = registry.select_random_challenge(specific_id=opts.challenge)

    # Get current failure count for visual indicator
    with lock_mgr._get_connection() as conn:
        row = conn.execute(
            "SELECT consecutive_fails FROM command_state WHERE command_identity = ?",
            (canonical_id,),
        ).fetchone()
        current_fails = int(row[0]) if row else 0

    # 4. Run Challenge Engine
    cmd_str = " ".join(original_args)
    engine = ChallengeEngine(
        challenge=challenge,
        command_str=cmd_str,
        fail_count=current_fails,
        tui=tui,
    )
    result = engine.run()

    # 5. Handle Outcome
    if result.state == ChallengeState.SUCCESS:
        lock_mgr.record_success(canonical_id)
        tui.print_success(result.message)
        restore_pristine_environment()
        sys.exit(execute_sudo(original_args, dry_run=opts.dry_run))

    elif result.state == ChallengeState.CANCELLED:
        print(f"\n[sudo-fun] {result.message}")
        sys.exit(130)

    elif result.state == ChallengeState.FAILED:
        new_fails, is_locked, remaining = lock_mgr.record_failure(canonical_id)
        if is_locked:
            spawn_failure_audio(canonical_id, duration=remaining, lock_mgr=lock_mgr)
            tui.print_locked(remaining)
            sys.exit(3)
        else:
            tui.print_failure(result.message, new_fails, max_fails=3)
            sys.exit(2)


if __name__ == "__main__":
    main()
