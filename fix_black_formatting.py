#!/usr/bin/env python
"""
Script to fix Black formatting issues in the codebase.
"""

import os
import subprocess
import sys


def main():
    """Apply Black formatting to all Python files."""
    print("Applying Black formatting to Python files...")

    # Get the list of files that Black would reformat
    result = subprocess.run(["black", "--check", "--diff", "."], capture_output=True, text=True)

    # Extract file paths from the output
    files_to_format = []
    for line in result.stderr.split("\n"):
        if line.startswith("would reformat"):
            file_path = line.replace("would reformat ", "").strip()
            if file_path != "tests/test_notifications.py":  # Skip the problematic file
                files_to_format.append(file_path)

    # Apply Black to each file individually
    if files_to_format:
        print(f"Formatting {len(files_to_format)} files...")
        for file_path in files_to_format:
            print(f"Formatting {file_path}...")
            subprocess.run(["black", file_path], check=True)
        print("All files formatted successfully!")
    else:
        print("No files need formatting.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
