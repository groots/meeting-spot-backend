#!/bin/bash
# deploy_fixes.sh
# Script to deploy fixes for profile picture upload and meeting request encryption issues

set -e  # Exit on error

# Print colored output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of fixes for profile picture upload and meeting request encryption issues${NC}"

# Check if we're in the backend directory
if [ ! -d "app" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory${NC}"
    exit 1
fi

# Backup current app configuration
echo -e "${YELLOW}Backing up current configuration...${NC}"
mkdir -p backup
cp -r app/middleware.py backup/middleware.py.bak || true
cp -r app/__init__.py backup/__init__.py.bak || true

# Verify middleware.py exists and has the necessary content
echo -e "${YELLOW}Verifying middleware.py...${NC}"
if [ ! -f "app/middleware.py" ]; then
    echo -e "${RED}app/middleware.py doesn't exist. Creating it...${NC}"
    cat > app/middleware.py << 'EOL'
"""Middleware for ensuring required environment variables and configurations are set."""

import logging
import os

from flask import Flask, current_app, request

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
EOL
    echo -e "${GREEN}Created app/middleware.py${NC}"
fi

# Verify middleware is registered in __init__.py
echo -e "${YELLOW}Verifying middleware registration in __init__.py...${NC}"
if ! grep -q "from .middleware import register_middleware" app/__init__.py; then
    echo -e "${RED}Middleware import not found in __init__.py. Please add it manually.${NC}"
    echo -e "${YELLOW}Add this line after other imports: from .middleware import register_middleware${NC}"
    exit 1
fi

if ! grep -q "register_middleware(app)" app/__init__.py; then
    echo -e "${RED}Middleware registration not found in __init__.py. Please add it manually.${NC}"
    echo -e "${YELLOW}Add this line before initializing other extensions: register_middleware(app)${NC}"
    exit 1
fi

# Create directory for profile pictures
echo -e "${YELLOW}Creating profile pictures directory...${NC}"
mkdir -p instance/profile_pictures
chmod 755 instance/profile_pictures

# Check and run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
if command -v flask &> /dev/null; then
    export FLASK_APP=wsgi.py
    flask db upgrade
else
    echo -e "${RED}Flask command not found. Make sure it's installed and in your PATH.${NC}"
    echo -e "${YELLOW}Trying with Python directly...${NC}"
    python -c "from app import create_app, db; app = create_app(); app.app_context().push(); from flask_migrate import upgrade; upgrade()"
fi

# Make the fix script executable and run it
echo -e "${YELLOW}Running the fix script...${NC}"
if [ -f "fix_both_issues.py" ]; then
    chmod +x fix_both_issues.py
    ./fix_both_issues.py
else
    echo -e "${RED}fix_both_issues.py not found. Please run the script manually.${NC}"
fi

# Run tests to verify fixes
echo -e "${YELLOW}Running tests to verify fixes...${NC}"
if [ -f "run_tests.sh" ]; then
    ./run_tests.sh
else
    echo -e "${YELLOW}No test script found. Skipping tests.${NC}"
fi

echo -e "${GREEN}Deployment of fixes completed!${NC}"
echo -e "${YELLOW}Please verify that both profile picture uploads and meeting requests are working properly.${NC}"
