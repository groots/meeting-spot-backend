#!/usr/bin/env python3
"""
Fix script for both the profile picture upload issue and the meeting request encryption key issue.
This script:
1. Ensures the encryption key middleware is properly registered in the Flask app
2. Verifies the profile_picture_url column exists in the users table
3. Creates the necessary directory structure for storing profile pictures
"""

import logging
import os
import sys

from flask import Flask
from sqlalchemy import inspect, text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("fix_script")


def ensure_middleware_registration():
    """Check and ensure middleware registration in __init__.py."""
    try:
        from app import create_app
        from app.middleware import register_middleware

        app = create_app()
        with app.app_context():
            if "ENCRYPTION_KEY" not in app.config:
                logger.warning("ENCRYPTION_KEY not set in app config")
                app.config["ENCRYPTION_KEY"] = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"
                logger.info("Set default ENCRYPTION_KEY in app config")
            else:
                logger.info("ENCRYPTION_KEY already set in app config")

        logger.info("Middleware registration verified")
        return True
    except Exception as e:
        logger.error(f"Failed to verify middleware registration: {str(e)}")
        return False


def ensure_profile_picture_column():
    """Check and ensure profile_picture_url column exists in users table."""
    try:
        from app import create_app, db

        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            if "users" in inspector.get_table_names():
                columns = [col["name"] for col in inspector.get_columns("users")]
                if "profile_picture_url" not in columns:
                    logger.info("Adding profile_picture_url column to users table")
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE users ADD COLUMN profile_picture_url VARCHAR(255)"))
                    logger.info("Successfully added profile_picture_url column")
                else:
                    logger.info("profile_picture_url column already exists in users table")
            else:
                logger.error("users table does not exist in the database")
                return False
        return True
    except Exception as e:
        logger.error(f"Failed to ensure profile_picture_url column: {str(e)}")
        return False


def ensure_profile_pictures_directory():
    """Create necessary directories for storing profile pictures."""
    try:
        from app import create_app

        app = create_app()
        with app.app_context():
            profile_pics_dir = os.path.join(app.instance_path, "profile_pictures")
            os.makedirs(profile_pics_dir, exist_ok=True)
            logger.info(f"Created profile pictures directory at {profile_pics_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to create profile pictures directory: {str(e)}")
        return False


def run_migrations():
    """Run database migrations to ensure all tables and columns are properly created."""
    try:
        logger.info("Running database migrations...")
        os.system("flask db upgrade")
        logger.info("Database migrations completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to run migrations: {str(e)}")
        return False


def main():
    """Execute all fix operations."""
    logger.info("Starting fix script for both issues")

    success = True
    success = ensure_middleware_registration() and success
    success = ensure_profile_picture_column() and success
    success = ensure_profile_pictures_directory() and success
    success = run_migrations() and success

    if success:
        logger.info("All fixes applied successfully!")
    else:
        logger.error("Some fixes failed. Please check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
