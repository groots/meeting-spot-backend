#!/usr/bin/env python3

from sqlalchemy import text

from app import create_app, db


def add_missing_columns():
    """Add missing columns to meeting_requests table"""
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        try:
            # Get columns that currently exist in the table
            result = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'meeting_requests'")
            ).fetchall()
            existing_columns = [row[0] for row in result]

            print(f"Current columns in meeting_requests table: {existing_columns}")

            # We need to check for and add all the required columns
            required_columns = {
                "location_a": "JSONB",
                "location_b": "JSONB",
                "user_b_email": "VARCHAR(120)",
                "user_b_name": "VARCHAR(255)",
            }

            for column, data_type in required_columns.items():
                if column not in existing_columns:
                    print(f"Adding {column} column...")
                    conn.execute(text(f"ALTER TABLE meeting_requests ADD COLUMN {column} {data_type}"))
                    conn.commit()
                    print(f"Added {column} column")
                else:
                    print(f"{column} column already exists")

            print("Migration completed successfully")

        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    add_missing_columns()
