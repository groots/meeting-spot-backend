#!/bin/bash
# deploy_fixes.sh
# This script deploys fixes for the profile picture upload and meeting requests issues

set -e  # Exit on any error

# Log file setup
LOGFILE="deployment_fixes.log"
# Clear log file
> $LOGFILE

# Timestamp function
timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

# Log function
log() {
  echo "$(timestamp) - $1" | tee -a $LOGFILE
}

# Error handling function
handle_error() {
  log "ERROR: $1"
  log "Deployment failed. Check the log file for details."
  exit 1
}

# Function to back up important files
backup_files() {
  log "Backing up important files..."

  # Create backup directory with timestamp
  BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
  mkdir -p $BACKUP_DIR

  # Backup app initialization file
  if [ -f "app/__init__.py" ]; then
    cp app/__init__.py "$BACKUP_DIR/init.py.bak"
    log "Backed up app/__init__.py"
  fi

  # Backup users model
  if [ -f "app/models/user.py" ]; then
    cp app/models/user.py "$BACKUP_DIR/user.py.bak"
    log "Backed up app/models/user.py"
  fi

  # Backup database
  if [ -f "app/dev.db" ]; then
    cp app/dev.db "$BACKUP_DIR/dev.db.bak"
    log "Backed up app/dev.db"
  fi

  # Copy current fixes script
  if [ -f "fix_both_issues.py" ]; then
    cp fix_both_issues.py "$BACKUP_DIR/fix_both_issues.py.bak"
    log "Backed up fix_both_issues.py"
  fi

  log "Backup completed in directory: $BACKUP_DIR"
}

# Function to verify app environment
verify_environment() {
  log "Verifying application environment..."

  # Check if app directory exists
  if [ ! -d "app" ]; then
    handle_error "app directory not found. Please run this script from the backend directory."
  fi

  # Check if migrations directory exists
  if [ ! -d "migrations" ]; then
    handle_error "migrations directory not found. Please run this script from the backend directory."
  fi

  # Check if required files exist
  if [ ! -f "app/__init__.py" ]; then
    handle_error "app/__init__.py not found. Cannot continue."
  fi

  # Check if SQLAlchemy is installed
  if ! python -c "import sqlalchemy" &> /dev/null; then
    log "SQLAlchemy not found. Installing required packages..."
    pip install -r requirements.txt || handle_error "Failed to install requirements"
  fi

  log "Environment verification completed"
}

# Function to check if middleware.py exists and create if needed
ensure_middleware_file() {
  log "Checking middleware.py file..."

  if [ ! -f "app/middleware.py" ]; then
    log "Creating app/middleware.py file"
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
    log "Created middleware.py file"
  else
    log "middleware.py already exists"
  fi
}

# Function to check middleware registration in __init__.py
ensure_middleware_registration() {
  log "Checking middleware registration in __init__.py..."

  # Check if middleware import is present
  if ! grep -q "from .middleware import register_middleware" app/__init__.py; then
    log "Adding middleware import to app/__init__.py"
    sed -i.bak '1,10s/from flask import Flask.*/&\n# Import encryption key middleware\nfrom .middleware import register_middleware/' app/__init__.py
  else
    log "Middleware import already exists in app/__init__.py"
  fi

  # Check if middleware registration is present
  if ! grep -q "register_middleware(app)" app/__init__.py; then
    log "Adding middleware registration to app/__init__.py"
    # Look for setup_cors(app) line and add register_middleware after it
    sed -i.bak '/setup_cors(app)/a\    # Register encryption key middleware\n    register_middleware(app)' app/__init__.py
  else
    log "Middleware registration already exists in app/__init__.py"
  fi
}

# Function to create profile pictures directory
ensure_profile_pictures_directory() {
  log "Ensuring profile pictures directory exists..."

  # Create instance directory if it doesn't exist
  if [ ! -d "instance" ]; then
    mkdir -p instance
    log "Created instance directory"
  fi

  # Create profile_pictures directory if it doesn't exist
  if [ ! -d "instance/profile_pictures" ]; then
    mkdir -p instance/profile_pictures
    chmod 755 instance/profile_pictures
    log "Created instance/profile_pictures directory with permissions 755"
  else
    log "instance/profile_pictures directory already exists"
  fi
}

# Function to apply database fixes
apply_database_fixes() {
  log "Applying database fixes..."

  # Run the comprehensive fix script
  log "Running fix_both_issues.py..."
  python fix_both_issues.py || handle_error "Fix script failed"

  # Additionally, run the direct phone column fix as a backup
  log "Running direct_phone_column_fix.py as a backup..."
  python direct_phone_column_fix.py || log "Warning: Direct phone column fix failed, but continuing..."

  log "Database fixes applied"
}

# Function to verify fixes
verify_fixes() {
  log "Verifying fixes..."

  # Verify middleware registration
  if ! grep -q "register_middleware(app)" app/__init__.py; then
    handle_error "Middleware registration not found in app/__init__.py after fixes"
  fi

  # Verify profile pictures directory
  if [ ! -d "instance/profile_pictures" ]; then
    handle_error "Profile pictures directory not created successfully"
  fi

  # Check if python is available for database verification
  if command -v python &> /dev/null; then
    # Verify database columns using Python
    python -c '
import sys
from app import create_app, db
from sqlalchemy import inspect

try:
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if "users" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "phone" not in columns or "profile_picture_url" not in columns:
                print("ERROR: Required columns not found in users table")
                sys.exit(1)
            else:
                print("Database columns verified successfully")
                sys.exit(0)
        else:
            print("ERROR: users table not found")
            sys.exit(1)
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
' || handle_error "Database column verification failed"
  else
    log "Warning: Python not available, skipping database column verification"
  fi

  log "All fixes verified successfully"
}

# Main deployment function
deploy_fixes() {
  log "Starting deployment of fixes for profile picture and meeting requests issues"

  # Step 1: Verify environment
  verify_environment

  # Step 2: Backup important files
  backup_files

  # Step 3: Ensure middleware file exists
  ensure_middleware_file

  # Step 4: Ensure middleware is registered in __init__.py
  ensure_middleware_registration

  # Step 5: Create profile pictures directory
  ensure_profile_pictures_directory

  # Step 6: Apply database fixes
  apply_database_fixes

  # Step 7: Verify fixes
  verify_fixes

  log "Deployment completed successfully"
  log "If the application is running, please restart it for the changes to take effect"
}

# Run the deployment
deploy_fixes
