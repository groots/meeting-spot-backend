import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_connection():
    """Test the database connection."""
    print("Attempting to connect to database...")

    try:
        # Connect to the database using the proxy
        conn = psycopg2.connect(
            host="127.0.0.1",  # Use localhost since we're using the proxy
            port=5433,
            database="findameetingspot_dev",
            user="postgres",
            password="ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ",
        )

        # Create a cursor
        cursor = conn.cursor()

        # Test the connection
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"Successfully connected to database. PostgreSQL version: {version[0]}")

        # Close the connection
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error connecting to database: {e}")


if __name__ == "__main__":
    test_connection()
