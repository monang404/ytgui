#!/bin/bash
# make_dist.sh - Package the app using git archive to avoid including secrets

# Ensure we're in the repository root
cd "$(dirname "$0")/.." || exit 1

# Output file name
OUTPUT="dist.zip"

echo "Creating distributable archive: $OUTPUT"
# git archive respects .gitignore, so cache/*.db, data/*.db, and *.log won't be included.
git archive HEAD -o "$OUTPUT"

echo "Packaging complete."
