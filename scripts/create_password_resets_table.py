"""
Script to create the password_resets table.
This is a fallback in case the Alembic migration doesn't work.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, inspect
from sqlalchemy.dialects.postgresql import UUID

from app import create_app, db


def create_table():
    """Create the password_resets table if it doesn't exist."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Check if the table already exists
        if "password_resets" in inspector.get_table_names():
            print("Table 'password_resets' already exists.")
            return

        # Create the table manually
        password_resets = Table(
            "password_resets",
            db.metadata,
            Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            Column("token", String(100), unique=True, nullable=False, index=True),
            Column("is_used", Boolean, default=False, nullable=False),
            Column("expires_at", DateTime(timezone=True), nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)),
            Column("updated_at", DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)),
        )

        # Create the table
        try:
            password_resets.create(db.engine)
            print("Table 'password_resets' created successfully.")
        except Exception as e:
            print(f"Error creating 'password_resets' table: {e}")


if __name__ == "__main__":
    create_table()
