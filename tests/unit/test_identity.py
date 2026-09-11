"""Tests for command identity resolution."""

from sudo_fun.core.identity import resolve_command_identity


def test_resolve_empty():
    cmd_id, args = resolve_command_identity([])
    assert cmd_id == "empty"
    assert args == []


def test_resolve_standard_command():
    cmd_id, args = resolve_command_identity(["whoami"])
    assert cmd_id.endswith("/whoami")
    assert args == ["whoami"]


def test_resolve_command_with_flags():
    cmd_id, args = resolve_command_identity(["ls", "-la", "/var/log"])
    assert cmd_id.endswith("/ls")
    assert args == ["ls", "-la", "/var/log"]


def test_resolve_sudo_flags_before_command():
    cmd_id, args = resolve_command_identity(["-u", "nobody", "id", "-u"])
    assert cmd_id.endswith("/id")
    assert args == ["-u", "nobody", "id", "-u"]


def test_resolve_only_flags():
    cmd_id, args = resolve_command_identity(["-i"])
    assert cmd_id == "builtin:shell_or_flags"
    assert args == ["-i"]
