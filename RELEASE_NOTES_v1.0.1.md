# v1.0.1 Release Notes

## Bug Fixes

- **Fixed model path resolution for face landmark detection** - The fallback path for loading the MediaPipe face_landmarker model was missing the `assets/` directory component, causing `FileNotFoundError` when running face-detection-dependent challenges (e.g., blink detection). The path has been corrected to `~/.local/share/sudo-fun/assets/models/` to match the actual download location. ([#1](https://github.com/itsnyxdev/sudo-fun/commit/38fd8e63dd941aa0acb03c0282fd24507f1e1343))

## Changelog

- Updated `src/sudo_fun/perception/model_utils.py` to include `assets` directory in fallback model path lookup
