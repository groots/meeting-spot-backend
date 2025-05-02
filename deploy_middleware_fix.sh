#!/bin/bash

# This script is designed to be run manually or as part of a GitHub Action workflow
# to fix the middleware.py file in the CI/CD pipeline

set -e  # Exit on any error

echo "🔧 Fixing middleware.py to include register_middleware function..."

# Create a temporary file with the correct middleware content
cat > middleware_fixed.py << 'EOF'
"""Middleware for ensuring required environment variables and configurations are set."""

import os
import logging
from flask import Flask, request, current_app

# Default encryption key to use if none is set in the environment
DEFAULT_ENCRYPTION_KEY = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"

def ensure_encryption_key(app: Flask) -> None:
    """Ensure encryption key is set in app config."""
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
        app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

def register_middleware(app: Flask) -> None:
    """Register middleware with the Flask app."""

    # Make sure encryption key is set
    ensure_encryption_key(app)

    # Register before_request handlers
    @app.before_request
    def check_encryption_key():
        """Check if encryption key is properly set in the config."""
        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
            current_app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

    # Log the encryption key status (don't log the actual key)
    if app.config.get("ENCRYPTION_KEY"):
        app.logger.info("ENCRYPTION_KEY is configured")
    else:
        app.logger.error("ENCRYPTION_KEY could not be set; this may cause issues with encrypted data")
EOF

# Replace the middleware.py file
cp middleware_fixed.py app/middleware.py

# Clean up
rm middleware_fixed.py

echo "✅ middleware.py fixed successfully"

# Create a special file for import fixes
cat > app/__init__.py_fix.py << 'EOF'
#!/usr/bin/env python3
import re

# Read the __init__.py file
with open("app/__init__.py", "r") as f:
    content = f.read()

# Check if the middleware import is missing
if "from .middleware import register_middleware" not in content:
    # Add the import after the CORS import
    content = re.sub(
        r"from \.cors_middleware import setup_cors\s*",
        "from .cors_middleware import setup_cors\n# Import encryption key middleware\nfrom .middleware import register_middleware\n",
        content
    )

# Check if the middleware registration is missing
if "register_middleware(app)" not in content:
    # Add the registration after the CORS setup
    content = re.sub(
        r"setup_cors\(app\)\s*",
        "setup_cors(app)\n\n    # Register encryption key middleware\n    register_middleware(app)\n",
        content
    )

# Write the changes back
with open("app/__init__.py", "w") as f:
    f.write(content)

print("✅ app/__init__.py fixed successfully")
EOF

# Run the __init__.py fixer
python app/__init__.py_fix.py
rm app/__init__.py_fix.py

echo "🚀 All middleware fixes applied successfully!"

# Commit and push the changes if running locally (not in CI)
if [ -z "$CI" ]; then
    git add app/middleware.py app/__init__.py
    git commit -m "Fix middleware for encryption key and properly export register_middleware"
    git push
    echo "✅ Changes committed and pushed to repository"
else
    echo "⏭️ Running in CI environment, skipping git commit and push"
fi
