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


def test_resolve_attached_flag():
    cmd_id, args = resolve_command_identity(["-unobody", "whoami"])
    assert cmd_id.endswith("/whoami")
    assert args == ["-unobody", "whoami"]


def test_resolve_long_flag_equals():
    cmd_id, args = resolve_command_identity(["--user=nobody", "whoami"])
    assert cmd_id.endswith("/whoami")
    assert args == ["--user=nobody", "whoami"]


def test_resolve_option_terminator():
    cmd_id, args = resolve_command_identity(["--", "-u", "whoami"])
    # After '--', the target is '-u'
    assert "-u" in cmd_id
    assert args == ["--", "-u", "whoami"]
