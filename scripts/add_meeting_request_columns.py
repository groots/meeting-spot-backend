#!/usr/bin/env python3

from sqlalchemy import text

from app import create_app, db


def add_meeting_request_columns():
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

            # Check if user_b_email column exists
            if "user_b_email" not in existing_columns:
                print("Adding user_b_email column...")
                conn.execute(text("ALTER TABLE meeting_requests ADD COLUMN user_b_email VARCHAR(120)"))
                conn.commit()
                print("Added user_b_email column")
            else:
                print("user_b_email column already exists")

            # Check if user_b_name column exists
            if "user_b_name" not in existing_columns:
                print("Adding user_b_name column...")
                conn.execute(text("ALTER TABLE meeting_requests ADD COLUMN user_b_name VARCHAR(255)"))
                conn.commit()
                print("Added user_b_name column")
            else:
                print("user_b_name column already exists")

            print("Migration completed successfully")

        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    add_meeting_request_columns()
