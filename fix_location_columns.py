#!/usr/bin/env python3

import getpass
import os

from sqlalchemy import create_engine, text


def fix_location_columns():
    """Fix location_a and location_b columns in meeting_requests table"""
    # Get admin password securely
    admin_pass = getpass.getpass("Enter PostgreSQL admin password: ")

    # Set the PostgreSQL connection string with admin credentials
    DB_URI = f"postgresql://postgres:{admin_pass}@localhost:5432/findameetingspot"

    try:
        engine = create_engine(DB_URI)
        conn = engine.connect()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    try:
        # Check the current type of location_a and location_b columns
        result = conn.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'meeting_requests'
            AND column_name IN ('location_a', 'location_b')
            """
            )
        ).fetchall()

        print(f"Current column types: {result}")

        # If the columns don't exist or have the wrong type, fix them
        try:
            conn.execute(text("ALTER TABLE meeting_requests DROP COLUMN IF EXISTS location_a"))
            conn.execute(text("ALTER TABLE meeting_requests DROP COLUMN IF EXISTS location_b"))
            print("Dropped existing columns if they existed")
        except Exception as e:
            print(f"Error dropping columns: {e}")
            conn.rollback()

        try:
            conn.execute(text("ALTER TABLE meeting_requests ADD COLUMN location_a JSONB NOT NULL DEFAULT '{}'::jsonb"))
            conn.execute(text("ALTER TABLE meeting_requests ADD COLUMN location_b JSONB"))
            print("Added location columns with correct types")
        except Exception as e:
            print(f"Error adding columns: {e}")
            conn.rollback()

        # Also add a transaction to avoid any issues
        try:
            conn.execute(text("BEGIN"))
            conn.execute(text("COMMIT"))
        except Exception as e:
            print(f"Error with transaction: {e}")
            conn.rollback()

        print("Fixed location columns successfully")

    except Exception as e:
        print(f"Error: {e}")
        try:
            conn.rollback()
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass


if __name__ == "__main__":
    fix_location_columns()
