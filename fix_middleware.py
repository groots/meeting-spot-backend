#!/usr/bin/env python3

# Script to add middleware import and registration to app/__init__.py

with open("app/__init__.py", "r") as f:
    lines = f.readlines()

# Add import if needed
import_added = False
for i, line in enumerate(lines):
    if "from .cors_middleware import setup_cors" in line:
        # Check if middleware import is already there
        if i + 1 < len(lines) and "from .middleware import register_middleware" not in lines[i + 1]:
            lines.insert(i + 1, "# Import encryption key middleware\n")
            lines.insert(i + 2, "from .middleware import register_middleware\n")
            import_added = True
        break

# Add registration if needed
registration_added = False
for i, line in enumerate(lines):
    if "setup_cors(app)" in line:
        # Check if middleware registration is already there
        if i + 1 < len(lines) and "register_middleware(app)" not in lines[i + 1]:
            lines.insert(i + 1, "\n    # Register encryption key middleware\n")
            lines.insert(i + 2, "    register_middleware(app)\n")
            registration_added = True
        break

# Write changes back
with open("app/__init__.py", "w") as f:
    f.writelines(lines)

print(f"Import added: {import_added}, Registration added: {registration_added}")
