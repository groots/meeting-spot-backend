"""
A web endpoint to verify the database schema in production.
This can be deployed to Cloud Run to check if the required columns exist.
"""

import logging
import os

from flask import Flask, jsonify
from sqlalchemy import create_engine

from verify_db_schema import check_user_data, get_db_url, verify_columns

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def verify_database():
    """Verify the database schema and return the results."""
    try:
        logger.info("Starting database verification endpoint")

        # Get database URL
        db_url = get_db_url()
        masked_url = db_url.replace(db_url.split(":")[2].split("@")[0], "***")
        logger.info(f"Using database URL: {masked_url}")

        # Create engine
        engine = create_engine(db_url)

        # Verify columns
        columns_exist = verify_columns(engine)

        # Result data
        result = {"column_verification": "success" if columns_exist else "failed", "user_data": {}}

        # Check user data if columns exist
        if columns_exist:
            users_with_username, users_without_username = check_user_data(engine)
            result["user_data"] = {
                "users_with_username": users_with_username,
                "users_without_username": users_without_username,
            }

        logger.info("Verification completed")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500


# Add health check endpoint
@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Run the app locally for testing (not for production)
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
