#!/usr/bin/env python3
"""
Migration Health Check Tool

This script performs diagnostics on the Alembic migration setup and helps
identify and fix common issues with database migrations.
"""

import argparse
import logging
import os
import subprocess
import sys
from configparser import ConfigParser

from sqlalchemy import create_engine, inspect, text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("migration_health")


def get_database_url():
    """Get database URL from environment or alembic config"""
    # First check environment variable
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # Try to get from alembic.ini
    try:
        config = ConfigParser()
        alembic_ini = os.path.join(os.path.dirname(__file__), "alembic.ini")
        if os.path.exists(alembic_ini):
            config.read(alembic_ini)
            if "alembic" in config and "sqlalchemy.url" in config["alembic"]:
                return config["alembic"]["sqlalchemy.url"]
    except Exception as e:
        logger.warning(f"Could not read alembic.ini: {e}")

    return None


def check_migration_directory():
    """Check if migration directory structure is correct"""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")

    if not os.path.exists(migrations_dir):
        logger.error("❌ Migrations directory not found!")
        return False

    versions_dir = os.path.join(migrations_dir, "versions")
    if not os.path.exists(versions_dir):
        logger.error("❌ Versions directory not found!")
        return False

    env_py = os.path.join(migrations_dir, "env.py")
    if not os.path.exists(env_py):
        logger.error("❌ env.py not found!")
        return False

    # Check if any migration files exist
    migration_files = [f for f in os.listdir(versions_dir) if f.endswith(".py")]
    if not migration_files:
        logger.warning("⚠️ No migration files found. Have you created any migrations?")
    else:
        logger.info(f"✅ Found {len(migration_files)} migration files")

    return True


def check_database_connection(db_url=None):
    """Check if we can connect to the database"""
    if not db_url:
        db_url = get_database_url()

    if not db_url:
        logger.error("❌ No database URL found! Set DATABASE_URL environment variable or configure in alembic.ini")
        return False

    try:
        # Create a database engine
        engine = create_engine(db_url)

        # Try to connect
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Successfully connected to database")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return False


def check_alembic_version_table(db_url=None):
    """Check if alembic_version table exists"""
    if not db_url:
        db_url = get_database_url()

    if not db_url:
        logger.error("❌ No database URL found!")
        return False

    try:
        # Create a database engine
        engine = create_engine(db_url)

        # Check if alembic_version table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "alembic_version" in tables:
            # Check if there's a version in the table
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = result.fetchall()

                if versions:
                    logger.info(f"✅ Found alembic_version table with version: {versions[0][0]}")
                    return True
                else:
                    logger.warning("⚠️ alembic_version table exists but has no version!")
                    return False
        else:
            logger.warning("⚠️ alembic_version table not found! Database may not be under migration control")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking alembic_version table: {e}")
        return False


def check_migration_history():
    """Check alembic migration history"""
    try:
        # Set environment variables
        env = os.environ.copy()
        env["FLASK_APP"] = "app:create_app"

        # Run flask db current
        result = subprocess.run(
            ["flask", "db", "current"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        if result.returncode == 0:
            current_rev = result.stdout.strip()
            logger.info(f"✅ Current database revision: {current_rev}")
        else:
            logger.error(f"❌ Failed to get current revision: {result.stderr}")
            return False

        # Run flask db check
        result = subprocess.run(
            ["flask", "db", "check"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )

        if "up to date" in result.stdout:
            logger.info("✅ Database schema is up to date")
        elif "not up to date" in result.stdout:
            logger.warning("⚠️ Database schema is not up to date!")
            logger.warning("⚠️ Run 'flask db upgrade' to apply pending migrations")
        else:
            logger.error(f"❌ Error checking database schema: {result.stderr}")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Error checking migration history: {e}")
        return False


def fix_missing_alembic_table(db_url=None, force=False):
    """Initialize alembic_version table if missing"""
    if not db_url:
        db_url = get_database_url()

    if not db_url:
        logger.error("❌ No database URL found!")
        return False

    try:
        # Create a database engine and check if table exists
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "alembic_version" not in tables or force:
            logger.info("Creating alembic_version table...")

            # Set environment variables
            env = os.environ.copy()
            env["FLASK_APP"] = "app:create_app"

            # Run flask db stamp to initialize the table with current version
            result = subprocess.run(
                ["flask", "db", "stamp", "head"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
            )

            if result.returncode == 0:
                logger.info("✅ Successfully initialized alembic_version table")
                return True
            else:
                logger.error(f"❌ Failed to initialize alembic_version table: {result.stderr}")
                return False
        else:
            logger.info("alembic_version table already exists")
            return True
    except Exception as e:
        logger.error(f"❌ Error fixing alembic_version table: {e}")
        return False


def main():
    """Main function for migration health check"""
    parser = argparse.ArgumentParser(description="Database Migration Health Check Tool")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    parser.add_argument("--force", action="store_true", help="Force fixes even if not needed")
    args = parser.parse_args()

    logger.info("=== Database Migration Health Check ===")

    # Step 1: Check migration directory structure
    logger.info("\n1. Checking migration directory structure...")
    dir_check = check_migration_directory()

    # Step 2: Check database connection
    logger.info("\n2. Checking database connection...")
    db_url = get_database_url()
    conn_check = check_database_connection(db_url)

    # If we can't connect to the database, exit
    if not conn_check:
        logger.error("Cannot continue without database connection")
        return 1

    # Step 3: Check alembic_version table
    logger.info("\n3. Checking alembic_version table...")
    version_table_check = check_alembic_version_table(db_url)

    # Step 4: Check migration history
    logger.info("\n4. Checking migration history...")
    history_check = check_migration_history()

    # Summary
    logger.info("\n=== Health Check Summary ===")
    logger.info(f"Migration directory structure: {'✅ OK' if dir_check else '❌ Issues found'}")
    logger.info(f"Database connection: {'✅ OK' if conn_check else '❌ Issues found'}")
    logger.info(f"Alembic version table: {'✅ OK' if version_table_check else '⚠️ Issues found'}")
    logger.info(f"Migration history: {'✅ OK' if history_check else '⚠️ Issues found'}")

    # Fix issues if requested
    if args.fix:
        logger.info("\n=== Fixing Issues ===")

        # Fix missing alembic_version table
        if not version_table_check or args.force:
            logger.info("Fixing alembic_version table...")
            fix_missing_alembic_table(db_url, args.force)

        # Re-check after fixes
        logger.info("\n=== Re-checking After Fixes ===")
        version_table_check = check_alembic_version_table(db_url)
        history_check = check_migration_history()

        logger.info(f"Alembic version table: {'✅ OK' if version_table_check else '⚠️ Still has issues'}")
        logger.info(f"Migration history: {'✅ OK' if history_check else '⚠️ Still has issues'}")

    # Return code
    if dir_check and conn_check and version_table_check and history_check:
        logger.info("\n✅ All checks passed! Database migration setup is healthy.")
        return 0
    else:
        logger.warning("\n⚠️ Some issues were found. Review the output and fix them.")
        if not args.fix:
            logger.info("Run with --fix to attempt automatic fixes")
        return 1


if __name__ == "__main__":
    sys.exit(main())
