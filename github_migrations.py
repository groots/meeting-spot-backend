#!/usr/bin/env python3
"""
GitHub Actions Database Migration Script for Find A Meeting Spot.

This script is designed to fix the issues with running database migrations in
GitHub Actions CI environment. It addresses:
1. Unix socket connection issues with pg8000
2. Immutable dictionary problems with connection parameters
3. Proper error handling for CI environments

Usage:
    python github_migrations.py [options]

Options:
    --check          Check if migrations are needed
    --upgrade        Apply all available migrations
    --skip-errors    Skip errors and continue (for CI environments)
    --force          Force migrations even in CI environments
"""

import argparse
import logging
import os
import sys
import traceback
from datetime import datetime

from flask import Flask
from flask_migrate import Migrate
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("github_migrations")


def is_github_actions():
    """Check if we're running in GitHub Actions."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


def setup_database_url():
    """Setup and validate the database URL for GitHub Actions."""
    # First check for DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")

    if not db_url:
        logger.warning("No DATABASE_URL found in environment.")

        # Check for PostgreSQL specific variables
        pguser = os.environ.get("PGUSER") or os.environ.get("DB_USER") or "postgres"
        pgpass = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD")
        pghost = os.environ.get("PGHOST") or os.environ.get("DB_HOST") or "localhost"
        pgport = os.environ.get("PGPORT") or os.environ.get("DB_PORT") or "5432"
        pgdb = os.environ.get("PGDATABASE") or os.environ.get("DB_NAME") or "postgres"

        # Construct a connection string that works well with pg8000
        if pgpass:
            db_url = f"postgresql+pg8000://{pguser}:{pgpass}@{pghost}:{pgport}/{pgdb}"
        else:
            db_url = f"postgresql+pg8000://{pguser}@{pghost}:{pgport}/{pgdb}"

        # No SSL in GitHub Actions test environment
        db_url += "?sslmode=disable"

        logger.info(f"Constructed database URL from environment variables.")
    else:
        # If we have DATABASE_URL, check if we need to modify for pg8000
        if "postgresql:" in db_url and "+pg8000" not in db_url:
            db_url = db_url.replace("postgresql:", "postgresql+pg8000:")
            logger.info("Modified DATABASE_URL to use pg8000 driver")

        # For GitHub Actions, ensure SSL is disabled
        if is_github_actions() and "sslmode=disable" not in db_url:
            if "?" in db_url:
                db_url += "&sslmode=disable"
            else:
                db_url += "?sslmode=disable"
            logger.info("Added sslmode=disable for GitHub Actions environment")

    # Set DATABASE_URL for Flask to use
    os.environ["DATABASE_URL"] = db_url

    # Mask sensitive info for logging
    if ":" in db_url and "@" in db_url:
        safe_url = (
            db_url.split("://")[0] + "://" + db_url.split("://")[1].split(":")[0] + ":****@" + db_url.split("@")[1]
        )
    else:
        safe_url = db_url

    logger.info(f"Using database URL: {safe_url}")
    return db_url


def test_database_connection(db_url):
    """Test direct database connection without Flask."""
    logger.info("Testing direct database connection...")

    try:
        # Create a basic SQLAlchemy engine with pg8000
        engine = create_engine(db_url)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            test_value = result.scalar()

        logger.info(f"Connection test successful: {test_value}")
        return True

    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        traceback.print_exc()
        return False


def create_app():
    """Create a Flask app instance with migrations configured."""
    from app import create_app

    app = create_app()

    # Ensure app is in the application context
    ctx = app.app_context()
    ctx.push()

    return app


def run_migrations(app, args):
    """Run database migrations using Flask-Migrate."""
    from flask import current_app
    from flask_migrate import current, downgrade, upgrade

    logger.info("Setting up migration environment...")

    try:
        # Get the Migrate extension from the app
        migrate = app.extensions.get("migrate")
        if not migrate:
            logger.error("Migration extension not found in app!")
            return False

        if args.check:
            logger.info("Checking for pending migrations...")

            # Get current revision
            current_rev = current(directory=migrate.directory)

            if current_rev == "head":
                logger.info("Database is up to date. No migrations needed.")
                return True
            else:
                logger.info(f"Database needs migration. Current revision: {current_rev}")
                return False

        if args.downgrade:
            logger.info(f"Downgrading database to revision: {args.downgrade}")
            downgrade(directory=migrate.directory, revision=args.downgrade)
            logger.info("Downgrade complete!")
            return True

        if args.upgrade:
            logger.info("Applying database migrations...")

            # Run the migration
            upgrade(directory=migrate.directory)

            logger.info("Migration complete!")

            # Verify current revision is head
            current_rev = current(directory=migrate.directory)
            logger.info(f"Current database revision: {current_rev}")

            return True

        # Default to just printing status info
        logger.info("No migration action specified. Current status:")
        current_rev = current(directory=migrate.directory)
        logger.info(f"Current database revision: {current_rev}")
        return True

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        traceback.print_exc()

        if args.skip_errors:
            logger.warning("Continuing despite migration error (--skip-errors)")
            return True
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Database migration helper for GitHub Actions")

    parser.add_argument("--check", action="store_true", help="Check if migrations are needed")
    parser.add_argument("--upgrade", action="store_true", help="Apply all available migrations")
    parser.add_argument("--downgrade", help="Downgrade to a specific revision")
    parser.add_argument("--skip-errors", action="store_true", help="Skip errors and continue")
    parser.add_argument("--force", action="store_true", help="Force migrations even in CI environments")

    args = parser.parse_args()

    logger.info("=== GitHub Actions Database Migration Tool ===")
    logger.info(f"Running at: {datetime.now().isoformat()}")

    if is_github_actions():
        logger.info("Detected GitHub Actions environment")

    try:
        # Setup database URL
        db_url = setup_database_url()

        # Test direct connection first
        if not test_database_connection(db_url):
            logger.error("Direct database connection failed. Cannot proceed with migrations.")

            if args.skip_errors:
                logger.warning("Exiting with success due to --skip-errors flag")
                return 0
            return 1

        # Create Flask app and run migrations
        app = create_app()

        if run_migrations(app, args):
            logger.info("Migration process completed successfully")
            return 0
        else:
            logger.error("Migration process failed")

            if args.skip_errors:
                logger.warning("Exiting with success due to --skip-errors flag")
                return 0
            return 1

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()

        if args.skip_errors:
            logger.warning("Exiting with success due to --skip-errors flag")
            return 0
        return 1


if __name__ == "__main__":
    sys.exit(main())
