#!/usr/bin/env python3
"""
Emergency fix for missing phone column in production.
"""

import logging
import os
import sys
import traceback

from sqlalchemy import create_engine, inspect, text

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("emergency_fix")


def fix_phone_column():
    """Add the phone column to the users table."""
    try:
        # Get database file paths
        possible_db_files = ["instance/app.db", "app/dev.db", "../app/dev.db", "dev.db"]

        db_url = None
        for db_file in possible_db_files:
            if os.path.exists(db_file):
                db_url = f"sqlite:///{db_file}"
                logger.info(f"Found database at {db_file}")
                break

        if not db_url:
            # Try environment variable as fallback
            db_url = os.environ.get("DATABASE_URL")
            if db_url:
                logger.info("Using DATABASE_URL from environment")
            else:
                logger.error("Could not find database file or DATABASE_URL")
                return False

        logger.info(f"Using database URL: {db_url}")

        # Create direct engine connection
        engine = create_engine(db_url)
        inspector = inspect(engine)

        tables = inspector.get_table_names()
        logger.info(f"Found tables: {tables}")

        if "users" not in tables:
            logger.error("Users table not found!")
            return False

        columns = [col["name"] for col in inspector.get_columns("users")]
        logger.info(f"Found columns in users table: {columns}")

        if "phone" not in columns:
            logger.info("Adding phone column via direct SQL")

            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                    logger.info("Column added successfully")

                    # Try to create index, but don't fail if it doesn't work
                    try:
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                        logger.info("Index created successfully")
                    except Exception as index_error:
                        logger.warning(f"Could not create index, but continuing: {str(index_error)}")
            except Exception as sql_error:
                logger.error(f"SQL error: {str(sql_error)}")
                logger.error(traceback.format_exc())
                return False

            # Verify the column was added
            try:
                # Re-inspect the database
                inspector = inspect(engine)
                columns = [col["name"] for col in inspector.get_columns("users")]
                logger.info(f"Updated columns in users table: {columns}")

                if "phone" in columns:
                    logger.info("Phone column is now present!")
                    return True
                else:
                    logger.error("Phone column still missing after SQL execution!")
                    return False
            except Exception as verify_error:
                logger.error(f"Error verifying column: {str(verify_error)}")
                # Even if verification fails, try to insert a test row to confirm
                try:
                    with engine.begin() as conn:
                        # Try to select a row with the phone column
                        result = conn.execute(text("SELECT phone FROM users LIMIT 1"))
                        logger.info("Phone column exists and is accessible!")
                        return True
                except Exception as test_error:
                    logger.error(f"Phone column test failed: {str(test_error)}")
                    return False
        else:
            logger.info("Phone column already exists")
            return True

    except Exception as e:
        logger.error(f"Error in direct database connection: {str(e)}")
        logger.error(traceback.format_exc())
        return False


# Function to try direct SQL if all else fails
def apply_direct_sql():
    """Try direct SQL application as a last resort."""
    logger.info("Attempting direct SQL as a last resort")

    try:
        # Find the database file
        possible_db_files = ["instance/app.db", "app/dev.db", "../app/dev.db", "dev.db"]

        db_file = None
        for path in possible_db_files:
            if os.path.exists(path):
                db_file = path
                break

        if not db_file:
            logger.error("No database file found for direct SQL")
            return False

        logger.info(f"Found database at {db_file}")

        # Try using sqlite3 command line
        import sqlite3

        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if "phone" not in columns:
            logger.info("Adding phone column via sqlite3")
            cursor.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(50)")
            conn.commit()

            # Try to create index
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)")
                conn.commit()
            except:
                logger.warning("Could not create index, but continuing")

            # Verify the column exists
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]

            if "phone" in columns:
                logger.info("Successfully added phone column via sqlite3!")
                conn.close()
                return True
            else:
                logger.error("Failed to add phone column via sqlite3")
                conn.close()
                return False
        else:
            logger.info("Phone column already exists (via sqlite3 check)")
            conn.close()
            return True

    except Exception as e:
        logger.error(f"Error in direct SQL: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting emergency fix for missing phone column")

    # Try the SQLAlchemy method first
    success = fix_phone_column()

    # If that fails, try direct SQL
    if not success:
        logger.warning("SQLAlchemy method failed, trying direct SQL")
        success = apply_direct_sql()

    if success:
        logger.info("=== FIX COMPLETED SUCCESSFULLY ===")
        logger.info("The phone column has been added to the users table.")
        logger.info("Please restart your application for the changes to take effect.")
        sys.exit(0)
    else:
        logger.error("=== FIX FAILED ===")
        logger.error("Please check the logs for details on why the fix failed.")
        logger.error("You may need to apply the direct SQL fix manually:")
        logger.error("  sqlite3 app/dev.db")
        logger.error("  ALTER TABLE users ADD COLUMN phone VARCHAR(50);")
        logger.error("  CREATE INDEX ix_users_phone ON users (phone);")
        logger.error("  .exit")
        sys.exit(1)
