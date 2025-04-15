#!/usr/bin/env python3
import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models.subscription import Subscription
from app.models.user import User


def create_premium_user():
    """
    Create or update a premium user for testing purposes
    """
    app = create_app("development")
    with app.app_context():
        # Check if the premium user already exists
        email = "premium@example.com"
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            print(f"Premium user already exists with email: {email}")
            user = existing_user
        else:
            # Create a new premium user
            user = User(email=email)
            user.set_password("premium123")
            db.session.add(user)
            db.session.commit()
            print(f"Created new premium user with email: {email}")
            print(f"Login credentials: {email} / premium123")

        # Check if user already has an active subscription
        existing_subscription = Subscription.query.filter_by(user_id=user.id, status="active").first()

        if existing_subscription:
            print(f"User already has an active {existing_subscription.plan_id} subscription")
        else:
            # Create a new subscription for the user
            subscription = Subscription(
                id=uuid.uuid4(),
                user_id=user.id,
                plan_id="premium",
                status="active",
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=365),  # 1 year subscription
                stripe_customer_id="manual_customer",
                stripe_subscription_id="manual_subscription",
                cancel_at_period_end=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.session.add(subscription)
            db.session.commit()
            print(f"Created new premium subscription for user: {email}")


if __name__ == "__main__":
    create_premium_user()
