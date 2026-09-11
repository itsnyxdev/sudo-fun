"""Unit tests for all interactive challenges."""

import numpy as np
from sudo_fun.challenges.animal import AnimalChallenge
from sudo_fun.challenges.base import ChallengeState
from sudo_fun.challenges.blink import BlinkChallenge
from sudo_fun.challenges.color import ColorChallenge
from sudo_fun.challenges.dance import DanceChallenge
from sudo_fun.challenges.pose import PoseChallenge


def test_pose_challenge_matching():
    pc = PoseChallenge()
    pc._target_key = "hands_above_head"
    pc._target_info = {
        "title": "Hands Above Head!",
        "desc": "Raise both hands!",
        "check": lambda angles: (angles.get("left_hand_up", 0) > 0.5 and angles.get("right_hand_up", 0) > 0.5),
        "demo_skeleton": [],
    }
    pc._hold_time_required = 0.2

    # Hands down -> still running, hold ratio low
    res = pc.update(0.1, {"pose_angles": {"left_hand_up": 0.0, "right_hand_up": 0.0}})
    assert res.state == ChallengeState.RUNNING
    assert res.metadata["hold_ratio"] == 0.0

    # Hands up for 0.1s -> holding
    res = pc.update(0.1, {"pose_angles": {"left_hand_up": 1.0, "right_hand_up": 1.0}})
    assert res.state == ChallengeState.RUNNING

    # Hands up for another 0.15s -> exceeds 0.2s hold requirement -> SUCCESS!
    res = pc.update(0.15, {"pose_angles": {"left_hand_up": 1.0, "right_hand_up": 1.0}})
    assert res.state == ChallengeState.SUCCESS


def test_dance_challenge_cycles():
    dc = DanceChallenge()
    dc.initialize("easy")
    dc._target_cycles = 2

    # Simulate up and down arm oscillations
    # Wave 1: up
    for _ in range(5):
        dc.update(0.1, {"pose_angles": {"left_hand_up": 1.0, "right_hand_up": 1.0}})
    # Wave 1: down
    for _ in range(6):
        dc.update(0.1, {"pose_angles": {"left_hand_up": 0.0, "right_hand_up": 0.0}})

    assert dc._cycle_count == 1

    # Wave 2: up
    for _ in range(6):
        dc.update(0.1, {"pose_angles": {"left_hand_up": 1.0, "right_hand_up": 1.0}})
    # Wave 2: down
    res = None
    for _ in range(6):
        res = dc.update(0.1, {"pose_angles": {"left_hand_up": 0.0, "right_hand_up": 0.0}})

    assert dc._cycle_count >= 2
    assert res.state == ChallengeState.SUCCESS


def test_blink_challenge_hysteresis():
    bc = BlinkChallenge()
    bc.initialize("normal")
    bc._target_duration = 1.0

    # 1 noisy frame below threshold should NOT fail immediately
    res = bc.update(0.03, {"ear": 0.15})
    assert res.state == ChallengeState.RUNNING

    # Next frame eyes open -> counter resets
    res = bc.update(0.03, {"ear": 0.30})
    assert res.state == ChallengeState.RUNNING
    assert bc._closed_consecutive_frames == 0

    # 3 consecutive closed frames -> declares blink -> FAILED
    bc.update(0.03, {"ear": 0.12})
    bc.update(0.03, {"ear": 0.12})
    res = bc.update(0.03, {"ear": 0.12})
    assert res.state == ChallengeState.FAILED
    assert "Blink detected" in res.message


def test_color_challenge_stroop():
    cc = ColorChallenge()
    cc.initialize("easy")
    cc._target_rounds = 1
    cc._word = "RED"
    cc._rendered_color = "blue"

    # User speaks written word ("red") -> tricked -> FAILED
    res = cc.update(0.1, {"speech_text": "i see red"})
    assert res.state == ChallengeState.FAILED
    assert "Tricked" in res.message

    # Re-initialize
    cc.initialize("easy")
    cc._target_rounds = 1
    cc._word = "RED"
    cc._rendered_color = "blue"

    # User speaks rendered color ("blue") -> SUCCESS
    res = cc.update(0.1, {"speech_text": "it is blue"})
    assert res.state == ChallengeState.SUCCESS


def test_animal_challenge_detection():
    ac = AnimalChallenge()
    ac.initialize("normal")
    ac._animal = "dog"

    # Audio matches dog bark -> SUCCESS
    res = ac.update(0.1, {
        "animal_detected": True,
        "detected_label": "Bark",
        "detected_score": 0.85,
    })
    assert res.state == ChallengeState.SUCCESS
    assert "Bark" in res.message
