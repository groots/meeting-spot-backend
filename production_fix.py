#!/usr/bin/env python3

"""
Production fix script for meeting spot backend.
This script ensures all necessary middleware is registered correctly.
"""

import os
import re
import sys

print("🔧 Production Fix Script for Meeting Spot Backend")

# 1. Update the middleware.py file to ensure it has the register_middleware function
middleware_path = "backend/app/middleware.py"
if not os.path.exists("backend"):
    print("Running in project root directory")
    middleware_path = "app/middleware.py"

print(f"📄 Checking {middleware_path}")

middleware_content = """
# Default encryption key to use if none is set in the environment
DEFAULT_ENCRYPTION_KEY = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"

def ensure_encryption_key(app: Flask) -> None:
    \"\"\"Ensure encryption key is set in app config.\"\"\"
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
        app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

def register_middleware(app: Flask) -> None:
    \"\"\"Register middleware with the Flask app.\"\"\"

    # Make sure encryption key is set
    ensure_encryption_key(app)

    # Register before_request handlers
    @app.before_request
    def check_encryption_key():
        \"\"\"Check if encryption key is properly set in the config.\"\"\"
        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
            current_app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

    # Log the encryption key status (don't log the actual key)
    if app.config.get("ENCRYPTION_KEY"):
        app.logger.info("ENCRYPTION_KEY is configured")
    else:
        app.logger.error("ENCRYPTION_KEY could not be set; this may cause issues with encrypted data")
"""

if os.path.exists(middleware_path):
    with open(middleware_path, "r") as f:
        content = f.read()

    if "def register_middleware" not in content:
        print("⚠️ register_middleware function missing, adding it...")
        # First, make sure imports are correct
        if "from flask import Flask, request, current_app" not in content:
            content = content.replace("from flask import Flask", "from flask import Flask, request, current_app")

        # Check if we need to add the DEFAULT_ENCRYPTION_KEY
        if "DEFAULT_ENCRYPTION_KEY" not in content:
            print("  ➕ Adding DEFAULT_ENCRYPTION_KEY")
            content += "\n# Default encryption key to use if none is set in the environment"
            content += '\nDEFAULT_ENCRYPTION_KEY = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"\n'

        # Check if we need to add ensure_encryption_key function
        if "def ensure_encryption_key" not in content:
            print("  ➕ Adding ensure_encryption_key function")
            content += """
def ensure_encryption_key(app: Flask) -> None:
    \"\"\"Ensure encryption key is set in app config.\"\"\"
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
        app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY
"""

        # Add register_middleware function
        print("  ➕ Adding register_middleware function")
        content += """
def register_middleware(app: Flask) -> None:
    \"\"\"Register middleware with the Flask app.\"\"\"

    # Make sure encryption key is set
    ensure_encryption_key(app)

    # Register before_request handlers
    @app.before_request
    def check_encryption_key():
        \"\"\"Check if encryption key is properly set in the config.\"\"\"
        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
            current_app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

    # Log the encryption key status (don't log the actual key)
    if app.config.get("ENCRYPTION_KEY"):
        app.logger.info("ENCRYPTION_KEY is configured")
    else:
        app.logger.error("ENCRYPTION_KEY could not be set; this may cause issues with encrypted data")
"""

        # Write updated content back to file
        with open(middleware_path, "w") as f:
            f.write(content)
        print("✅ Updated middleware.py with register_middleware function")
    else:
        print("✅ register_middleware function already exists")
else:
    print(f"❌ Cannot find {middleware_path}")

# 2. Update app/__init__.py to import and register the middleware
init_path = "backend/app/__init__.py"
if not os.path.exists("backend"):
    init_path = "app/__init__.py"

print(f"\n📄 Checking {init_path}")

if os.path.exists(init_path):
    with open(init_path, "r") as f:
        init_content = f.read()

    # Check for middleware import
    if "from .middleware import register_middleware" not in init_content:
        print("⚠️ Middleware import missing, adding it...")
        init_content = init_content.replace(
            "from .cors_middleware import setup_cors",
            "from .cors_middleware import setup_cors\n# Import encryption key middleware\nfrom .middleware import register_middleware",
        )
    else:
        print("✅ Middleware import exists")

    # The most critical part: Make sure the middleware is CORRECTLY registered in the create_app function
    if "register_middleware(app)" not in init_content:
        print("⚠️ Middleware registration missing, adding it...")
        # Find where setup_cors is called in create_app
        match = re.search(r"([ \t]*)setup_cors\(app\)", init_content)
        if match:
            indent = match.group(1)
            replacement = f"{indent}setup_cors(app)\n\n{indent}# Register encryption key middleware\n{indent}register_middleware(app)"
            init_content = init_content.replace(f"{indent}setup_cors(app)", replacement)
        else:
            # We need to manually check if we can find a better place to insert
            lines = init_content.split("\n")
            for i, line in enumerate(lines):
                if "def create_app" in line:
                    # Found the create_app function, now look for the app = Flask(__name__) line
                    for j in range(i, len(lines)):
                        if "app = Flask(__name__)" in lines[j]:
                            # Add registration after app creation
                            indent = lines[j].split("app")[0]
                            lines.insert(j + 2, f"{indent}# Register encryption key middleware")
                            lines.insert(j + 3, f"{indent}register_middleware(app)")
                            init_content = "\n".join(lines)
                            break
                    break
    else:
        print("✅ Middleware registration exists")

    # Write the updated content back to file
    with open(init_path, "w") as f:
        f.write(init_content)
    print("✅ Updated app/__init__.py to properly register middleware")
else:
    print(f"❌ Cannot find {init_path}")

print("\n🚀 Fix completed! Please restart the application for changes to take effect.")
