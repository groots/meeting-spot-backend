"""Script to test database connection and user creation."""
import os
import sys

from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

# Load environment variables if needed
# from dotenv import load_dotenv
# load_dotenv()

# Use the same connection string as the production app
# Replace with the actual value if needed
DATABASE_URL = "postgresql+pg8000://meetingspot:MeetingSpot123!@/findameetingspot?unix_sock=/cloudsql/find-a-meeting-spot:us-east1:findameetingspot/.s.PGSQL.5432"


def test_connection():
    """Test database connection and basic operations."""
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        # Test connection
        with engine.connect() as conn:
            # Check version
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"Successfully connected to database. PostgreSQL version: {version}")

            # Check if users table exists and has the expected schema
            result = conn.execute(
                text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
            )
            print("\nUsers table schema:")
            for row in result:
                print(f"- {row[0]}: {row[1]}")

            # Try to insert a test user
            email = "test_script@example.com"
            password_hash = generate_password_hash("test123")

            # Check if user already exists
            result = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email})
            if result.fetchone():
                print(f"\nUser {email} already exists")
            else:
                # Create new user
                try:
                    conn.execute(
                        text(
                            "INSERT INTO users (id, email, password_hash, created_at, updated_at) VALUES (uuid_generate_v4(), :email, :password_hash, NOW(), NOW())"
                        ),
                        {"email": email, "password_hash": password_hash},
                    )
                    conn.commit()
                    print(f"\nSuccessfully created test user: {email}")
                except Exception as e:
                    print(f"\nError creating user: {str(e)}")

    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
