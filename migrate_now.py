"""
A simple endpoint to run migrations directly.
This is designed to be invoked via the web to trigger migration scripts.
"""

import logging
import os

from flask import Flask, jsonify
from sqlalchemy import create_engine

from run_migrations_directly import add_username_column

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Get database connection string from environment or use default for local development
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


@app.route("/")
def migrate():
    """Run the migration and return the status."""
    try:
        logger.info("Starting migration endpoint")

        # Get database URL
        db_url = get_db_url()
        logger.info(f"Using database URL: {db_url.replace(db_url.split(':')[2].split('@')[0], '***')}")

        # Create engine
        engine = create_engine(db_url)

        # Run the migration
        success = add_username_column(engine)

        if success:
            logger.info("Migration completed successfully")
            return jsonify({"status": "success", "message": "Migration completed successfully"})
        else:
            logger.error("Migration failed")
            return jsonify({"status": "error", "message": "Migration failed"}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500


if __name__ == "__main__":
    # Run the app locally for testing (not for production)
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
