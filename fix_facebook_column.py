#!/usr/bin/env python
"""Fix the missing Facebook OAuth column in the users table."""

import os
import sqlite3
from pathlib import Path

# Get the path to the SQLite database
db_path = Path(__file__).parent / "instance" / "dev.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if the column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "facebook_oauth_id" not in columns:
        print("Adding facebook_oauth_id column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN facebook_oauth_id VARCHAR(255)")
        conn.commit()
        print("Column added successfully!")
    else:
        print("facebook_oauth_id column already exists.")

    # Verify the column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if "facebook_oauth_id" in columns:
        print("Verification passed: Column exists in users table.")
    else:
        print("ERROR: Column was not added successfully.")

except Exception as e:
    print(f"Error adding column: {e}")
finally:
    conn.close()

print("Done.")
