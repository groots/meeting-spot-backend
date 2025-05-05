#!/usr/bin/env python3
"""
Fix login issues by adding necessary columns to the database.

This script directly connects to the database to add any missing columns
needed by the User model and authentication system.
"""

import logging
import os
import sqlite3
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("login_fix")


def find_database_path():
    """Find the SQLite database file path."""
    # Common paths where the database might be stored
    possible_paths = [
        "instance/development.db",
        "instance/dev.db",
        "app/dev.db",
        "app/test.db",
        "instance/app.db",
        "instance/app.sqlite",
        "instance/app.sqlite3",
        "app.db",
        "app.sqlite",
        "app.sqlite3",
        "development.db",
        "test.db",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Found database at {path}")
            return path

    # Try to load from configuration
    try:
        from app import create_app

        app = create_app("development")
        with app.app_context():
            db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            if db_url.startswith("sqlite:///"):
                db_path = db_url[10:]  # Remove sqlite:///
                if os.path.exists(db_path):
                    logger.info(f"Found database at {db_path} from config")
                    return db_path
    except Exception as e:
        logger.warning(f"Could not load database path from config: {str(e)}")

    logger.error("Could not find database file")
    return None


def add_missing_columns(db_path):
    """Add missing columns to the users table."""
    if not db_path:
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current columns in the users table
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        logger.info(f"Existing columns: {', '.join(sorted(existing_columns))}")

        # Columns to add with their SQLite data types
        columns_to_add = {
            "username": "VARCHAR(50)",
            "first_name": "VARCHAR(50)",
            "last_name": "VARCHAR(50)",
            "phone": "VARCHAR(50)",
            "profile_picture_url": "VARCHAR(255)",
            "facebook_oauth_id": "VARCHAR(255)",
        }

        # Add missing columns
        for column, data_type in columns_to_add.items():
            if column not in existing_columns:
                try:
                    logger.info(f"Adding {column} column")
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {data_type}")
                    conn.commit()
                    logger.info(f"✅ Added {column} column")
                except sqlite3.OperationalError as e:
                    # Some SQLite versions don't support adding constraints in ALTER TABLE
                    logger.error(f"❌ Failed to add {column}: {str(e)}")

        # If username column was added, populate it with email prefix
        if "username" in columns_to_add and "username" not in existing_columns:
            try:
                logger.info("Populating username column from email")
                cursor.execute("SELECT id, email FROM users")
                users = cursor.fetchall()

                for user_id, email in users:
                    username = email.split("@")[0]
                    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (username, user_id))

                conn.commit()
                logger.info(f"✅ Populated usernames for {len(users)} users")
            except Exception as e:
                logger.error(f"❌ Failed to populate usernames: {str(e)}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"❌ Database error: {str(e)}")
        return False


def create_patch_for_app_init():
    """Create a patch in app/__init__.py to make it more resilient to missing columns."""
    try:
        # File path to patch
        file_path = "app/__init__.py"

        if not os.path.exists(file_path):
            logger.warning(f"❌ {file_path} not found, skipping patch")
            return False

        # Read current file content
        with open(file_path, "r") as f:
            content = f.read()

        # Only patch if not already patched
        if "init_models(app, db)" not in content:
            logger.info(f"Adding model initialization patch to {file_path}")

            # Find the line after database initialization
            db_init_line = "db.init_app(app)"
            jwt_init_line = "jwt.init_app(app)"
            migrate_init_line = "migrate.init_app(app, db)"

            if migrate_init_line in content:
                # Insert after migrate initialization
                content = content.replace(
                    migrate_init_line,
                    migrate_init_line
                    + '\n\n    # Initialize models based on database schema\n    try:\n        # Import here to avoid circular imports\n        from .models import init_models\n        init_models(app, db)\n    except Exception as e:\n        app.logger.error(f"Error initializing models: {str(e)}")',
                )

                # Write back the patched file
                with open(file_path, "w") as f:
                    f.write(content)

                logger.info(f"✅ Applied patch to {file_path}")
                return True
            else:
                logger.warning(f"❌ Could not find insertion point in {file_path}")
                return False
        else:
            logger.info(f"✅ {file_path} already patched")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to patch app/__init__.py: {str(e)}")
        return False


def fix_login_issues():
    """Fix login issues by applying all necessary fixes."""
    logger.info("Starting login fix process")

    # Find database
    db_path = find_database_path()
    if not db_path:
        logger.error("❌ Cannot proceed without database path")
        return False

    # Add missing columns
    if not add_missing_columns(db_path):
        logger.error("❌ Failed to add missing columns")
        return False

    # Create patch for app/__init__.py
    create_patch_for_app_init()

    logger.info("✅ Login fix process completed")
    return True


if __name__ == "__main__":
    if fix_login_issues():
        logger.info("✅ Successfully fixed login issues")
        sys.exit(0)
    else:
        logger.error("❌ Failed to fix login issues")
        sys.exit(1)
