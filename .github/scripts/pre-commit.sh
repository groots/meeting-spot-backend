#!/bin/bash
set -e

# This script runs before commit to ensure code is formatted correctly
echo "Running pre-commit checks..."

# Run our formatting script
.github/scripts/format_code.sh

# Check if any files were modified by the formatters
if git diff --name-only | grep -q '\.py$'; then
    echo "Formatting changed some files. Adding them to the commit..."
    git add $(git diff --name-only | grep '\.py$')
fi

echo "Pre-commit checks complete!"
