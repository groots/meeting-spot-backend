#!/usr/bin/env python3
"""
Add username column to users table.

This script adds the missing username column to the users table and
populates it with the first part of the email address for existing users.
"""

import logging
import sys

from flask import Flask
from sqlalchemy import Boolean, Column, String, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("username_migration")


def add_username_column():
    """Add username column to users table."""
    try:
        from app import create_app, db

        app = create_app("development")

        with app.app_context():
            inspector = inspect(db.engine)
            existing_columns = {column["name"] for column in inspector.get_columns("users")}

            logger.info(f"Existing columns in 'users' table: {', '.join(sorted(existing_columns))}")

            # Check if username column already exists
            if "username" in existing_columns:
                logger.info("✅ Username column already exists")
                return True

            # Add username column - for SQLite, we can't add a UNIQUE constraint directly
            try:
                logger.info("Adding username column to users table")
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50)"))
                logger.info("✅ Added username column")

                # Generate usernames from email for existing users
                logger.info("Generating usernames for existing users")
                users = db.session.execute(text("SELECT id, email FROM users")).fetchall()

                for user in users:
                    # Extract username from email (part before @)
                    email_parts = user.email.split("@")
                    username = email_parts[0]

                    # Update the user
                    db.session.execute(
                        text("UPDATE users SET username = :username WHERE id = :id"),
                        {"username": username, "id": user.id},
                    )

                db.session.commit()
                logger.info(f"✅ Generated usernames for {len(users)} users")

                return True

            except OperationalError as e:
                logger.error(f"❌ Database error adding username column: {str(e)}")
                return False

    except ImportError as e:
        logger.error(f"❌ Import error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    if add_username_column():
        logger.info("✅ Successfully added username column to users table")
        sys.exit(0)
    else:
        logger.error("❌ Failed to add username column")
        sys.exit(1)
