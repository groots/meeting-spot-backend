"""Alembic migration environment for the Find a Meeting Spot application.

This module configures the Alembic migration environment and provides functions
for running migrations in different contexts (development, production, etc.).
"""

import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option("sqlalchemy.url", get_engine_url())
target_db = current_app.extensions["migrate"].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def get_gcp_connection_config():
    """Get a GCP-specific connection configuration when running in Cloud environment."""
    # Check if we're running in a GCP environment
    if os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT"):
        is_gcp = True
    else:
        is_gcp = False

    if not is_gcp:
        return {}

    # Set appropriate connection pool settings for Cloud SQL
    gcp_config = {
        "pool_size": 5,  # Smaller pool size for Cloud SQL connections
        "max_overflow": 2,
        "pool_timeout": 30,  # Shorter timeout
        "pool_recycle": 1800,  # Recycle connections every 30 minutes
        "connect_args": {
            "sslmode": "prefer",  # Enable SSL for Cloud SQL connections
        },
    }

    # Check for Cloud SQL proxy settings
    instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")
    if instance_connection_name:
        logger.info(f"Using Cloud SQL instance: {instance_connection_name}")
        # Note: actual connection string is handled by SQLAlchemy in Flask app

    return gcp_config


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
        "BITBUCKET_COMMIT",
    ]
    return any(os.environ.get(var) for var in ci_env_vars)


def should_skip_migrations_in_ci():
    """Determine if we should skip migrations in CI."""
    # Check for explicit environment variables that control behavior
    if os.environ.get("FORCE_DB_MIGRATIONS_IN_CI") == "true":
        return False

    if os.environ.get("SKIP_DB_MIGRATIONS_IN_CI") == "true":
        return True

    # Default to skipping in CI
    return is_ci_environment()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # CRITICAL FIX: Always skip actual DB operations in CI environments by default
    # This can be overridden by setting FORCE_DB_MIGRATIONS_IN_CI=true
    if should_skip_migrations_in_ci():
        logger.warning("CI environment detected. Skipping database migrations by default.")
        logger.warning("Set FORCE_DB_MIGRATIONS_IN_CI=true to override this behavior.")

        # Update GitHub step summary if available
        try:
            # Create GitHub step summary if available
            summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_path:
                with open(summary_path, "a") as f:
                    f.write("## ⏩ Database Migrations Skipped\n\n")
                    f.write("CI environment detected - database migrations skipped by default.\n")
                    f.write("To force migrations in CI, set `FORCE_DB_MIGRATIONS_IN_CI=true`\n")
        except Exception:
            pass

        return

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    cfg = config.get_section(config.config_ini_section)

    # Determine the pool class based on environment
    if os.environ.get("FLASK_ENV") == "production":
        # Use a QueuePool for production environments
        poolclass = pool.QueuePool

        # Get GCP-specific configuration if in GCP environment
        # Only apply these for QueuePool
        gcp_config = get_gcp_connection_config()

        # Apply specific SQLAlchemy options for Cloud SQL if needed
        if gcp_config:
            for key, value in gcp_config.items():
                if key != "connect_args":
                    cfg[f"sqlalchemy.{key}"] = str(value)
    else:
        # Use a NullPool for development/testing - no pool config needed
        poolclass = pool.NullPool
        # Don't apply pool config to NullPool
        gcp_config = {}

    # Create the engine with the appropriate configuration
    try:
        connectable = engine_from_config(
            cfg,
            prefix="sqlalchemy.",
            poolclass=poolclass,
        )

        # Apply connect_args if present in GCP config and we're using QueuePool
        if poolclass == pool.QueuePool and gcp_config and "connect_args" in gcp_config:
            # Get the dialect-specific connect_args
            try:
                # First try the direct dialect.connect_args access
                if hasattr(connectable.dialect, "connect_args"):
                    for key, value in gcp_config["connect_args"].items():
                        connectable.dialect.connect_args[key] = value
                    logger.info("Applied connect_args to dialect.connect_args")
                # Then try create_connect_args approach
                elif hasattr(connectable.dialect, "create_connect_args"):
                    logger.info("Using dialect.create_connect_args approach")
                    # For SQLAlchemy that uses create_connect_args
                    # We need to modify the URL object instead for proper connection arg handling
                    url = connectable.url
                    for key, value in gcp_config["connect_args"].items():
                        if not hasattr(url.query, key):
                            url.query[key] = value
                # If neither method works, try setting connect_args on the Engine.dialect
                else:
                    # Some versions of pg8000 with SQLAlchemy use a different approach
                    logger.info(f"Using generic approach for {connectable.dialect.name}")
                    # Set default connection parameters without failing if they don't exist
                    if not hasattr(connectable, "_connect_args"):
                        setattr(connectable, "_connect_args", {})

                    # Apply connect args to every available location that might be used
                    for key, value in gcp_config["connect_args"].items():
                        # Try engine connect_args
                        if hasattr(connectable, "connect_args"):
                            connectable.connect_args[key] = value
                        # Try engine._connect_args
                        if hasattr(connectable, "_connect_args"):
                            connectable._connect_args[key] = value
            except Exception as connect_args_error:
                # Log but don't fail
                logger.warning(f"Could not apply connect_args: {str(connect_args_error)}")
                logger.warning(f"Connection may proceed without these parameters: {gcp_config['connect_args']}")

        # Try to connect and run migrations
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=get_metadata(),
                process_revision_directives=process_revision_directives,
                transaction_per_migration=True,  # Ensure each migration runs in its own transaction
                **current_app.extensions["migrate"].configure_args,
            )

            with context.begin_transaction():
                context.run_migrations()

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")

        # Check if this is a connection error
        if "connection" in str(e).lower() and ("refused" in str(e).lower() or "could not connect" in str(e).lower()):
            logger.error("Database connection failed. This may be expected in CI environments without a database.")

            # If we're in a CI environment with GitHub Actions, create a summary message
            if is_ci_environment():
                logger.warning("CI environment detected - continuing despite database connection error")
                try:
                    # Create GitHub step summary if available
                    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
                    if summary_path:
                        with open(summary_path, "a") as f:
                            f.write("## ⚠️ Database Migration Warning\n\n")
                            f.write("Database connection error occurred, but CI process allowed to continue.\n")
                            f.write("This is expected in environments without a database server.\n\n")
                            f.write(f"Error: `{str(e)}`\n")
                except Exception:
                    pass

                # Exit without error if we're told to ignore DB connection errors
                if os.environ.get("CI_IGNORE_DB_CONNECTION_ERRORS") == "true":
                    logger.info("Exiting with success status to allow CI to continue")
                    return

        # Special handling for common Cloud SQL errors
        if "SSL SYSCALL error" in str(e) or "connection timed out" in str(e).lower():
            logger.error(
                "This appears to be a Cloud SQL connection issue. "
                "Make sure your Cloud SQL proxy is running or IAM permissions are correct."
            )

        # Only raise the exception if we're not in a CI environment or if we're not ignoring errors
        if not is_ci_environment() or os.environ.get("CI_IGNORE_DB_ERRORS") != "true":
            raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
