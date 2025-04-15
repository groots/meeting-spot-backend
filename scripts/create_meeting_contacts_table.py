#!/usr/bin/env python3

from sqlalchemy import text

from app import create_app, db


def create_meeting_contacts_table():
    """Create meeting_contacts join table"""
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        try:
            # Check if the table already exists
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'meeting_contacts')")
            ).fetchone()

            if result and result[0]:
                print("meeting_contacts table already exists.")
                return

            print("Creating meeting_contacts table...")
            conn.execute(
                text(
                    """
                CREATE TABLE meeting_contacts (
                    meeting_request_id UUID NOT NULL REFERENCES meeting_requests(request_id) ON DELETE CASCADE,
                    contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (meeting_request_id, contact_id)
                )
                """
                )
            )
            conn.commit()
            print("Successfully created meeting_contacts table!")

        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    create_meeting_contacts_table()
