#!/usr/bin/env python3
"""
Subscription model migration script

This script creates a new subscriptions table and migrates data from
the User model's subscription fields to the new Subscription model.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import Column, ForeignKey, create_engine, text
from sqlalchemy.dialects.postgresql import UUID

from app import create_app, db
from app.models.subscription import Subscription
from app.models.user import User


def migrate_subscriptions():
    """
    Create the subscriptions table and migrate data from User model
    """
    app = create_app()

    with app.app_context():
        # Check if subscriptions table already exists
        engine = db.engine
        inspector = db.inspect(engine)

        # Create the table if it doesn't exist
        if "subscriptions" not in inspector.get_table_names():
            print("Creating subscriptions table...")

            # Create the table using SQLAlchemy's create_all mechanism
            Subscription.__table__.create(engine)
            print("Subscriptions table created successfully!")
        else:
            print("Subscriptions table already exists")

        # Migrate data from User model
        print("Migrating data from User model...")

        # Get all users with subscription data
        # First check if the fields exist on User model
        user_fields = [c.name for c in inspector.get_columns("users")]

        if "subscription_plan" in user_fields and "subscription_status" in user_fields:
            # Get all users with subscription info
            users_with_subscriptions = User.query.filter(
                User.subscription_plan.isnot(None), User.subscription_status.isnot(None)
            ).all()

            print(f"Found {len(users_with_subscriptions)} users with subscription data")

            # Create a subscription for each user
            for user in users_with_subscriptions:
                # Skip if user already has a subscription
                existing_sub = Subscription.query.filter_by(user_id=user.id).first()
                if existing_sub:
                    print(f"User {user.email} already has a subscription, skipping")
                    continue

                # Create a new subscription
                subscription = Subscription(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    plan_id=user.subscription_plan or "free",
                    status=user.subscription_status or "inactive",
                    current_period_start=datetime.now(timezone.utc),
                    current_period_end=user.subscription_end_date,
                    stripe_customer_id=getattr(user, "stripe_customer_id", None),
                    cancel_at_period_end=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                db.session.add(subscription)
                print(f"Created subscription for user {user.email}")

            db.session.commit()
            print("Migration completed successfully!")
        else:
            print("User model doesn't have subscription fields, nothing to migrate")


if __name__ == "__main__":
    migrate_subscriptions()
