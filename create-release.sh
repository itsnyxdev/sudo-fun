#!/bin/bash
# Release script for v1.0.1
# This script creates the GitHub release and triggers the packaging workflow

set -e

REPO="itsnyxdev/sudo-fun"
TAG="v1.0.1"
BRANCH="main"

echo "================================"
echo "Creating Release: ${TAG}"
echo "Repository: ${REPO}"
echo "================================"
echo ""

# Step 1: Create the release using GitHub CLI
echo "Step 1: Creating GitHub release ${TAG}..."
echo "Command: gh release create ${TAG} --target ${BRANCH} --title '${TAG}' --notes-file CHANGELOG.md"
echo ""
echo "To run this command, execute:"
echo "  gh release create ${TAG} --target ${BRANCH} --title '${TAG}' --notes-file CHANGELOG.md"
echo ""

# Step 2: Trigger the release workflow
echo "Step 2: After the release is created, the workflow will auto-trigger."
echo "The 'Release Packaging' workflow will run automatically when the release is published."
echo ""
echo "To manually trigger if needed:"
echo "  gh workflow run release.yml -f tag=${TAG}"
echo ""

# Step 3: Monitor workflow
echo "Step 3: Monitor the workflow progress at:"
echo "  https://github.com/${REPO}/actions"
echo ""

echo "================================"
echo "Summary"
echo "================================"
echo "Release Tag:    ${TAG}"
echo "Target Branch:  ${BRANCH}"
echo "Release Notes:  CHANGELOG.md"
echo "Workflow:       .github/workflows/release.yml"
echo ""
echo "The Release Packaging workflow will:"
echo "  1. Download ML models and audio assets"
echo "  2. Create source archives (.tar.gz and .zip)"
echo "  3. Attach assets to the GitHub release"
echo ""
