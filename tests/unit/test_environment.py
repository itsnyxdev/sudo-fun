"""Unit test for environment variable restoration before sudo execution."""

import os
from sudo_fun.main import _PRISTINE_ENV, restore_pristine_environment


def test_restore_pristine_environment():
    # Mutate os.environ as Qt or OpenCV would
    os.environ["XDG_SESSION_TYPE"] = "x11"
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    os.environ["TEST_MUTATED_VAR"] = "corrupted"

    # Call restore
    restore_pristine_environment()

    # Verify mutations are wiped or restored to original
    assert "TEST_MUTATED_VAR" not in os.environ
    if "XDG_SESSION_TYPE" in _PRISTINE_ENV:
        assert os.environ["XDG_SESSION_TYPE"] == _PRISTINE_ENV["XDG_SESSION_TYPE"]
    else:
        assert "XDG_SESSION_TYPE" not in os.environ
