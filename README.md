# ⚡ sudo-fun

> **A serious, modular Linux wrapper around `/usr/bin/sudo` that turns privileged execution into proof-of-fun interactive challenges.**

[![Tests](https://img.shields.io/badge/tests-23%20passed-brightgreen.svg)](#testing)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#requirements)
[![Linux](https://img.shields.io/badge/platform-Linux%20(PipeWire%20%7C%20Pulse%20%7C%20ALSA)-orange.svg)](#features)

---

## 🎯 Concept

Instead of immediately running a privileged command, `sudo-fun` randomly selects an interactive challenge. The user must successfully complete the challenge first:

```bash
sudo-fun <command> [args...]
```

If the challenge succeeds, `sudo-fun` executes the original command through the genuine `/usr/bin/sudo`, preserving all argument boundaries and flags verbatim.

If the user fails **3 consecutive times** for that command:
1. The command identity is **locked for 10 minutes**.
2. A detached, independent background process is spawned that continuously loops `failed.mp3` for the duration of the lockout.
3. The main `sudo-fun` process exits immediately.
4. Any repeated invocations during the 10-minute lockout period are rejected on a **fast path (< 10ms)** without initializing cameras, microphones, or ML models.

---

## 🎮 The 6 Interactive Challenges

| Challenge | Type | Hardware | Detection Mechanism |
| :--- | :--- | :--- | :--- |
| **Lightning Reflexes** (`timing.reaction`) | Timing | Keyboard | Zero-ML random-delay trigger with false-start detection |
| **Pose Match** (`vision.pose_match`) | Vision | Webcam | Geometric joint angles (vector dot product) against target pose |
| **Dance Groove** (`vision.dance`) | Vision | Webcam | Temporal oscillation & wave cycle analysis |
| **Don't Blink!** (`vision.dont_blink`) | Vision | Webcam | Eye Aspect Ratio (EAR) with noise hysteresis & head-movement tolerance |
| **Stroop Color Voice** (`audio.stroop_color`) | Audio | Microphone | Grammar-constrained offline Vosk speech recognition (< 50ms latency) |
| **Animal Sound** (`audio.animal_sound`) | Audio | Microphone | Lightweight YAMNet ONNX AudioSet classification (bark, moo, meow, etc.) |

---

## 🔒 Security & Privacy Guarantees

- **No Root Wrapper**: `sudo-fun` runs completely unprivileged. It never modifies, intercepts, or replaces `/usr/bin/sudo`.
- **Argument Preservation**: Arguments are passed directly via `os.execv("/usr/bin/sudo", ["/usr/bin/sudo"] + original_args)` with zero shell interpolation (`shell=False`), preventing command injection or glob expansion vulnerabilities.
- **Local-Only Inference**: All perception models (MediaPipe Tasks, Vosk, YAMNet ONNX) run 100% offline on CPU. No audio or video frames are ever uploaded or written to disk.
- **State File Permissions**: Persistent state directory (`~/.local/state/sudo-fun/`) is strictly permission-locked to `0700` (`rwx------`), and the SQLite WAL database is locked to `0600` (`rw-------`).

---

## 🚀 Installation & Quick Start

### 1. Requirements
- Linux with Python 3.10+ (Python 3.11/3.12 recommended)
- Webcam and microphone (optional; gracefully falls back to keyboard reaction challenges if absent)
- Audio system: PipeWire (`pw-play`), PulseAudio (`paplay`), or ALSA

### 2. Automatic Install (Recommended)

Run the automated installer script, which detects your Linux distribution, installs required system packages, sets up an isolated virtual environment, and configures Bash, Zsh, or Fish:

```bash
curl -sSL https://raw.githubusercontent.com/itsnyxdev/sudo-fun/main/install.sh | bash
```

Or clone and run locally:

```bash
git clone https://github.com/itsnyxdev/sudo-fun.git
cd sudo-fun
./install.sh
```

#### Installer Flags
- `--alias`: Automatically configure `alias sudo="sudo-fun"` in your shell.
- `--no-alias`: Skip shell alias configuration.
- `--skip-deps`: Skip system package manager package installation.
- `--dir <path>`: Custom installation directory (default: `~/.local/share/sudo-fun`).
- `--bin-dir <path>`: Custom launcher path (default: `~/.local/bin`).

### 3. Manual Setup with `uv`
```bash
# Clone the repository
git clone https://github.com/itsnyxdev/sudo-fun.git
cd sudo-fun

# Create virtual environment and install
uv venv --python python3.11 .venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Basic Usage
```bash
# Execute command through sudo-fun
sudo-fun whoami

# Test with simulated dry-run (does not execute real sudo on pass)
sudo-fun --dry-run apt update

# Test a specific challenge
sudo-fun --challenge timing.reaction ls -la

# Adjust difficulty (easy, normal, hard)
sudo-fun --difficulty hard systemctl restart nginx
```

---

## 🧪 Testing

Run the full pytest suite (23 unit and integration tests):

```bash
.venv/bin/pytest tests/
```

### Key Test Coverage
- `tests/unit/test_identity.py`: Canonical binary path resolution & symlink dereferencing.
- `tests/unit/test_lock_manager.py`: Multi-threaded atomic SQLite transactions, failure counter progression, and lock expiration.
- `tests/unit/test_executor.py`: Verifies `os.execv` argument vector fidelity.
- `tests/unit/test_challenges.py`: Validates pose angle math, dance cycle hysteresis, EAR blink calculations, Stroop speech logic, and animal classification.
- `tests/integration/test_cli_flow.py`: End-to-end 3-failure lockout simulation, fast-path lock rejection (< 10ms), and CLI exit code compliance.

---

## 📁 Project Structure

```
sudo-fun/
├── assets/
│   ├── failed.mp3              # Generated comical failure audio
│   ├── failed.wav              # WAV source
│   └── models/                 # Lightweight offline models
│       ├── face_landmarker.task
│       ├── pose_landmarker_lite.task
│       ├── yamnet.onnx
│       ├── yamnet_class_map.csv
│       └── vosk-model-small-en-us-0.15/
├── src/
│   └── sudo_fun/
│       ├── main.py             # CLI entrypoint & fast-path gatekeeper
│       ├── core/
│       │   ├── identity.py     # Command identity resolution
│       │   ├── lock_manager.py # Persistent SQLite WAL lock manager
│       │   ├── executor.py     # os.execv safe sudo delegation
│       │   └── engine.py       # Main challenge lifecycle orchestrator
│       ├── challenges/         # 6 interactive challenges
│       ├── perception/         # Camera, audio, pose, face, ASR, classifier
│       ├── ui/                 # Rich live TUI & OpenCV companion overlay
│       └── audio_player/       # Detached background failed.mp3 daemon & spawner
└── tests/                      # Unit & integration test suites
```
