#!/usr/bin/env python3
"""
Script to automatically fix common linting issues.
"""
import os
import re


def fix_unused_typing_imports(file_path):
    """Remove unused typing imports."""
    with open(file_path, "r") as f:
        content = f.read()

    # Remove unused typing imports
    pattern = (
        r"from typing import (?:Any, |Dict, |List, |Optional, |Union, )*?"
        r"(?:Any|Dict|List|Optional|Union)(?:, (?:Any|Dict|List|Optional|Union))*?\n"
    )
    content = re.sub(pattern, "", content)

    # Remove empty typing imports
    content = re.sub(r"from typing import\n", "", content)

    with open(file_path, "w") as f:
        f.write(content)


def fix_unused_os_imports(file_path):
    """Remove unused os imports."""
    with open(file_path, "r") as f:
        content = f.read()

    # Check if os is used in the file
    if "os." not in content and "os.path" not in content and "os.environ" not in content:
        content = re.sub(r"import os\n", "", content)

    with open(file_path, "w") as f:
        f.write(content)


def fix_long_lines(file_path):
    """Fix lines that are too long."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        if len(line) > 100 and not line.startswith("#"):
            # Split long string literals
            if '"' in line and line.count('"') % 2 == 0:
                parts = line.split('"')
                for i in range(1, len(parts), 2):
                    if len(parts[i]) > 80:
                        parts[i] = parts[i][:80] + '" +\n        "' + parts[i][80:]
                line = '"'.join(parts)
            elif "'" in line and line.count("'") % 2 == 0:
                parts = line.split("'")
                for i in range(1, len(parts), 2):
                    if len(parts[i]) > 80:
                        parts[i] = parts[i][:80] + "' +\n        '" + parts[i][80:]
                line = "'".join(parts)

        fixed_lines.append(line)

    with open(file_path, "w") as f:
        f.writelines(fixed_lines)


def fix_meeting_request_dict_any(file_path):
    """Fix Dict and Any in meeting_request.py."""
    if "meeting_request.py" in file_path:
        with open(file_path, "r") as f:
            content = f.read()

        # Add Dict and Any imports if they're used
        if "Dict" in content and "from typing import Dict" not in content:
            content = re.sub(
                r"from typing import (.*?)\n",
                r"from typing import \1, Dict\n",
                content,
            )

        if "Any" in content and "from typing import Any" not in content:
            content = re.sub(
                r"from typing import (.*?)\n",
                r"from typing import \1, Any\n",
                content,
            )

        with open(file_path, "w") as f:
            f.write(content)


def main():
    """Main function to fix linting issues."""
    # Get all Python files
    python_files = []
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    # Fix each file
    for file_path in python_files:
        fix_unused_typing_imports(file_path)
        fix_unused_os_imports(file_path)
        fix_long_lines(file_path)
        fix_meeting_request_dict_any(file_path)


if __name__ == "__main__":
    main()
