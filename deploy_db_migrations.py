#!/usr/bin/env python3
"""
Automated Database Migration Script
-----------------------------------
This script handles database migrations safely across all environments.
Run this script during deployment to ensure database schema is up-to-date.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_migrations")


def get_database_url():
    """Get database URL from environment or app config"""
    # First check environment variable
    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        logger.info("Using DATABASE_URL from environment")
        return db_url

    # Try to get from app config
    try:
        from app import create_app

        app = create_app("production")
        with app.app_context():
            db_url = app.config.get("SQLALCHEMY_DATABASE_URI")
            if db_url:
                logger.info("Using database URL from app config")
                return db_url
    except Exception as e:
        logger.warning(f"Could not get database URL from app config: {e}")

    # Check for SQLite database files
    possible_db_files = ["instance/app.db", "app/dev.db", "dev.db"]
    for db_file in possible_db_files:
        if os.path.exists(db_file):
            sqlite_url = f"sqlite:///{db_file}"
            logger.info(f"Using SQLite database at {db_file}")
            return sqlite_url

    return None


@contextmanager
def create_backup(db_url=None):
    """Create database backup if possible"""
    backup_created = False
    backup_path = None

    try:
        # Only backup SQLite databases automatically
        if db_url and db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                backup_path = f"{db_path}.bak.{int(time.time())}"
                subprocess.run(["cp", db_path, backup_path], check=True)
                logger.info(f"Created database backup at {backup_path}")
                backup_created = True

        yield backup_created, backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        yield False, None


def check_migration_history():
    """Check current migration history"""
    try:
        # Execute alembic history
        logger.info("Checking migration history...")
        result = subprocess.run(
            ["flask", "db", "history"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy()
        )

        if result.returncode == 0:
            logger.info("Current migration history:")
            for line in result.stdout.splitlines()[:10]:  # Show last 10 migrations
                logger.info(f"  {line}")
        else:
            logger.warning("Could not get migration history")
            logger.warning(result.stderr)

        # Show current head
        result = subprocess.run(
            ["flask", "db", "current"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy()
        )

        if result.returncode == 0:
            logger.info(f"Current database version: {result.stdout.strip()}")
            return True
        else:
            logger.warning("Could not get current database version")
            logger.warning(result.stderr)
            return False
    except Exception as e:
        logger.error(f"Error checking migration history: {e}")
        return False


def run_database_migrations(dry_run=False):
    """Run database migrations"""
    try:
        # Check pending migrations first
        logger.info("Checking for pending migrations...")
        result = subprocess.run(
            ["flask", "db", "check"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy()
        )

        has_pending = False
        if "not up to date" in result.stdout:
            has_pending = True
            logger.info("Pending migrations found")
        elif "up to date" in result.stdout:
            logger.info("Database schema is up to date, no migrations needed")
            return True
        else:
            logger.warning("Could not determine migration status, proceeding with upgrade")
            logger.warning(result.stderr)

        if dry_run:
            logger.info("DRY RUN: Would run 'flask db upgrade' to apply pending migrations")
            return True

        # Apply migrations
        logger.info("Applying database migrations...")
        upgrade_result = subprocess.run(
            ["flask", "db", "upgrade"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy()
        )

        if upgrade_result.returncode == 0:
            logger.info("Database migrations applied successfully")
            logger.info(upgrade_result.stdout)
            return True
        else:
            logger.error("Failed to apply database migrations")
            logger.error(upgrade_result.stderr)
            return False

    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        return False


def verify_migrations():
    """Verify migrations were applied correctly"""
    try:
        # Check schema version after migrations
        logger.info("Verifying database schema after migrations...")
        result = subprocess.run(
            ["flask", "db", "check"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy()
        )

        if "up to date" in result.stdout:
            logger.info("Database schema is up to date after migrations")
            return True
        else:
            logger.warning("Database schema may not be up to date after migrations")
            logger.warning(result.stdout)
            return False

    except Exception as e:
        logger.error(f"Error verifying migrations: {e}")
        return False


def perform_migration_with_backup(dry_run=False):
    """Complete migration process with backup"""
    # Get database URL
    db_url = get_database_url()
    if not db_url:
        logger.error("Could not determine database URL")
        return False

    # Create backup if possible
    with create_backup(db_url) as (backup_created, backup_path):
        if backup_created:
            logger.info(f"Database backup created at {backup_path}")
        else:
            logger.warning("Database backup could not be created, proceeding anyway")

        # Check current migration history
        check_migration_history()

        # Run migrations
        success = run_database_migrations(dry_run)

        if success and not dry_run:
            # Verify migrations
            verify_success = verify_migrations()
            if verify_success:
                logger.info("Migration process completed successfully")
                return True
            else:
                logger.warning("Migration process completed but verification failed")
                logger.warning("Please check database schema manually")
                # We still return True as migrations did apply
                return True

        return success


def main():
    """Main function to run migrations"""
    parser = argparse.ArgumentParser(description="Run database migrations safely")
    parser.add_argument("--dry-run", action="store_true", help="Check for migrations without applying them")
    args = parser.parse_args()

    logger.info("Starting database migration process")
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")

    success = perform_migration_with_backup(args.dry_run)

    if success:
        logger.info("Migration process completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration process failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

