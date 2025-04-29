"""
Script to specifically run the migration for the places tables directly.
This script can be used to fix the case where the places tables don't exist.
"""

import logging
import os
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
    return "postgresql://postgres:ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ@localhost:5433/findameetingspot_dev"


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


def create_places_tables(engine):
    """Create places tables directly in the database."""
    try:
        # Create a session
        Session = sessionmaker(bind=engine)

        def run_migration():
            with Session() as session, session.begin():
                # Check if the tables already exist
                inspector = sa.inspect(engine)
                tables = inspector.get_table_names()

                # Create places table if it doesn't exist
                if "places" not in tables:
                    logger.info("Creating places table...")
                    session.execute(
                        text(
                            """
                        CREATE TABLE places (
                            id UUID NOT NULL,
                            name VARCHAR NOT NULL,
                            address VARCHAR NOT NULL,
                            latitude FLOAT NOT NULL,
                            longitude FLOAT NOT NULL,
                            google_place_id VARCHAR,
                            suggested_by_id UUID NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                            updated_at TIMESTAMP WITH TIME ZONE,
                            PRIMARY KEY (id),
                            UNIQUE (google_place_id),
                            FOREIGN KEY(suggested_by_id) REFERENCES users (id) ON DELETE CASCADE
                        )
                    """
                        )
                    )
                    logger.info("Places table created successfully")
                else:
                    logger.info("Places table already exists")

                # Create meeting_request_suggested_places table if it doesn't exist
                if "meeting_request_suggested_places" not in tables:
                    logger.info("Creating meeting_request_suggested_places table...")
                    session.execute(
                        text(
                            """
                        CREATE TABLE meeting_request_suggested_places (
                            meeting_request_id UUID NOT NULL,
                            place_id UUID NOT NULL,
                            created_at TIMESTAMP DEFAULT now(),
                            PRIMARY KEY (meeting_request_id, place_id),
                            FOREIGN KEY(meeting_request_id) REFERENCES meeting_requests (request_id) ON DELETE CASCADE,
                            FOREIGN KEY(place_id) REFERENCES places (id) ON DELETE CASCADE
                        )
                    """
                        )
                    )
                    logger.info("meeting_request_suggested_places table created successfully")
                else:
                    logger.info("meeting_request_suggested_places table already exists")

                # Check if selected_place_id column exists in meeting_requests
                meeting_requests_columns = [col["name"] for col in inspector.get_columns("meeting_requests")]
                if "selected_place_id" not in meeting_requests_columns:
                    logger.info("Adding selected_place_id column to meeting_requests table...")
                    session.execute(
                        text(
                            """
                        ALTER TABLE meeting_requests ADD COLUMN selected_place_id UUID;
                        ALTER TABLE meeting_requests ADD CONSTRAINT meeting_requests_selected_place_id_fkey
                            FOREIGN KEY (selected_place_id) REFERENCES places (id) ON DELETE CASCADE;
                    """
                        )
                    )
                    logger.info("selected_place_id column added successfully")
                else:
                    logger.info("selected_place_id column already exists")

                # Update alembic_version table
                session.execute(text("UPDATE alembic_version SET version_num = '9b430c7496d6'"))
                logger.info("Updated alembic_version to 9b430c7496d6")

                # Commit the transaction
                logger.info("Committing transaction...")

        # Retry the operation if needed
        retry_operation(run_migration)

        logger.info("Places tables migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False


def main():
    """Main function to run the migration."""
    logger.info("Starting direct migration for places tables")

    try:
        # Get database URL
        db_url = get_db_url()
        # Mask password in logs
        masked_url = db_url
        if "@" in db_url and ":" in db_url.split("@")[0]:
            parts = db_url.split("@")
            auth = parts[0].split(":")
            masked_url = f"{auth[0]}:****@{parts[1]}"
        logger.info(f"Using database URL: {masked_url}")

        # Create engine
        engine = create_engine(db_url)

        # Run migration
        success = create_places_tables(engine)

        if success:
            logger.info("Migration completed successfully")
        else:
            logger.error("Migration failed")
            exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
