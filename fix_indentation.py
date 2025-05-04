#!/usr/bin/env python3
"""
Fix indentation issues in auth.py file.
"""

import re
import sys


def fix_indentation_in_file(file_path):
    """Fix indentation issues in the given file."""
    print(f"Fixing indentation in {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Fix indentation in register function
    content = re.sub(
        r'@auth_bp\.route\("/register", methods=\["POST"\]\)\s*\ndef register\(\):\s*"""Register a new user\."""\s*\s+data = request\.get_json\(\)',
        '@auth_bp.route("/register", methods=["POST"])\ndef register():\n    """Register a new user."""\n    data = request.get_json()',
        content,
    )

    # Fix other indentation issues in register function
    content = re.sub(
        r"    # Check if user already exists\s+existing_user",
        "    # Check if user already exists\n    existing_user",
        content,
    )

    content = re.sub(r"    # Create new user\s+new_user", "    # Create new user\n    new_user", content)

    content = re.sub(r"        db\.session\.commit\(\)", "        db.session.commit()", content)

    # Fix indentation issues in login function
    content = re.sub(r"        except Exception as e:", "    except Exception as e:", content)

    content = re.sub(
        r'        current_app\.logger\.error\(f"Unhandled exception in login endpoint: {str\(e\)}"\)',
        '        current_app.logger.error(f"Unhandled exception in login endpoint: {str(e)}")',
        content,
    )

    # Fix indentation in upload_profile_picture function
    content = re.sub(
        r"    user = User\.query\.get\(current_user_id\)\s+if not user:",
        "    user = User.query.get(current_user_id)\n    if not user:",
        content,
    )

    content = re.sub(r"                else:", "            else:", content)

    # Write the fixed content back
    with open(file_path, "w") as f:
        f.write(content)

    print(f"Indentation fixed in {file_path}")


if __name__ == "__main__":
    try:
        auth_file = "app/api/auth.py"
        fix_indentation_in_file(auth_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
