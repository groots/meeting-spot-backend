"""Debug script to test user registration directly."""
import os
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

# Database connection string
DATABASE_URL = "postgresql+pg8000://meetingspot:MeetingSpot123!@/findameetingspot?unix_sock=/cloudsql/find-a-meeting-spot:us-east1:findameetingspot/.s.PGSQL.5432"


def debug_registration():
    """Test user registration directly against the database."""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        # Connect to database
        with engine.connect() as conn:
            # Generate test user data
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            password_hash = generate_password_hash("Password123!")
            now = datetime.now(timezone.utc).isoformat()
            user_id = uuid.uuid4()

            print(f"Attempting to register user: {email}")

            # Check users table structure
            result = conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position"
                )
            )
            print("\nUsers table schema:")
            columns = []
            for row in result:
                columns.append(row[0])
                nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                print(f"- {row[0]}: {row[1]} {nullable}")

            # Create SQL INSERT based on columns
            insert_sql = """
            INSERT INTO users (id, email, password_hash, created_at, updated_at)
            VALUES (:id, :email, :password_hash, :created_at, :updated_at)
            """

            # Try to insert user
            try:
                result = conn.execute(
                    text(insert_sql),
                    {
                        "id": user_id,
                        "email": email,
                        "password_hash": password_hash,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                conn.commit()
                print(f"\nSuccessfully created user {email} with ID {user_id}")
                return True
            except Exception as e:
                print(f"\nError inserting user: {str(e)}")
                print(f"SQL: {insert_sql}")
                print(f"Parameters: id={user_id}, email={email}")

                # Try with raw SQL as a fallback
                try:
                    raw_sql = f"""
                    INSERT INTO users (id, email, password_hash, created_at, updated_at)
                    VALUES ('{user_id}', '{email}', '{password_hash}', '{now}', '{now}')
                    """
                    conn.execute(text(raw_sql))
                    conn.commit()
                    print(f"Successfully created user with raw SQL")
                    return True
                except Exception as e2:
                    print(f"Error with raw SQL: {str(e2)}")
                    return False

    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False


if __name__ == "__main__":
    success = debug_registration()
    sys.exit(0 if success else 1)
