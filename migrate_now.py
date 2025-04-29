"""
A simple endpoint to run migrations directly.
This is designed to be invoked via the web to trigger migration scripts.
"""

import logging
import os

from flask import Flask, jsonify
from sqlalchemy import create_engine

from run_migrations_directly import add_username_column, get_db_url

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


# Add health check endpoint
@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Run the app locally for testing (not for production)
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
