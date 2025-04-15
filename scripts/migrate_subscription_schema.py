#!/usr/bin/env python3

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, MetaData, String, Table, inspect, text
from sqlalchemy.dialects.postgresql import UUID

from app import create_app, db


def migrate_subscription_schema():
    """Add subscription model fields and tables"""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        conn = db.engine.connect()

        # Add columns to users table if they don't exist
        if "stripe_customer_id" not in [col["name"] for col in inspector.get_columns("users")]:
            print("Adding subscription columns to users table...")
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255) UNIQUE, "
                    "ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50), "
                    "ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50), "
                    "ADD COLUMN IF NOT EXISTS subscription_end_date TIMESTAMP WITH TIME ZONE"
                )
            )
            conn.commit()
            print("Added subscription columns to users table.")
        else:
            print("Subscription columns already exist in users table.")

        # Create subscriptions table if it doesn't exist
        if not inspector.has_table("subscriptions"):
            print("Creating subscriptions table...")
            meta = MetaData()

            # Define subscriptions table
            Table(
                "subscriptions",
                meta,
                Column("id", UUID, primary_key=True),
                Column("user_id", UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                Column("stripe_subscription_id", String(255), unique=True),
                Column("stripe_customer_id", String(255)),
                Column("plan_id", String(50), nullable=False),
                Column("status", String(50), nullable=False),
                Column("current_period_start", DateTime(timezone=True)),
                Column("current_period_end", DateTime(timezone=True)),
                Column("cancel_at_period_end", Boolean, default=False),
                Column(
                    "created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
                ),
                Column(
                    "updated_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
                ),
            )

            # Create the table
            meta.create_all(db.engine)
            print("Created subscriptions table.")
        else:
            print("Subscriptions table already exists.")

        print("Migration completed successfully.")
        # Apply migrations
        db.session.commit()

        # Test creating a new User object to verify columns exist
        try:
            from app.models.user import User

            test_user = User(email="test_subscription@example.com", subscription_plan="free")
            db.session.add(test_user)
            db.session.commit()
            db.session.delete(test_user)
            db.session.commit()
            print("Successfully created test user with subscription columns.")
        except Exception as e:
            print(f"Error creating test user: {e}")
            db.session.rollback()


if __name__ == "__main__":
    migrate_subscription_schema()
