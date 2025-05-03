#!/usr/bin/env python
"""
Script to fix API paths in test files.
"""

import os
import re
from pathlib import Path


def fix_test_file(file_path):
    """Fix API paths in a test file."""
    with open(file_path, "r") as f:
        content = f.read()

    # Fix paths by removing the namespace prefixes that were added by Flask-RestX

    # Restore original paths for contacts API
    content = re.sub(r'"/api/v1/contacts/contacts(.*?)"', r'"/api/v1/contacts\1"', content)

    # Restore original paths for payments API
    content = re.sub(r'"/api/v1/payments/payments(.*?)"', r'"/api/v1/payments\1"', content)

    # Restore original paths for geocoding API
    content = re.sub(r'"/api/v1/geocoding/geocoding(.*?)"', r'"/api/v1/geocoding\1"', content)

    # Restore original paths for users API
    content = re.sub(r'"/api/v1/users/users(.*?)"', r'"/api/v1/users\1"', content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"Fixed {file_path}")


def main():
    """Main function."""
    # Find all test files in the tests directory
    tests_dir = Path("tests")
    test_files = list(tests_dir.glob("**/*.py"))

    for test_file in test_files:
        if test_file.name.startswith("test_"):
            fix_test_file(test_file)


if __name__ == "__main__":
    main()
