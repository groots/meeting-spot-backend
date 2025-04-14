#!/usr/bin/env python
"""
Fix Password Hash Column Length

This script directly alters the password_hash column in the users table
to increase its size from 128 to 256 characters, which is needed for the
current password hashing algorithm (scrypt).

Usage:
    python fix_password_hash_column.py
"""

import os
import sys
from datetime import datetime

import pg8000
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection info from environment variables
DB_USER = os.getenv("DB_USER", "meetingspot")
DB_PASS = os.getenv("DB_PASS", "MeetingSpot123!")
DB_NAME = os.getenv("DB_NAME", "findameetingspot")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

# For Cloud SQL with socket
DB_SOCKET_DIR = os.getenv("DB_SOCKET_DIR", "/cloudsql")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "find-a-meeting-spot:us-east1:findameetingspot")


def log(message):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def connect_with_connector():
    """Connect to Cloud SQL using the socket connector."""
    log("Connecting to database using socket connector...")

    unix_socket = f"{DB_SOCKET_DIR}/{INSTANCE_CONNECTION_NAME}/.s.PGSQL.5432"

    try:
        conn = pg8000.connect(user=DB_USER, password=DB_PASS, database=DB_NAME, unix_sock=unix_socket)
        log("Connected successfully using socket connector!")
        return conn
    except Exception as e:
        log(f"Error connecting with socket connector: {e}")
        return None


def connect_with_tcp():
    """Connect to database using TCP."""
    log(f"Connecting to database at {DB_HOST}:{DB_PORT}...")

    try:
        conn = pg8000.connect(user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST, port=DB_PORT)
        log("Connected successfully using TCP!")
        return conn
    except Exception as e:
        log(f"Error connecting with TCP: {e}")
        return None


def fix_password_hash_column(conn):
    """Alter the password_hash column to 256 characters."""
    try:
        cursor = conn.cursor()

        # Check current column definition first
        cursor.execute(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'password_hash'
        """
        )

        result = cursor.fetchone()
        current_length = result[0] if result else None

        if current_length == 256:
            log("Password hash column is already 256 characters. No change needed.")
            return True

        log(f"Current password_hash column length: {current_length}")
        log("Altering password_hash column to 256 characters...")

        # Alter the column
        cursor.execute(
            """
            ALTER TABLE users
            ALTER COLUMN password_hash TYPE varchar(256)
        """
        )

        # Commit the transaction
        conn.commit()

        # Verify the change
        cursor.execute(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'password_hash'
        """
        )

        result = cursor.fetchone()
        new_length = result[0] if result else None

        log(f"New password_hash column length: {new_length}")

        if new_length == 256:
            log("Successfully altered password_hash column!")
            return True
        else:
            log("Failed to alter column correctly.")
            return False

    except Exception as e:
        log(f"Error altering password_hash column: {e}")
        conn.rollback()
        return False


def main():
    """Main function to fix the password hash column."""
    log("Starting password hash column fix...")

    # Try to connect using the socket connector first (for Cloud SQL)
    conn = connect_with_connector()

    # If that fails, try TCP connection
    if not conn:
        log("Socket connection failed, trying TCP...")
        conn = connect_with_tcp()

    if not conn:
        log("Failed to connect to database. Exiting.")
        sys.exit(1)

    try:
        success = fix_password_hash_column(conn)

        if success:
            log("Password hash column fix completed successfully!")
        else:
            log("Failed to fix password hash column.")
            sys.exit(1)

    finally:
        # Close the connection
        if conn:
            conn.close()
            log("Database connection closed.")


if __name__ == "__main__":
    main()
