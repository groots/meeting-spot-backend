#!/usr/bin/env python
"""
Database migration fix script.

This script creates tables that are missing from the database in the correct order,
respecting dependencies between tables.
"""

import os
import sys
from datetime import datetime

import click
import sqlalchemy as sa
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData, create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import ForeignKeyConstraint

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import Contact, MeetingRequest, User


@click.command()
@click.option("--database-url", help="Database URL to use, overrides environment variable")
@click.option("--dry-run", is_flag=True, help="Show SQL but do not execute")
def fix_migrations(database_url, dry_run):
    """Fix database migrations by creating missing tables in the correct order."""
    app = create_app()

    # Use provided database URL or the one from app config
    db_url = database_url or app.config.get("SQLALCHEMY_DATABASE_URI")
    if not db_url:
        click.echo("Error: No database URL provided and none found in app config")
        sys.exit(1)

    click.echo(f"Connecting to database: {db_url.replace(':/', '://****:****@')}")

    # Create engine and connect
    engine = create_engine(db_url)
    conn = engine.connect()
    inspector = inspect(engine)
    metadata = MetaData()

    # Check which tables already exist
    existing_tables = inspector.get_table_names()
    click.echo(f"Existing tables: {', '.join(existing_tables)}")

    # Tables to create in order (respecting dependencies)
    tables_to_create = []

    # Check if contacts table exists
    if "contacts" not in existing_tables:
        click.echo("Adding 'contacts' table to creation list")
        tables_to_create.append(
            {
                "name": "contacts",
                "creation": lambda: sa.Table(
                    "contacts",
                    metadata,
                    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
                    sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column("name", sa.String(255), nullable=False),
                    sa.Column("email", sa.String(255), nullable=True),
                    sa.Column("phone", sa.String(50), nullable=True),
                    sa.Column("company", sa.String(255), nullable=True),
                    sa.Column("notes", sa.Text(), nullable=True),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                    sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
                ),
            }
        )

    # Check if meeting_contacts table exists
    if "meeting_contacts" not in existing_tables:
        click.echo("Adding 'meeting_contacts' table to creation list")
        tables_to_create.append(
            {
                "name": "meeting_contacts",
                "creation": lambda: sa.Table(
                    "meeting_contacts",
                    metadata,
                    sa.Column("meeting_request_id", postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                    sa.ForeignKeyConstraint(
                        ["meeting_request_id"], ["meeting_requests.request_id"], ondelete="CASCADE"
                    ),
                    sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
                    sa.PrimaryKeyConstraint("meeting_request_id", "contact_id"),
                ),
            }
        )

    # If no tables to create, we're done
    if not tables_to_create:
        click.echo("All required tables exist. No changes needed.")
        return

    # Create tables
    click.echo(f"Will create {len(tables_to_create)} tables: {', '.join(t['name'] for t in tables_to_create)}")

    if dry_run:
        click.echo("DRY RUN - Not executing changes")
        # Just print the SQL
        for table_info in tables_to_create:
            table = table_info["creation"]()
            click.echo(f"\nSQL for creating {table_info['name']}:")
            click.echo(sa.schema.CreateTable(table).compile(engine))
        return

    # Actually create the tables
    try:
        with conn.begin() as transaction:
            for table_info in tables_to_create:
                click.echo(f"Creating table: {table_info['name']}")
                table = table_info["creation"]()
                table.create(engine)

            # Update alembic_version to reflect our changes
            if "alembic_version" in existing_tables:
                # Get context to manage migrations
                context = MigrationContext.configure(conn)

                # Set version to the latest migration (hardcoded for simplicity)
                # This should be the latest migration version
                latest_revision = "a4b2c3d5e6f7"  # Our new contacts table migration

                # Update alembic_version
                context._update_current_rev(None, latest_revision)
                click.echo(f"Updated alembic_version to: {latest_revision}")

            click.echo("All tables created successfully!")
    except Exception as e:
        click.echo(f"Error creating tables: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    fix_migrations()
