# v1.0.1

## Bug Fixes

- **Fixed model path resolution for face landmark detection** - The fallback path for loading the MediaPipe face_landmarker model was missing the `assets/` directory component, causing `FileNotFoundError` when running face-detection-dependent challenges (e.g., blink detection). The path has been corrected to `~/.local/share/sudo-fun/assets/models/` to match the actual download location.

## Changes

- Updated `src/sudo_fun/perception/model_utils.py` to include `assets` directory in fallback model path lookup

## Installation

See [README](https://github.com/itsnyxdev/sudo-fun#readme) for installation and usage.
