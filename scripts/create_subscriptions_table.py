#!/usr/bin/env python3

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import create_app, db


def create_subscriptions_table():
    """Create subscriptions table with direct SQL"""
    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # Create the table with direct SQL
        print("Creating subscriptions table...")
        try:
            # Check if the table already exists
            result = conn.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'subscriptions')")
            ).fetchone()

            if result and result[0]:
                print("Subscriptions table already exists.")
                return

            # Create the table
            conn.execute(
                text(
                    """
                CREATE TABLE subscriptions (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    stripe_subscription_id VARCHAR(255) UNIQUE,
                    stripe_customer_id VARCHAR(255),
                    plan_id VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    current_period_start TIMESTAMP WITH TIME ZONE,
                    current_period_end TIMESTAMP WITH TIME ZONE,
                    cancel_at_period_end BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
                )
            )
            conn.commit()
            print("Successfully created subscriptions table!")

            # Add a test subscription for our premium user
            premium_user_id = None
            premium_user = conn.execute(text("SELECT id FROM users WHERE email = 'premium@example.com'")).fetchone()

            if premium_user:
                premium_user_id = premium_user[0]
                sub_id = uuid.uuid4()
                now = datetime.now(timezone.utc)
                end_date = now + timedelta(days=365)

                # Create a subscription for the premium user
                conn.execute(
                    text(
                        f"""
                    INSERT INTO subscriptions (
                        id, user_id, plan_id, status, current_period_start,
                        current_period_end, cancel_at_period_end, created_at, updated_at
                    ) VALUES (
                        '{sub_id}', '{premium_user_id}', 'premium', 'active',
                        '{now.isoformat()}', '{end_date.isoformat()}',
                        FALSE, '{now.isoformat()}', '{now.isoformat()}'
                    )
                    """
                    )
                )
                conn.commit()
                print(f"Added subscription for premium user (id: {premium_user_id})")
            else:
                print("Premium user not found. Run create_premium_user.py first.")

        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    create_subscriptions_table()
