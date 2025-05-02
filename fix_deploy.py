#!/usr/bin/env python3

# Script to ensure middleware.py has the register_middleware function

import os

# Content to add if the function is missing
MIDDLEWARE_CONTENT = """
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

# Check if middleware.py exists
middleware_path = "app/middleware.py"
if not os.path.exists(middleware_path):
    # Create the file if it doesn't exist
    with open(middleware_path, "w") as f:
        f.write(
            """\"\"\"Middleware for ensuring required environment variables and configurations are set.\"\"\"

import os
import logging
from flask import Flask, request, current_app
"""
            + MIDDLEWARE_CONTENT
        )
    print(f"Created {middleware_path} with register_middleware function")
else:
    # Read the existing file
    with open(middleware_path, "r") as f:
        content = f.read()

    # Check if register_middleware function exists
    if "def register_middleware" not in content:
        # Append the function
        with open(middleware_path, "w") as f:
            if "DEFAULT_ENCRYPTION_KEY" not in content:
                # Add the whole content including the default key
                f.write(content + MIDDLEWARE_CONTENT)
            else:
                # Just add the register_middleware function
                f.write(
                    content
                    + """
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
                )
        print(f"Added register_middleware function to {middleware_path}")
    else:
        print(f"register_middleware function already exists in {middleware_path}")

print("Done!")
