"""
A simple endpoint to run the places migration directly.
This is designed to be invoked via the web to trigger migration scripts.
"""

import logging
import os

from flask import Flask, jsonify
from sqlalchemy import create_engine

from apply_places_migration import create_places_tables, get_db_url

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/")
def home():
    """Home page with instructions."""
    return """
    <html>
        <head><title>Places Migration Tool</title></head>
        <body>
            <h1>Places Migration Tool</h1>
            <p>This tool helps apply the places migration to your database.</p>
            <p>Click the button below to run the migration:</p>
            <form action="/run-migration" method="get">
                <button type="submit">Run Places Migration</button>
            </form>
            <p>Check health status: <a href="/health">Health Check</a></p>
        </body>
    </html>
    """


@app.route("/run-migration")
def migrate():
    """Run the migration and return the status."""
    try:
        logger.info("Starting places migration endpoint")

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

        # Run the migration
        success = create_places_tables(engine)

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
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
