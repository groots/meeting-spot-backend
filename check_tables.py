import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

print("Checking database tables...")
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        # Get all tables
        result = connection.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """
            )
        )
        tables = result.fetchall()

        print("\nDatabase tables:")
        for table in tables:
            table_name = table[0]
            print(f"\n- {table_name}")

            # Get columns for each table
            columns = connection.execute(
                text(
                    f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """
                )
            )
            print("  Columns:")
            for column in columns:
                print(f"    - {column[0]}: {column[1]}")

        print("\nDatabase check complete!")
except Exception as e:
    print(f"Error checking database: {e}")
