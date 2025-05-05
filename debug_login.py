#!/usr/bin/env python3
"""
Debug Login Functionality

This script tests login queries directly against the database to diagnose
any issues with user authentication.
"""

import os
import sys
import traceback
import uuid
from datetime import datetime, timezone

from flask import Flask
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

# Configure paths for imports
sys.path.insert(0, os.path.abspath("."))

# Setup logging
import logging

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("debug_login")


def check_database_connection(app, db):
    """Check the database connection and basic queries."""
    logger.info("Starting database connection check")
    try:
        with app.app_context():
            # Check if we can connect to the database at all
            result = db.session.execute(text("SELECT 1")).fetchone()
            logger.info(f"Basic database query result: {result}")

            # Check all tables in the database
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"Database tables: {tables}")

            if "users" not in tables:
                logger.error("CRITICAL ERROR: 'users' table doesn't exist!")
                return False

            # Print details about users table
            users_columns = [col["name"] for col in inspector.get_columns("users")]
            logger.info(f"Users table columns: {users_columns}")

            # Check required columns
            required_columns = ["id", "email", "password_hash"]
            missing_columns = [col for col in required_columns if col not in users_columns]
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False

            logger.info("Database connection and schema look good")
            return True
    except Exception as e:
        logger.error(f"Error checking database connection: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def test_user_queries(app, db, test_email="test@example.com"):
    """Test queries used in the login endpoint."""
    from app.models.user import User

    logger.info(f"Testing user queries for email: {test_email}")
    try:
        with app.app_context():
            # Method 1: ORM Query
            logger.info("Trying ORM query...")
            user = User.query.filter_by(email=test_email).first()
            if user:
                logger.info(f"Found user with email {test_email} via ORM query (id: {user.id})")
            else:
                logger.warning(f"User with email {test_email} not found via ORM query")

            # Method 2: Specific Column Query
            logger.info("Trying specific column query...")
            query = db.session.query(User.id, User.email, User.password_hash).filter(User.email == test_email)
            user_data = query.first()
            if user_data:
                logger.info(f"Found user with email {test_email} via specific column query")
            else:
                logger.warning(f"User with email {test_email} not found via specific column query")

            # Method 3: Raw SQL query
            logger.info("Trying raw SQL query...")
            stmt = text("SELECT id, email, password_hash FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": test_email}).fetchone()
            if result:
                logger.info(f"Found user with email {test_email} via raw SQL query")
            else:
                logger.warning(f"User with email {test_email} not found via raw SQL query")

            # List all users
            logger.info("Listing all users in database...")
            all_users = User.query.all()
            logger.info(f"Total users: {len(all_users)}")
            for user in all_users[:5]:  # Show first 5 users only
                logger.info(f"User: {user.email} (id: {user.id})")

            if len(all_users) > 5:
                logger.info(f"... and {len(all_users) - 5} more users")

            return True
    except Exception as e:
        logger.error(f"Error testing user queries: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def create_test_user(app, db, email="test@example.com", password="testpassword"):
    """Create a test user if it doesn't exist."""
    from app.models.user import User

    logger.info(f"Checking if test user {email} exists, or creating one")
    try:
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                logger.info(f"Test user {email} already exists (id: {existing_user.id})")
                return existing_user

            # Create new user
            logger.info(f"Creating new test user {email}")
            now = datetime.now(timezone.utc)
            new_user = User(
                id=uuid.uuid4(),
                email=email,
                password_hash=generate_password_hash(password),
                created_at=now,
                updated_at=now,
            )

            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Created test user {email} (id: {new_user.id})")
            return new_user
    except Exception as e:
        logger.error(f"Error creating test user: {str(e)}")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return None


def main():
    """Main function for debugging login."""
    logger.info("Starting login debug script")

    try:
        # Try with different environment settings
        env_options = ["development", "production", "testing"]
        from app import create_app, db

        for env in env_options:
            logger.info(f"Trying with {env} environment...")
            try:
                app = create_app(env)

                # Log the database URL (without credentials)
                db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
                safe_db_url = db_url.split("@")[-1] if "@" in db_url else db_url
                logger.info(f"Database URL: {safe_db_url}")

                # Check database connection
                if check_database_connection(app, db):
                    # Try to login with test user
                    email = "test@example.com"
                    password = "testpassword"

                    # Create test user if needed
                    if create_test_user(app, db, email, password):
                        # Test user queries
                        test_user_queries(app, db, email)

                        # Try logging in manually with this user
                        with app.app_context():
                            from app.models.user import User

                            user = User.query.filter_by(email=email).first()
                            if user and user.check_password(password):
                                logger.info(f"Successfully logged in as {email}")

                                # Try generating a token
                                try:
                                    token = user.generate_access_token()
                                    logger.info(f"Successfully generated token")
                                except Exception as e:
                                    logger.error(f"Failed to generate token: {str(e)}")
                            else:
                                logger.error(f"Failed to log in as {email}")

                    logger.info(f"Environment {env} worked successfully!")
                    break
                else:
                    logger.warning(f"Environment {env} failed database connection check")
            except Exception as e:
                logger.error(f"Error with environment {env}: {str(e)}")
                logger.error(traceback.format_exc())

        logger.info("Login debug script completed")
        return 0
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
