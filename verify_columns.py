#!/usr/bin/env python3

import getpass

from sqlalchemy import create_engine, text


def verify_columns():
    """Verify that the meeting_requests table has the correct columns"""
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
        # Check all columns in the meeting_requests table
        result = conn.execute(
            text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'meeting_requests'
                ORDER BY ordinal_position
                """
            )
        ).fetchall()

        print("Meeting Requests Table Columns:")
        print("===============================")
        for row in result:
            column_name, data_type, is_nullable = row
            nullable = "NULL" if is_nullable == "YES" else "NOT NULL"
            print(f"{column_name:25} {data_type:15} {nullable}")

        print("\nVerifying required columns...")
        # Check for our specific columns
        required_columns = ["location_a", "location_b", "selected_place_id"]
        missing_columns = []

        for col_name in required_columns:
            if not any(col[0] == col_name for col in result):
                missing_columns.append(col_name)

        if missing_columns:
            print(f"ERROR: The following required columns are missing: {', '.join(missing_columns)}")
        else:
            print("All required columns are present!")

            # Print details of the required columns
            required_cols_details = [col for col in result if col[0] in required_columns]
            for col in required_cols_details:
                print(f"  - {col[0]} ({col[1]}, {'NULLABLE' if col[2] == 'YES' else 'NOT NULL'})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            conn.close()
        except:
            pass


if __name__ == "__main__":
    verify_columns()
