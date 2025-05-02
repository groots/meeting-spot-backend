"""Alembic migration environment for the Find a Meeting Spot application.

This module configures the Alembic migration environment and provides functions
for running migrations in different contexts (development, production, etc.).
"""

import logging
import os
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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """

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
        gcp_config = {}

    connectable = engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=poolclass,
    )

    # Apply connect_args if present in GCP config
    if gcp_config and "connect_args" in gcp_config:
        for key, value in gcp_config["connect_args"].items():
            connectable.dialect.dbapi.connect_args[key] = value

    # Use a try-except block to catch specific Cloud SQL connection issues
    try:
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
        # Special handling for common Cloud SQL errors
        if "SSL SYSCALL error" in str(e) or "connection timed out" in str(e).lower():
            logger.error(
                "This appears to be a Cloud SQL connection issue. "
                "Make sure your Cloud SQL proxy is running or IAM permissions are correct."
            )
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
