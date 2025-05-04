#!/usr/bin/env python3
"""
Format all Python files in the project using Black.

This script automatically excludes files listed in .noformat.
"""

import os
import subprocess
import sys
from pathlib import Path


def get_excluded_files():
    """Get list of files to exclude from formatting."""
    noformat_path = Path(".noformat")
    if not noformat_path.exists():
        return []

    excluded = []
    with open(noformat_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                excluded.append(line)

    return excluded


def format_files():
    """Run Black formatter on all Python files, excluding specified ones."""
    excluded = get_excluded_files()

    # Convert excluded files to command-line format
    exclude_pattern = "|".join(excluded) if excluded else None

    cmd = ["black"]
    if exclude_pattern:
        cmd.extend(["--exclude", exclude_pattern])
    cmd.append(".")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}", file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(format_files())
