"""
Verify the database schema in production and check if the required columns exist.
"""

import logging
import os
import sys

import sqlalchemy as sa
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_url():
    """Get the database URL based on the environment."""
    # For Cloud SQL with proxy
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    if instance_connection_name:
        db_user = os.environ.get("DB_USER", "postgres")
        db_pass = os.environ.get("DB_PASS", "postgres")
        db_name = os.environ.get("DB_NAME", "find_a_meeting_spot")

        # When deployed to Google Cloud Run, use the proxy provided by the runtime
        db_host = os.environ.get("DB_HOST", "127.0.0.1")
        db_port = os.environ.get("DB_PORT", "5432")

        return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    # Local development default
    return "postgresql://postgres:postgres@localhost:5432/find_a_meeting_spot"


def verify_columns(engine):
    """Verify that the required columns exist in the users table."""
    try:
        # Check if the columns exist
        inspector = sa.inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("users")]

        logger.info("Found columns in users table: %s", columns)

        # Check for required columns
        required_columns = ["username", "first_name", "last_name", "facebook_oauth_id"]
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            logger.warning("Missing columns: %s", missing_columns)
            return False
        else:
            logger.info("All required columns exist!")
            return True

    except Exception as e:
        logger.error(f"Error verifying columns: {str(e)}")
        return False


def check_user_data(engine):
    """Check if users have username values populated."""
    try:
        # Create a connection
        with engine.connect() as conn:
            # Check total users
            total_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            logger.info(f"Total users in database: {total_users}")

            # Check users with usernames
            users_with_username = conn.execute(text("SELECT COUNT(*) FROM users WHERE username IS NOT NULL")).scalar()
            logger.info(f"Users with username: {users_with_username}")

            # Check users without usernames
            users_without_username = conn.execute(text("SELECT COUNT(*) FROM users WHERE username IS NULL")).scalar()
            logger.info(f"Users without username: {users_without_username}")

            # Sample usernames
            sample_users = conn.execute(text("SELECT id, email, username FROM users LIMIT 5")).fetchall()
            logger.info("Sample users:")
            for user in sample_users:
                logger.info(f"  ID: {user[0]}, Email: {user[1]}, Username: {user[2]}")

            return users_with_username, users_without_username

    except Exception as e:
        logger.error(f"Error checking user data: {str(e)}")
        return 0, 0


def main():
    """Main function to verify the database schema."""
    logger.info("Starting database schema verification")

    try:
        # Get database URL
        db_url = get_db_url()
        masked_url = db_url.replace(db_url.split(":")[2].split("@")[0], "***")
        logger.info(f"Using database URL: {masked_url}")

        # Create engine
        engine = create_engine(db_url)

        # Verify columns
        columns_exist = verify_columns(engine)

        # Check user data
        if columns_exist:
            users_with_username, users_without_username = check_user_data(engine)

            if users_without_username > 0:
                logger.warning(f"{users_without_username} users still need usernames")
            else:
                logger.info("All users have usernames!")

        logger.info("Verification completed")
        return 0 if columns_exist else 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
