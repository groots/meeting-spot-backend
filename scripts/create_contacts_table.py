#!/usr/bin/env python3

from sqlalchemy import text

from app import create_app, db


def create_contacts_table():
    """Create contacts table with all required columns"""
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        try:
            # Check if the table already exists
            table_exists = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'contacts')")
            ).fetchone()

            if table_exists and table_exists[0]:
                # Table exists, check for missing columns
                result = conn.execute(
                    text("SELECT column_name FROM information_schema.columns WHERE table_name = 'contacts'")
                ).fetchall()
                existing_columns = [row[0] for row in result]
                print(f"Existing columns in contacts table: {existing_columns}")

                # Add missing columns if needed
                required_columns = {
                    "id": "UUID PRIMARY KEY",
                    "user_id": "UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE",
                    "name": "VARCHAR(255)",
                    "email": "VARCHAR(120) NOT NULL",
                    "phone": "VARCHAR(50)",
                    "company": "VARCHAR(255)",
                    "notes": "TEXT",
                    "created_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()",
                    "updated_at": "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()",
                }

                for column, data_type in required_columns.items():
                    if column not in existing_columns:
                        print(f"Adding column {column} to contacts table...")
                        conn.execute(text(f"ALTER TABLE contacts ADD COLUMN {column} {data_type}"))
                        conn.commit()
                        print(f"Added column {column}")

                print("Updated contacts table with all required columns")
            else:
                # Create the table from scratch
                print("Creating contacts table...")
                conn.execute(
                    text(
                        """
                    CREATE TABLE contacts (
                        id UUID PRIMARY KEY,
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        name VARCHAR(255),
                        email VARCHAR(120) NOT NULL,
                        phone VARCHAR(50),
                        company VARCHAR(255),
                        notes TEXT,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                    """
                    )
                )
                conn.commit()
                print("Successfully created contacts table!")

        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    create_contacts_table()
