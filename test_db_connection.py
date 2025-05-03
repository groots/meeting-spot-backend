#!/usr/bin/env python3
"""
Database connection test script for Find A Meeting Spot.

This script verifies that the pg8000 adapter works correctly with SQLAlchemy and
cloud-sql-python-connector in this environment.
"""

import argparse
import logging
import os
import sys
import traceback
from datetime import datetime

import pg8000
import sqlalchemy
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("db_test")

# Load environment variables
load_dotenv()


def get_pg8000_info():
    """Get information about the pg8000 module."""
    logger.info(f"pg8000 version: {pg8000.__version__}")

    # Check pg8000 module attributes
    pg8000_attrs = [attr for attr in dir(pg8000) if not attr.startswith("_")]
    logger.info(f"pg8000 top-level attributes: {pg8000_attrs}")

    # Check for connect method
    if hasattr(pg8000, "connect"):
        logger.info("pg8000.connect method exists")
    else:
        logger.warning("pg8000.connect method NOT FOUND")

    # Check for dbapi module
    if hasattr(pg8000, "dbapi"):
        logger.info("pg8000.dbapi module exists")
        dbapi_attrs = [attr for attr in dir(pg8000.dbapi) if not attr.startswith("_")]
        logger.info(f"pg8000.dbapi attributes: {dbapi_attrs}")
    else:
        logger.warning("pg8000.dbapi module NOT FOUND")


def test_direct_connection(dsn):
    """Test connection using pg8000 directly."""
    logger.info("Testing direct pg8000 connection...")

    try:
        # Parse DSN into connection parameters
        params = {}
        for part in dsn.split():
            key, value = part.split("=", 1)
            params[key] = value

        # Connect directly with pg8000
        conn = pg8000.connect(
            user=params.get("user"),
            password=params.get("password"),
            host=params.get("host"),
            port=int(params.get("port", 5432)),
            database=params.get("dbname"),
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"Connected successfully. PostgreSQL version: {version}")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Direct connection failed: {str(e)}")
        traceback.print_exc()
        return False


def test_sqlalchemy_connection(dsn):
    """Test connection using SQLAlchemy with pg8000."""
    logger.info("Testing SQLAlchemy connection with pg8000...")

    try:
        # Create SQLAlchemy engine with pg8000
        engine = create_engine(f"postgresql+pg8000://{dsn.replace('=', ':', 1).replace(' ', '&')}")

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"SQLAlchemy connected successfully. PostgreSQL version: {version}")

        # Get engine and dialect details
        logger.info(f"SQLAlchemy version: {sqlalchemy.__version__}")
        logger.info(f"Engine: {engine}")
        logger.info(f"Dialect: {engine.dialect.__class__.__name__}")

        # Check for connect_args attribute in dialect
        if hasattr(engine.dialect, "connect_args"):
            logger.info("engine.dialect.connect_args exists")
            logger.info(f"Current connect_args: {engine.dialect.connect_args}")
        else:
            logger.warning("engine.dialect.connect_args NOT FOUND")

        # Check for _connect_args attribute in engine
        if hasattr(engine, "_connect_args"):
            logger.info("engine._connect_args exists")
        else:
            logger.warning("engine._connect_args NOT FOUND")

        # Check for create_connect_args method in dialect
        if hasattr(engine.dialect, "create_connect_args"):
            logger.info("engine.dialect.create_connect_args exists")
            try:
                args = engine.dialect.create_connect_args(engine.url)
                logger.info(f"create_connect_args result type: {type(args)}")
            except:
                logger.warning("Failed to call create_connect_args")
        else:
            logger.warning("engine.dialect.create_connect_args NOT FOUND")

        return True

    except Exception as e:
        logger.error(f"SQLAlchemy connection failed: {str(e)}")
        traceback.print_exc()
        return False


def main():
    """Main function to run tests."""
    parser = argparse.ArgumentParser(description="Test database connections")
    parser.add_argument(
        "--dsn",
        default=os.getenv("DATABASE_URL"),
        help="Database connection string in format 'user=username password=pass host=host port=5432 dbname=db'",
    )

    args = parser.parse_args()

    if not args.dsn:
        logger.error("No DSN provided. Set DATABASE_URL environment variable or use --dsn.")
        return 1

    logger.info("=== Find A Meeting Spot Database Connection Tester ===")
    logger.info(f"Running tests at: {datetime.now().isoformat()}")

    # Get information about pg8000
    get_pg8000_info()

    # Run tests
    direct_success = test_direct_connection(args.dsn)
    sqlalchemy_success = test_sqlalchemy_connection(args.dsn)

    # Summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Direct pg8000 connection: {'SUCCESS' if direct_success else 'FAILED'}")
    logger.info(f"SQLAlchemy with pg8000: {'SUCCESS' if sqlalchemy_success else 'FAILED'}")

    if direct_success and sqlalchemy_success:
        logger.info("✅ All database connection tests passed!")
        return 0
    else:
        logger.error("❌ Some database connection tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
