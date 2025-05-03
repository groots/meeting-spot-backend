#!/usr/bin/env python3
"""
Comprehensive fix script for both profile picture uploads and meeting requests issues.
This script:
1. Ensures the encryption key middleware is properly registered
2. Creates the profile pictures directory
3. Makes sure the required database columns exist (phone, profile_picture_url)
"""

import logging
import os
import shutil
import sys

from sqlalchemy import inspect, text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("fix_script")


def ensure_profile_pictures_directory(app):
    """Create the profile pictures directory if it doesn't exist."""
    try:
        profile_pics_dir = os.path.join(app.instance_path, "profile_pictures")
        if not os.path.exists(profile_pics_dir):
            logger.info(f"Creating profile pictures directory: {profile_pics_dir}")
            os.makedirs(profile_pics_dir, exist_ok=True)
            # Set appropriate permissions
            os.chmod(profile_pics_dir, 0o755)
            logger.info("Profile pictures directory created successfully")
        else:
            logger.info("Profile pictures directory already exists")
        return True
    except Exception as e:
        logger.error(f"Failed to create profile pictures directory: {str(e)}")
        return False


def ensure_database_columns(app, db):
    """Ensure required database columns (phone, profile_picture_url) exist."""
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            if "users" not in inspector.get_table_names():
                logger.error("Users table does not exist!")
                return False

            columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Existing columns in users table: {columns}")

            missing_columns = []
            if "phone" not in columns:
                missing_columns.append(("phone", "VARCHAR(50)"))
            if "profile_picture_url" not in columns:
                missing_columns.append(("profile_picture_url", "VARCHAR(255)"))

            if missing_columns:
                logger.info(f"Missing columns to add: {missing_columns}")
                with db.engine.begin() as conn:
                    for column_name, column_type in missing_columns:
                        logger.info(f"Adding {column_name} column to users table")
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))

                        # Create index for phone column if needed
                        if column_name == "phone":
                            conn.execute(
                                text(f"CREATE INDEX IF NOT EXISTS ix_users_{column_name} ON users ({column_name})")
                            )

                # Verify the columns were added
                columns = [col["name"] for col in inspector.get_columns("users")]
                all_added = all(col[0] in columns for col in missing_columns)
                if all_added:
                    logger.info("Successfully added all missing columns!")
                    return True
                else:
                    logger.error("Failed to add some columns!")
                    return False
            else:
                logger.info("All required columns already exist!")
                return True
    except Exception as e:
        logger.error(f"Error ensuring database columns: {str(e)}")
        return False


def verify_middleware_registration():
    """Verify middleware is properly registered in __init__.py"""
    try:
        init_file_path = os.path.join(os.path.dirname(__file__), "app", "__init__.py")
        if not os.path.exists(init_file_path):
            logger.error(f"App initialization file not found at {init_file_path}")
            return False

        # Read the initialization file
        with open(init_file_path, "r") as f:
            init_content = f.read()

        # Check if middleware is imported
        if "from .middleware import register_middleware" not in init_content:
            logger.error("Middleware import not found in app/__init__.py")
            return False

        # Check if middleware is registered
        if "register_middleware(app)" not in init_content:
            logger.error("Middleware is not registered in app/__init__.py")
            return False

        logger.info("Middleware is properly imported and registered")
        return True
    except Exception as e:
        logger.error(f"Error verifying middleware registration: {str(e)}")
        return False


def verify_middleware_file():
    """Verify middleware.py file exists and contains necessary functions"""
    try:
        middleware_file_path = os.path.join(os.path.dirname(__file__), "app", "middleware.py")
        if not os.path.exists(middleware_file_path):
            logger.error(f"Middleware file not found at {middleware_file_path}")
            return False

        # Read the middleware file
        with open(middleware_file_path, "r") as f:
            middleware_content = f.read()

        # Check for essential functions
        if "ensure_encryption_key" not in middleware_content:
            logger.error("ensure_encryption_key function not found in middleware.py")
            return False

        if "register_middleware" not in middleware_content:
            logger.error("register_middleware function not found in middleware.py")
            return False

        logger.info("Middleware file contains all necessary functions")
        return True
    except Exception as e:
        logger.error(f"Error verifying middleware file: {str(e)}")
        return False


def fix_issues():
    """Main function to fix all issues."""
    success = True

    # Import Flask app and db
    try:
        from app import create_app, db

        app = create_app()

        # Step 1: Verify middleware file
        if not verify_middleware_file():
            logger.error("Middleware file verification failed")
            success = False

        # Step 2: Verify middleware registration
        if not verify_middleware_registration():
            logger.error("Middleware registration verification failed")
            success = False

        # Step 3: Create profile pictures directory
        if not ensure_profile_pictures_directory(app):
            logger.error("Failed to create profile pictures directory")
            success = False

        # Step 4: Ensure database columns exist
        if not ensure_database_columns(app, db):
            logger.error("Failed to ensure database columns")
            success = False

        return success
    except Exception as e:
        logger.error(f"Error in fix_issues: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("Starting comprehensive fix script")
    if fix_issues():
        logger.info("All issues fixed successfully")
        sys.exit(0)
    else:
        logger.error("Some issues could not be fixed")
        sys.exit(1)
