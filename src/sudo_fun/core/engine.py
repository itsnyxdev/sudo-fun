"""Challenge Engine orchestrator and main execution loop."""

from __future__ import annotations

import select
import sys
import termios
import time
import tty
from typing import Optional

from sudo_fun.challenges.base import (
    BaseChallenge,
    ChallengeResult,
    ChallengeState,
    RequiredDevice,
)
from sudo_fun.perception.asr import SpeechRecognizer
from sudo_fun.perception.audio import AudioService
from sudo_fun.perception.camera import CameraService
from sudo_fun.perception.classifier import AudioClassifier
from sudo_fun.perception.face_detector import FaceDetector
from sudo_fun.perception.pose_detector import PoseDetector
from sudo_fun.ui.overlay import CompanionOverlay
from sudo_fun.ui.tui import TerminalUI


class ChallengeEngine:
    """Coordinates lifecycle, perception streaming, and UI feedback for challenges."""

    def __init__(
        self,
        challenge: BaseChallenge,
        command_str: str,
        fail_count: int,
        tui: Optional[TerminalUI] = None,
        overlay: Optional[CompanionOverlay] = None,
    ):
        self.challenge = challenge
        self.command_str = command_str
        self.fail_count = fail_count
        self.tui = tui or TerminalUI()
        self.overlay = overlay or CompanionOverlay()

    def run(self) -> ChallengeResult:
        """Runs the interactive challenge loop to completion."""
        # Initialize challenge parameters
        self.challenge.initialize()

        req = self.challenge.required_devices
        camera_svc = CameraService() if (req & RequiredDevice.CAMERA) else None
        audio_svc = AudioService() if (req & RequiredDevice.MICROPHONE) else None

        pose_detector = None
        face_detector = None
        asr = None
        classifier = None

        if req & RequiredDevice.CAMERA:
            if "pose" in self.challenge.id or "dance" in self.challenge.id:
                try:
                    pose_detector = PoseDetector()
                except Exception:
                    pass
            if "blink" in self.challenge.id:
                try:
                    face_detector = FaceDetector()
                except Exception:
                    pass

        if req & RequiredDevice.MICROPHONE:
            if "stroop" in self.challenge.id:
                try:
                    asr = SpeechRecognizer(grammar=["red", "green", "blue", "yellow", "white", "purple"])
                except Exception:
                    pass
            if "animal" in self.challenge.id:
                try:
                    classifier = AudioClassifier()
                except Exception:
                    pass

        # Start hardware services
        if camera_svc:
            camera_svc.start()
        if audio_svc:
            audio_svc.start()

        self.tui.start()

        # Terminal raw mode setup for non-blocking single keypress capture
        old_term_settings = None
        is_tty = sys.stdin.isatty()
        if is_tty:
            try:
                old_term_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                old_term_settings = None

        start_time = time.time()
        last_tick = start_time
        timeout = self.challenge.timeout_seconds
        result = ChallengeResult(ChallengeState.RUNNING, "Starting...")

        try:
            while result.state == ChallengeState.RUNNING:
                now = time.time()
                dt = now - last_tick
                last_tick = now

                elapsed = now - start_time
                if elapsed >= timeout:
                    result = ChallengeResult(
                        ChallengeState.FAILED,
                        f"Challenge timed out after {timeout:.1f} seconds!",
                    )
                    break

                # Gather keyboard events
                key_event = None
                if is_tty and select.select([sys.stdin], [], [], 0.0)[0]:
                    try:
                        ch = sys.stdin.read(1)
                        if ch == "\x03":  # Ctrl+C
                            result = ChallengeResult(
                                ChallengeState.CANCELLED,
                                "Challenge cancelled by user.",
                            )
                            break
                        elif ch == " ":
                            key_event = " "
                        elif ch in ("\r", "\n"):
                            key_event = "enter"
                        else:
                            key_event = ch
                    except Exception:
                        pass

                # Gather perception inputs
                frame = None
                pose_angles = None
                landmarks = None
                ear = None

                if camera_svc:
                    frame = camera_svc.get_latest_frame()
                    if frame is not None:
                        if pose_detector:
                            landmarks = pose_detector.process(frame)
                            if landmarks:
                                pose_angles = pose_detector.get_key_angles(landmarks)
                        if face_detector:
                            ear = face_detector.process_ear(frame)

                speech_text = None
                animal_detected = False
                detected_label = ""
                detected_score = 0.0

                if audio_svc:
                    # Incremental streaming for Vosk ASR (prevents duplicate chunks)
                    if asr:
                        new_audio = audio_svc.get_new_audio_samples()
                        speech_text = asr.process_audio(new_audio)

                    # 1.0s sliding window for environmental audio classification
                    if classifier and hasattr(self.challenge, "_animal"):
                        audio_chunk = audio_svc.get_audio_window(1.0)
                        animal_detected, detected_label, detected_score = classifier.is_animal_sound_detected(
                            audio_chunk, self.challenge._animal
                        )

                # Build context
                context = {
                    "frame": frame,
                    "landmarks": landmarks,
                    "pose_angles": pose_angles,
                    "ear": ear,
                    "speech_text": speech_text,
                    "animal_detected": animal_detected,
                    "detected_label": detected_label,
                    "detected_score": detected_score,
                    "key_event": key_event,
                }

                # Update challenge
                result = self.challenge.update(dt, context)

                if result.metadata and result.metadata.get("reset_speech"):
                    if asr:
                        asr.reset()
                    if audio_svc:
                        audio_svc.reset_speech_buffer()

                # Render UI
                rem_time = max(0.0, timeout - elapsed)
                time_ratio = rem_time / timeout
                time_text = f"{rem_time:.1f}s"

                self.tui.update(
                    command=self.command_str,
                    challenge_name=self.challenge.name,
                    instructions=self.challenge.description,
                    status_message=result.message,
                    time_ratio=time_ratio,
                    time_text=time_text,
                    fail_count=self.fail_count,
                )

                # Render companion overlay window if camera challenge
                if frame is not None:
                    demo_info = self.challenge.render_demo()
                    overlay_key = self.overlay.show(
                        frame=frame,
                        landmarks=landmarks,
                        demo_info=demo_info,
                        status_text=result.message,
                    )
                    if overlay_key == "q" or overlay_key == "esc":
                        result = ChallengeResult(
                            ChallengeState.CANCELLED,
                            "Cancelled from companion window.",
                        )
                        break
                    elif overlay_key == " ":
                        key_event = " "

                time.sleep(0.03)

        finally:
            # Restore terminal attributes first before any output
            if is_tty and old_term_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term_settings)
                except Exception:
                    pass

            self.tui.stop()
            self.overlay.close()

            if camera_svc:
                camera_svc.stop()
            if audio_svc:
                audio_svc.stop()
            if pose_detector:
                pose_detector.close()
            if face_detector:
                face_detector.close()
            self.challenge.cleanup()

        return result
