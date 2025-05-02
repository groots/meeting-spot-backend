#!/bin/bash
# deploy_production_fix.sh
# Script to deploy fixes for the production environment to address
# both profile picture upload and meeting request 500 errors

set -e  # Exit on error

# Print colored output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting production fix deployment for meeting requests and profile picture issues${NC}"

# Check if we're in the backend directory
if [ ! -d "app" ]; then
    echo -e "${RED}Error: This script must be run from the backend directory${NC}"
    exit 1
fi

# Create backup directory
echo -e "${YELLOW}Creating backup of critical files...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup important files
if [ -f "app/middleware.py" ]; then
    cp app/middleware.py "$BACKUP_DIR/middleware.py.bak"
fi
cp app/__init__.py "$BACKUP_DIR/__init__.py.bak"

echo -e "${GREEN}Backups created in $BACKUP_DIR${NC}"

# Make production_fix.py executable and run it for diagnosis
echo -e "${YELLOW}Running diagnostic script...${NC}"
if [ ! -f "production_fix.py" ]; then
    echo -e "${RED}production_fix.py not found. Please ensure the script is in the backend directory.${NC}"
    exit 1
fi

chmod +x production_fix.py
./production_fix.py

# Check if the fix created a log file
if [ -f "production_fix.log" ]; then
    echo -e "${YELLOW}Log file created: production_fix.log${NC}"
    echo -e "${YELLOW}Last 10 lines of log:${NC}"
    tail -10 production_fix.log
fi

# Create profile_pictures directory if it doesn't exist
echo -e "${YELLOW}Ensuring profile_pictures directory exists...${NC}"
mkdir -p instance/profile_pictures
chmod 755 instance/profile_pictures

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
export FLASK_APP=wsgi.py
export FLASK_ENV=production
flask db upgrade

# Verify the middleware is correctly installed
echo -e "${YELLOW}Verifying middleware installation...${NC}"
if [ ! -f "app/middleware.py" ]; then
    echo -e "${RED}Middleware file still missing after fix. Creating it manually...${NC}"
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
    echo -e "${GREEN}Created middleware.py manually${NC}"
fi

# Check __init__.py for proper middleware registration
if ! grep -q "from .middleware import register_middleware" app/__init__.py; then
    echo -e "${RED}Middleware import not found in __init__.py. Adding it...${NC}"
    # Create a temporary file
    TEMP_FILE=$(mktemp)
    # Add the import after cors_middleware import
    awk '/from .cors_middleware import setup_cors/ {
        print $0
        print "\n# Import encryption key middleware\nfrom .middleware import register_middleware"
        next
    }
    { print $0 }' app/__init__.py > "$TEMP_FILE"
    mv "$TEMP_FILE" app/__init__.py
    echo -e "${GREEN}Added middleware import to __init__.py${NC}"
fi

if ! grep -q "register_middleware(app)" app/__init__.py; then
    echo -e "${RED}Middleware registration not found in __init__.py. Adding it...${NC}"
    # Create a temporary file
    TEMP_FILE=$(mktemp)
    # Add the registration after setup_cors(app)
    awk '/setup_cors\(app\)/ {
        print $0
        print "\n    # Register encryption key middleware\n    register_middleware(app)"
        next
    }
    { print $0 }' app/__init__.py > "$TEMP_FILE"
    mv "$TEMP_FILE" app/__init__.py
    echo -e "${GREEN}Added middleware registration to __init__.py${NC}"
fi

# Verify API routes - run a quick test to see if our routes are properly registered
echo -e "${YELLOW}Verifying API routes...${NC}"
python3 -c "
from app import create_app
app = create_app('production')
meeting_endpoint = False
profile_endpoint = False
for rule in app.url_map.iter_rules():
    if '/api/v1/meeting-requests/' in str(rule):
        meeting_endpoint = True
    if '/api/v1/auth/me/picture' in str(rule):
        profile_endpoint = True
if meeting_endpoint and profile_endpoint:
    print('${GREEN}✅ Both endpoints are properly registered${NC}')
else:
    print('${RED}❌ Endpoints not found: Meeting requests: ' + str(meeting_endpoint) + ', Profile picture: ' + str(profile_endpoint) + '${NC}')
"

# Final steps for deployment
echo -e "${YELLOW}Final deployment steps...${NC}"

# Restart the application server (adjust as needed for your environment)
if [ -f "/etc/systemd/system/findameetingspot.service" ]; then
    echo -e "${YELLOW}Restarting systemd service...${NC}"
    sudo systemctl restart findameetingspot.service
    echo -e "${GREEN}Service restarted${NC}"
elif [ -x "$(command -v docker)" ] && docker ps | grep -q "findameetingspot"; then
    echo -e "${YELLOW}Restarting Docker container...${NC}"
    docker restart $(docker ps | grep findameetingspot | awk '{print $1}')
    echo -e "${GREEN}Docker container restarted${NC}"
elif [ -x "$(command -v supervisorctl)" ]; then
    echo -e "${YELLOW}Restarting supervisor-managed service...${NC}"
    supervisorctl restart findameetingspot
    echo -e "${GREEN}Service restarted${NC}"
else
    echo -e "${YELLOW}No service manager detected. Please restart the application manually.${NC}"
fi

echo -e "${GREEN}Production fix deployment completed!${NC}"
echo -e "${YELLOW}Please verify that both profile picture uploads and meeting requests are working properly.${NC}"
echo -e "${YELLOW}If issues persist, check the log file at production_fix.log for more details.${NC}"
