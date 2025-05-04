#!/usr/bin/env python3
"""
Format all migration files and other problem files in the repository.

This script specifically targets migrations and other directories
that are showing formatting errors.
"""

import os
import subprocess
import sys
from pathlib import Path


def get_excluded_files():
    """Get list of files to exclude from formatting."""
    noformat_path = Path(".noformat")
    if not noformat_path.exists():
        return ["tests/test_notifications.py"]

    excluded = []
    with open(noformat_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                excluded.append(line)

    # Make sure test_notifications.py is in the list
    if "tests/test_notifications.py" not in excluded:
        excluded.append("tests/test_notifications.py")

    return excluded


def format_problem_files():
    """Format migrations and other commonly problematic files."""
    excluded = get_excluded_files()

    # Convert excluded files to command-line format
    exclude_pattern = "|".join(excluded) if excluded else None
    exclude_arg = f"--exclude={exclude_pattern}" if exclude_pattern else ""

    # Directories/files to target
    targets = [
        "app/__init__.py",
        "app/api/v1/cors.py",
        "app/api/v1/subscriptions.py",
        "app/cors_middleware.py",
        "app/api/meeting_requests.py",
        "app/api/geocoding.py",
        "debug_register.py",
        "deployment_fix/app",
        "development_config.py",
        "init_db.py",
        "migrations",
        "test_db.py",
        "tests/test_cors.py",
    ]

    print(f"Formatting specific problem files/directories...")
    for target in targets:
        if os.path.exists(target):
            print(f"  Formatting {target}")
            cmd = ["black"]
            if exclude_arg:
                cmd.append(exclude_arg)
            cmd.append(target)

            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error formatting {target}: {e}")

    print(f"All formatting complete!")


if __name__ == "__main__":
    format_problem_files()
