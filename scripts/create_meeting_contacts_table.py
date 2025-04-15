"""
Script to create the meeting_contacts association table.
This is a fallback in case the Alembic migration doesn't work.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, inspect
from sqlalchemy.dialects.postgresql import UUID

from app import create_app, db


def create_table():
    """Create the meeting_contacts association table if it doesn't exist."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        # Check if the table already exists
        if "meeting_contacts" in inspector.get_table_names():
            print("meeting_contacts table already exists.")
            return

        # Create the table manually
        meeting_contacts = Table(
            "meeting_contacts",
            db.metadata,
            Column(
                "meeting_request_id",
                UUID(as_uuid=True),
                ForeignKey("meeting_requests.request_id", ondelete="CASCADE"),
                primary_key=True,
            ),
            Column("contact_id", UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
            Column("created_at", DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc)),
        )

        # Create the table
        try:
            meeting_contacts.create(db.engine)
            print("Table 'meeting_contacts' created successfully.")
        except Exception as e:
            print(f"Error creating 'meeting_contacts' table: {e}")


if __name__ == "__main__":
    create_table()
