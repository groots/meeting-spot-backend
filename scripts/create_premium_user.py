#!/usr/bin/env python3

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import create_app, db
from app.models.user import User


def create_premium_user():
    """Create or update a premium user for testing purposes"""
    app = create_app()
    with app.app_context():
        email = "premium@example.com"
        password = "premium123"

        # First see if we can get a user object without querying all fields
        connection = db.session.connection()
        result = connection.execute(text(f"SELECT id FROM users WHERE email = '{email}'")).fetchone()

        if not result:
            # Create new user with direct SQL to avoid ORM issues
            user_id = uuid.uuid4()
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                text(
                    f"""
                INSERT INTO users
                (id, email, created_at, updated_at, subscription_plan, subscription_status, subscription_end_date)
                VALUES
                ('{user_id}', '{email}', '{now}', '{now}', 'premium', 'active', '{(datetime.now(timezone.utc) + timedelta(days=365)).isoformat()}')
                """
                )
            )

            # Set password with a separate query
            user = User.query.get(user_id)
            user.set_password(password)
            db.session.commit()

            print(f"Premium user created: {email}, ID: {user_id}")
        else:
            # Update existing user
            user_id = result[0]
            end_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            connection.execute(
                text(
                    f"""
                UPDATE users
                SET subscription_plan = 'premium',
                    subscription_status = 'active',
                    subscription_end_date = '{end_date}'
                WHERE id = '{user_id}'
                """
                )
            )

            # Set password with a separate query
            user = User.query.get(user_id)
            user.set_password(password)
            db.session.commit()

            print(f"Premium user updated: {email}, ID: {user_id}")

        print(f"Login credentials: {email} / {password}")


if __name__ == "__main__":
    create_premium_user()
