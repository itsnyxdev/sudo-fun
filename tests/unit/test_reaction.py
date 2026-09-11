"""Tests for ReactionChallenge logic."""

import time
from sudo_fun.challenges.base import ChallengeState
from sudo_fun.challenges.reaction import ReactionChallenge


def test_reaction_false_start():
    rc = ReactionChallenge()
    rc.initialize("normal")

    # Initial state is wait
    res = rc.update(0.1, {"key_event": None})
    assert res.state == ChallengeState.RUNNING

    # Pressing space during wait phase triggers immediate false start failure
    res = rc.update(0.1, {"key_event": " "})
    assert res.state == ChallengeState.FAILED
    assert "False start" in res.message


def test_reaction_successful_timing():
    rc = ReactionChallenge()
    rc.initialize("easy")  # 1 round, threshold 0.5s

    # Advance time to trigger signal
    res = rc.update(5.0, {"key_event": None})
    assert res.state == ChallengeState.RUNNING
    assert "PRESS SPACE NOW" in res.message

    # Press space within threshold
    res = rc.update(0.1, {"key_event": " "})
    assert res.state == ChallengeState.SUCCESS
    assert "Success" in res.message


def test_reaction_too_slow():
    rc = ReactionChallenge()
    rc.initialize("easy")  # threshold 0.5s

    # Advance to signal phase
    rc.update(5.0, {"key_event": None})

    # Simulate waiting too long (e.g. 0.8s) before pressing
    rc._signal_start_time = time.time() - 0.8
    res = rc.update(0.1, {"key_event": " "})
    assert res.state == ChallengeState.FAILED
    assert "Too slow" in res.message
