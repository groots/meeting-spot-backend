#!/usr/bin/env python3
"""
Direct phone column fix script.
This script directly adds the phone column to the users table.
"""

import logging
import os
import sys

from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("direct_fix")


def apply_direct_fix():
    """Apply the direct fix to add the phone column to the users table."""
    try:
        # Get database URL from environment
        # Try the environment variable first
        db_url = os.environ.get("DATABASE_URL")

        # If not set, try to get it from the Flask app
        if not db_url:
            try:
                from app import create_app

                app = create_app("production")  # Use production config
                with app.app_context():
                    db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                    logger.info(f"Got database URL from app config")
            except Exception as e:
                logger.error(f"Failed to get database URL from app config: {str(e)}")
                return False

        if not db_url:
            logger.error("No database URL found")
            return False

        logger.info(f"Using database URL: {db_url.split('@')[1] if '@' in db_url else '*****'}")

        # Create SQLAlchemy engine
        engine = create_engine(db_url)

        # Add phone column if it doesn't exist
        with engine.begin() as conn:
            # Check if column exists
            if "sqlite" in db_url.lower():
                # SQLite syntax
                result = conn.execute(
                    text(
                        """
                    SELECT count(*) FROM pragma_table_info('users')
                    WHERE name = 'phone'
                """
                    )
                ).scalar()

                if result == 0:
                    logger.info("Adding phone column to users table (SQLite)")
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                    # SQLite doesn't support ADD INDEX in ALTER TABLE
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                    logger.info("Successfully added phone column to users table")
                else:
                    logger.info("phone column already exists in users table")
            else:
                # PostgreSQL/MySQL syntax
                try:
                    # Try PostgreSQL syntax first
                    result = conn.execute(
                        text(
                            """
                        SELECT column_name FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name = 'phone'
                    """
                        )
                    ).fetchall()

                    if not result:
                        logger.info("Adding phone column to users table (PostgreSQL)")
                        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                        logger.info("Successfully added phone column to users table")
                    else:
                        logger.info("phone column already exists in users table")
                except Exception as e:
                    logger.error(f"Error using PostgreSQL syntax: {str(e)}")
                    logger.info("Trying MySQL syntax...")

                    # Try MySQL syntax
                    result = conn.execute(
                        text(
                            """
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_name = 'users' AND column_name = 'phone'
                    """
                        )
                    ).scalar()

                    if result == 0:
                        logger.info("Adding phone column to users table (MySQL)")
                        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX ix_users_phone ON users (phone)"))
                        logger.info("Successfully added phone column to users table")
                    else:
                        logger.info("phone column already exists in users table")

        return True
    except Exception as e:
        logger.error(f"Failed to apply direct fix: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("Starting direct phone column fix")
    if apply_direct_fix():
        logger.info("Direct fix completed successfully")
        sys.exit(0)
    else:
        logger.error("Direct fix failed")
        sys.exit(1)
