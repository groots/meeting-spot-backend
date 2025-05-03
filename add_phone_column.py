#!/usr/bin/env python3
"""Simple script to add the phone column to the users table."""

from sqlalchemy import inspect, text

from app import create_app, db


def add_phone_column():
    """Add the phone column to the users table if it doesn't exist."""
    app = create_app("production")
    with app.app_context():
        inspector = inspect(db.engine)
        if "users" not in inspector.get_table_names():
            print("Error: users table does not exist!")
            return False

        columns = [col["name"] for col in inspector.get_columns("users")]
        print(f"Existing columns in users table: {columns}")

        if "phone" not in columns:
            print("phone column is missing - adding it now")

            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                conn.execute(text("CREATE INDEX ix_users_phone ON users (phone)"))

            # Verify the column was added
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "phone" in columns:
                print("Successfully added phone column!")
                return True
            else:
                print("Failed to add phone column!")
                return False
        else:
            print("phone column already exists!")
            return True


if __name__ == "__main__":
    add_phone_column()
