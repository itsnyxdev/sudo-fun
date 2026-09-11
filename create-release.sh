#!/bin/bash
# Create v1.0.1 release tag
# This script uses the GitHub CLI to create the release and trigger the workflow

set -e

OWNER="itsnyxdev"
REPO="sudo-fun"
TAG="v1.0.1"
COMMIT="8cf79c64a0589fea4054e8f913099a465fb37e7a"

echo "Creating release tag: ${TAG}"
echo "Target commit: ${COMMIT}"

# Note: To trigger this workflow, you would run:
# gh release create v1.0.1 --target main --title "v1.0.1" --notes-file CHANGELOG.md
# gh workflow run release.yml -f tag=v1.0.1
