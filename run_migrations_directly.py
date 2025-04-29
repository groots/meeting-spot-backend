"""
Script to specifically run the migration for the username field directly.
This script can be used to fix the case where the alembic migration didn't run correctly.
"""

import logging
import os
import sys
import time

import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Get database connection string from environment or use default for local development
def get_db_url():
    """Get the database URL based on the environment."""
    # First check if DATABASE_URL is directly set (highest priority)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    # Next check for individual DB connection parameters
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")
    db_host = os.environ.get("DB_HOST")
    db_port = os.environ.get("DB_PORT")

    if db_user and db_pass and db_name and db_host and db_port:
        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # For Cloud SQL with proxy via instance connection name
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    if instance_connection_name:
        db_user = os.environ.get("DB_USER", "postgres")
        db_pass = os.environ.get("DB_PASS", "postgres")
        db_name = os.environ.get("DB_NAME", "find_a_meeting_spot")
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = os.environ.get("DB_PORT", "5432")
        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Local development default (lowest priority)
    return "postgresql://postgres:postgres@localhost:5432/find_a_meeting_spot"


def retry_operation(func, max_retries=5, retry_interval=5):
    """Retry an operation with exponential backoff."""
    retries = 0
    while True:
        try:
            return func()
        except (OperationalError, ProgrammingError) as e:
            # Check if it's a connection error
            if "connection" in str(e).lower() and retries < max_retries:
                retries += 1
                logger.warning(f"Connection error detected, retrying ({retries}/{max_retries})...")
                time.sleep(retry_interval * retries)  # Exponential backoff
            else:
                logger.error(f"Failed after {retries} retries or not a connection error: {str(e)}")
                raise


def add_username_column(engine):
    """Add username and name columns directly to the database."""
    try:
        # Create a session
        Session = sessionmaker(bind=engine)

        def add_columns():
            with Session() as session, session.begin():
                # Check if the columns already exist
                inspector = sa.inspect(engine)
                columns = [col["name"] for col in inspector.get_columns("users")]

                # Add username column if it doesn't exist
                if "username" not in columns:
                    logger.info("Adding username column to users table...")
                    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50)"))
                    try:
                        session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
                        logger.info("Added unique index for username column")
                    except Exception as e:
                        logger.warning(f"Could not create unique index for username: {str(e)}")
                else:
                    logger.info("Username column already exists")

                # Add first_name column if it doesn't exist
                if "first_name" not in columns:
                    logger.info("Adding first_name column to users table...")
                    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(50)"))
                else:
                    logger.info("first_name column already exists")

                # Add last_name column if it doesn't exist
                if "last_name" not in columns:
                    logger.info("Adding last_name column to users table...")
                    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(50)"))
                else:
                    logger.info("last_name column already exists")

                # Add facebook_oauth_id column if it doesn't exist
                if "facebook_oauth_id" not in columns:
                    logger.info("Adding facebook_oauth_id column to users table...")
                    session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_oauth_id VARCHAR(255)"))
                    try:
                        session.execute(
                            text(
                                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_facebook_oauth_id ON users (facebook_oauth_id)"
                            )
                        )
                        logger.info("Added unique index for facebook_oauth_id column")
                    except Exception as e:
                        logger.warning(f"Could not create unique index for facebook_oauth_id: {str(e)}")
                else:
                    logger.info("facebook_oauth_id column already exists")

                # Commit the transaction
                logger.info("Committing transaction...")

        # Retry the column addition if needed
        retry_operation(add_columns)

        def generate_usernames():
            with Session() as session, session.begin():
                logger.info("Generating usernames from email addresses...")
                # Try standard SQL approach
                try:
                    session.execute(
                        text(
                            """
                            UPDATE users
                            SET username = SPLIT_PART(email, '@', 1)
                            WHERE username IS NULL
                            """
                        )
                    )
                    logger.info("Generated usernames using SPLIT_PART function")
                except Exception as e1:
                    logger.warning(f"Could not generate usernames with SPLIT_PART: {str(e1)}")
                    try:
                        session.execute(
                            text(
                                """
                                UPDATE users
                                SET username = SUBSTRING(email FROM 1 FOR POSITION('@' IN email) - 1)
                                WHERE username IS NULL
                                """
                            )
                        )
                        logger.info("Generated usernames using SUBSTRING function")
                    except Exception as e2:
                        logger.warning(f"Could not generate usernames with SUBSTRING: {str(e2)}")

                        # Last resort: fetch and update each user individually
                        try:
                            result = session.execute(text("SELECT id, email FROM users WHERE username IS NULL"))
                            users_updated = 0
                            for row in result:
                                user_id = row[0]
                                email = row[1]
                                username = email.split("@")[0] if "@" in email else email

                                session.execute(
                                    text("UPDATE users SET username = :username WHERE id = :user_id"),
                                    {"username": username, "user_id": user_id},
                                )
                                users_updated += 1

                            logger.info(f"Generated usernames for {users_updated} users individually")
                        except Exception as e3:
                            logger.error(f"All username generation methods failed: {str(e3)}")

                # Commit the transaction
                logger.info("Committing username updates transaction...")

        # Retry the username generation if needed
        retry_operation(generate_usernames)

        logger.info("Migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False


def main():
    """Main function to run the migration."""
    logger.info("Starting direct migration for username fields")

    try:
        # Get database URL
        db_url = get_db_url()
        masked_url = db_url.replace(db_url.split(":")[2].split("@")[0], "***")
        logger.info(f"Using database URL: {masked_url}")

        # Create engine
        engine = create_engine(db_url)

        # Run the migration
        success = add_username_column(engine)

        if success:
            logger.info("Migration completed successfully")
            return 0
        else:
            logger.error("Migration failed")
            return 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
