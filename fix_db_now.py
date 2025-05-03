#!/usr/bin/env python3
"""
Emergency fix for missing phone column in production.
This script directly adds the phone column to the database using SQLAlchemy.
"""

import logging
import os
import sys

from sqlalchemy import create_engine, inspect, text

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("emergency_fix")


def fix_phone_column():
    """Add the phone column to the users table."""
    try:
        # Try to import Flask app to get the database connection
        from app import create_app, db

        app = create_app()
        logger.info("Successfully created app instance")

        with app.app_context():
            # Get database connection
            logger.info("Getting database connection")
            connection = db.engine.connect()

            # Inspect the database
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Found tables: {tables}")

            if "users" not in tables:
                logger.error("Users table does not exist in the database!")
                return False

            # Check if phone column exists
            columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Found columns in users table: {columns}")

            if "phone" not in columns:
                logger.info("Phone column is missing - adding it now")

                # Execute the direct SQL to add the column
                with db.engine.begin() as conn:
                    # SQLite specific ALTER TABLE
                    if "sqlite" in str(db.engine.url).lower():
                        logger.info("Using SQLite syntax")
                        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                    # PostgreSQL syntax
                    else:
                        logger.info("Using PostgreSQL/MySQL syntax")
                        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))

                # Verify the column was added
                columns = [col["name"] for col in inspector.get_columns("users")]
                if "phone" in columns:
                    logger.info("Successfully added phone column!")
                    return True
                else:
                    logger.error("Failed to add phone column!")
                    return False
            else:
                logger.info("Phone column already exists - no action needed")
                return True

    except Exception as e:
        logger.error(f"Error fixing phone column: {str(e)}")
        logger.error("Attempting direct database connection...")

        try:
            # Try to get database URL from environment
            db_url = os.environ.get("DATABASE_URL")
            if not db_url:
                # Check if there's a database file in the instance directory
                if os.path.exists("instance/app.db"):
                    db_url = f"sqlite:///instance/app.db"
                elif os.path.exists("app/dev.db"):
                    db_url = f"sqlite:///app/dev.db"
                else:
                    logger.error("Could not find database URL or file")
                    return False

            logger.info(f"Using database URL: {db_url if 'sqlite' in db_url else '******'}")

            # Create direct engine connection
            engine = create_engine(db_url)
            inspector = inspect(engine)

            if "users" not in inspector.get_table_names():
                logger.error("Users table not found in direct connection!")
                return False

            columns = [col["name"] for col in inspector.get_columns("users")]
            if "phone" not in columns:
                logger.info("Adding phone column via direct connection")

                with engine.begin() as conn:
                    # SQLite specific ALTER TABLE
                    if "sqlite" in db_url.lower():
                        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                    # PostgreSQL/MySQL
                    else:
                        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))

                # Verify the column was added
                columns = [col["name"] for col in inspector.get_columns("users")]
                if "phone" in columns:
                    logger.info("Successfully added phone column via direct connection!")
                    return True
                else:
                    logger.error("Failed to add phone column via direct connection!")
                    return False
            else:
                logger.info("Phone column already exists (detected via direct connection)")
                return True

        except Exception as direct_error:
            logger.error(f"Error in direct database connection: {str(direct_error)}")
            return False


if __name__ == "__main__":
    logger.info("Starting emergency fix for missing phone column")

    if fix_phone_column():
        logger.info("=== FIX COMPLETED SUCCESSFULLY ===")
        logger.info("The phone column has been added to the users table.")
        logger.info("Please restart your application for the changes to take effect.")
        sys.exit(0)
    else:
        logger.error("=== FIX FAILED ===")
        logger.error("Please check the logs for details on why the fix failed.")
        logger.error("You may need to apply the direct SQL fix manually:")
        logger.error("  ALTER TABLE users ADD COLUMN phone VARCHAR(50);")
        logger.error("  CREATE INDEX ix_users_phone ON users (phone);")
        sys.exit(1)
