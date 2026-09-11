"""Unit tests for safe sudo command execution."""

from unittest.mock import patch
from sudo_fun.core.executor import execute_sudo, SUDO_BINARY


def test_execute_sudo_dry_run():
    args = ["apt", "install", "-y", "nginx"]
    code = execute_sudo(args, dry_run=True)
    assert code == 0


def test_execute_sudo_preserves_arguments():
    with patch("os.execv") as mock_execv, patch("os.path.exists", return_value=True), patch("os.access", return_value=True):
        args = ["sh", "-c", "echo 'hello world' > /tmp/test.txt; rm -rf /foo"]
        execute_sudo(args, dry_run=False)

        mock_execv.assert_called_once()
        called_bin, called_argv = mock_execv.call_args[0]
        assert called_bin == SUDO_BINARY
        # Crucial check: argument vector is preserved exactly as an array with no shell interpolation
        assert called_argv == [SUDO_BINARY, "sh", "-c", "echo 'hello world' > /tmp/test.txt; rm -rf /foo"]
