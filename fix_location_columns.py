#!/usr/bin/env python3

import getpass
import os

from sqlalchemy import create_engine, text


def fix_location_columns():
    """Fix columns in meeting_requests table"""
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
        # Check the current columns in the meeting_requests table
        result = conn.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'meeting_requests'
            AND column_name IN ('location_a', 'location_b', 'selected_place_id')
            """
            )
        ).fetchall()

        print(f"Current column types: {result}")
        column_names = [col[0] for col in result]

        # Fix location_a and location_b columns if needed
        if "location_a" not in column_names or "location_b" not in column_names:
            try:
                if "location_a" not in column_names:
                    conn.execute(
                        text("ALTER TABLE meeting_requests ADD COLUMN location_a JSONB NOT NULL DEFAULT '{}'::jsonb")
                    )
                    print("Added location_a column")

                if "location_b" not in column_names:
                    conn.execute(text("ALTER TABLE meeting_requests ADD COLUMN location_b JSONB"))
                    print("Added location_b column")
            except Exception as e:
                print(f"Error adding location columns: {e}")
                conn.rollback()

        # Fix selected_place_id column if needed
        if "selected_place_id" not in column_names:
            try:
                # Add selected_place_id column with UUID type without foreign key constraint
                conn.execute(
                    text(
                        """
                ALTER TABLE meeting_requests ADD COLUMN selected_place_id UUID
                """
                    )
                )
                print("Added selected_place_id column")
            except Exception as e:
                print(f"Error adding selected_place_id column: {e}")
                conn.rollback()

        # Commit the changes
        try:
            conn.commit()
            print("Fixed meeting_requests table columns successfully")
        except Exception as e:
            print(f"Error committing changes: {e}")
            conn.rollback()

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
