#!/bin/bash
set -e

# Configuration
REPO_ROOT="$(git rev-parse --show-toplevel)"
COMMIT_HASH="$(git rev-parse --short HEAD)"
RELEASE_DIR="$REPO_ROOT/release"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RELEASE_NAME="korrigo_release_$COMMIT_HASH"
ZIP_FILE="$RELEASE_DIR/$RELEASE_NAME.zip"
MANIFEST_FILE="$RELEASE_DIR/${RELEASE_NAME}_manifest.txt"
SHA_FILE="$RELEASE_DIR/${RELEASE_NAME}_SHA256.txt"

# Ensure clean slate
echo ">> Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Git is not clean. Commit or stash changes before releasing."
    exit 1
fi

echo ">> Preparing release directory..."
mkdir -p "$RELEASE_DIR"

# Build Release Pack (Source Only)
echo ">> Archiving source code (HEAD) to $ZIP_FILE..."
git archive --format=zip --output="$ZIP_FILE" HEAD

# Generate Manifest
echo ">> Generating manifest..."
unzip -l "$ZIP_FILE" > "$MANIFEST_FILE"

# Generate Checksum
echo ">> Calculating SHA256..."
sha256sum "$ZIP_FILE" > "$SHA_FILE"

echo "--------------------------------------------------------"
echo "✅ Release Pack Generated Successfully"
echo "   Archive:  $ZIP_FILE"
echo "   Manifest: $MANIFEST_FILE"
echo "   Checksum: $SHA_FILE"
echo "--------------------------------------------------------"
cat "$SHA_FILE"
echo "--------------------------------------------------------"
