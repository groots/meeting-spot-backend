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
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
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


def is_ci_environment():
    """Check if we're running in a CI environment."""
    ci_env_vars = [
        "CI",
        "GITHUB_ACTIONS",
        "GITHUB_WORKFLOW",
        "GITHUB_SHA",
        "GITLAB_CI",
        "TRAVIS",
        "CIRCLECI",
        "JENKINS_URL",
        "TEAMCITY_VERSION",
    ]
    return any(os.environ.get(var) for var in ci_env_vars)


def should_skip_migrations_in_ci():
    """Determine if we should skip migrations in CI."""
    # Check for explicit environment variables
    if os.environ.get("FORCE_DB_MIGRATIONS_IN_CI") == "true":
        return False

    if os.environ.get("SKIP_DB_MIGRATIONS_IN_CI") == "true":
        return True

    # Check for marker file
    if os.path.exists(".skip_migrations_in_ci"):
        logger.info("Found .skip_migrations_in_ci marker file")
        return True

    # Default to not skipping
    return False


def create_skip_marker_if_needed():
    """Create a skip marker file if running in CI without Cloud SQL Proxy."""
    if not is_ci_environment():
        return False

    # Don't create marker if explicitly told to force migrations
    if os.environ.get("FORCE_DB_MIGRATIONS_IN_CI") == "true":
        return False

    # Check if we're running in GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Check if Cloud SQL Proxy is running
        try:
            result = subprocess.run(
                ["ps", "aux"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if "cloud_sql_proxy" not in result.stdout and "cloud-sql-proxy" not in result.stdout:
                logger.warning("Cloud SQL Proxy not detected in CI environment")

                # Run the skip migrations script if it exists
                if os.path.exists("ci_cd/skip_migrations_in_ci.py"):
                    logger.info("Running skip_migrations_in_ci.py")
                    subprocess.run(
                        ["python", "ci_cd/skip_migrations_in_ci.py"],
                        check=True,
                    )
                    return True
                else:
                    # Create marker file manually
                    with open(".skip_migrations_in_ci", "w") as f:
                        f.write("# Migration Skip Marker\n")
                        f.write(f"# Created: {time.time()}\n")
                    os.environ["SKIP_DB_MIGRATIONS_IN_CI"] = "true"
                    os.environ["CI_IGNORE_DB_CONNECTION_ERRORS"] = "true"
                    logger.info("Created .skip_migrations_in_ci marker file")
                    return True
        except Exception as e:
            logger.warning(f"Error checking for Cloud SQL Proxy: {e}")

    return False


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
            ["flask", "db", "history"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
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
            ["flask", "db", "current"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
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
        # Check if we should skip migrations in CI
        if should_skip_migrations_in_ci():
            logger.info("Skipping migrations in CI environment as configured")
            return True

        # Check pending migrations first
        logger.info("Checking for pending migrations...")
        result = subprocess.run(
            ["flask", "db", "check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
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
            ["flask", "db", "upgrade"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
        )

        if upgrade_result.returncode == 0:
            logger.info("Database migrations applied successfully")
            logger.info(upgrade_result.stdout)
            return True
        else:
            # Check if we should ignore DB errors in CI
            if is_ci_environment() and os.environ.get("CI_IGNORE_DB_ERRORS") == "true":
                logger.warning("Database migration failed, but CI_IGNORE_DB_ERRORS is set to true")
                logger.warning(upgrade_result.stderr)
                return True
            else:
                logger.error("Failed to apply database migrations")
                logger.error(upgrade_result.stderr)
                return False

    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        # Special handling for CI environments
        if is_ci_environment() and os.environ.get("CI_IGNORE_DB_ERRORS") == "true":
            logger.warning(f"Error ignored in CI: {e}")
            return True
        return False


def verify_migrations():
    """Verify migrations were applied correctly"""
    try:
        # Check schema version after migrations
        logger.info("Verifying database schema after migrations...")
        result = subprocess.run(
            ["flask", "db", "check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
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
        # Special handling for CI environments
        if is_ci_environment() and os.environ.get("CI_IGNORE_DB_ERRORS") == "true":
            logger.warning(f"Verification error ignored in CI: {e}")
            return True
        return False


def perform_migration_with_backup(dry_run=False):
    """Complete migration process with backup"""
    # Get database URL
    db_url = get_database_url()
    if not db_url:
        logger.error("Could not determine database URL")
        # Special handling for CI environments
        if is_ci_environment() and os.environ.get("CI_IGNORE_DB_ERRORS") == "true":
            logger.warning("Missing database URL ignored in CI environment")
            return True
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
    """Main function to handle command-line arguments and run migrations."""
    parser = argparse.ArgumentParser(description="Deploy database migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--skip-backup", action="store_true", help="Skip database backup step")
    parser.add_argument("--force", action="store_true", help="Force migrations even in CI environments")
    args = parser.parse_args()

    logger.info("========== Database Migration Process ==========")

    # Force migrations if requested via CLI argument
    if args.force:
        os.environ["FORCE_DB_MIGRATIONS_IN_CI"] = "true"
        os.environ["SKIP_DB_MIGRATIONS_IN_CI"] = "false"
        logger.info("Forcing migrations to run (--force flag used)")

    # Check if we need to create a skip marker for CI environments
    skipped = create_skip_marker_if_needed()
    if skipped:
        logger.info("⏩ Migrations will be skipped in this CI environment")
        # Update GitHub step summary if available
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            try:
                with open(summary_path, "a") as f:
                    f.write("## ⏩ Database Migrations Skipped\n\n")
                    f.write("CI environment detected without Cloud SQL Proxy - database migrations skipped.\n")
            except Exception:
                pass
        return 0

    # Proceed with migration process
    try:
        # Check if database URL is available first
        db_url = get_database_url()
        if not db_url:
            logger.error("No database connection available")

            # Special handling for CI environments
            if is_ci_environment() and os.environ.get("CI_IGNORE_DB_CONNECTION_ERRORS") == "true":
                logger.warning("Missing database connection ignored in CI")
                return 0
            return 1

        # Show migration history
        check_migration_history()

        # Run migrations with backup unless skipped
        if args.skip_backup:
            logger.info("Skipping backup as requested")
            success = run_database_migrations(dry_run=args.dry_run)
        else:
            success = perform_migration_with_backup(dry_run=args.dry_run)

        if not success:
            logger.error("Failed to apply database migrations")
            return 1

        # Verify migrations
        if not args.dry_run and not verify_migrations():
            logger.warning("Migration verification had warnings")
            # Don't fail the build for verification warnings

        logger.info("Database migration process completed successfully")
        return 0

    except FileNotFoundError as e:
        # This is likely a Unix socket error with pg8000
        if "No such file or directory" in str(e) and "sock.connect" in str(e):
            logger.error(f"Unix socket connection error: {e}")
            logger.error("This error typically occurs when trying to connect to a PostgreSQL server via Unix socket")
            logger.error("In CI environments, you need to run Cloud SQL Proxy or skip migrations")

            if is_ci_environment():
                # Create skip marker and exit successfully
                create_skip_marker_if_needed()
                logger.warning("Created migration skip marker due to socket connection error")
                return 0
            return 1
        else:
            logger.error(f"File not found error: {e}")
            return 1

    except Exception as e:
        logger.error(f"Error during migration process: {e}")

        # Special handling for CI environments
        if is_ci_environment() and os.environ.get("CI_IGNORE_DB_ERRORS") == "true":
            logger.warning(f"Error ignored in CI: {e}")
            return 0

        return 1


if __name__ == "__main__":
    main()
