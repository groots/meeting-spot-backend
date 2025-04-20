import json
from unittest.mock import patch

import pytest
from flask import url_for
from flask_jwt_extended import decode_token

from app import db
from app.models.user import User


def test_login_success(client, test_user):
    """Test successful login with correct credentials."""
    # Given a user that exists
    user, password = test_user

    # When login is attempted with correct credentials
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )

    # Then it should succeed
    assert response.status_code == 200
    assert "access_token" in response.json
    assert "user" in response.json

    # And token should be valid and contain user id
    token = response.json["access_token"]
    decoded = decode_token(token)
    assert decoded["sub"] == str(user.id)


def test_login_invalid_credentials(client, test_user):
    """Test login with invalid credentials."""
    # Given a user that exists
    user, _ = test_user

    # When login is attempted with incorrect password
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "wrong_password"},
    )

    # Then it should fail
    assert response.status_code == 401
    assert "Invalid credentials" in response.json.get("error", "")


def test_login_missing_fields(client):
    """Test login with missing fields."""
    # When login is attempted without required fields
    response = client.post(
        "/api/v1/auth/login",
        json={},
    )

    # Then it should fail
    assert response.status_code == 400
    assert "Email and password are required" in response.json.get("message", "")


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    # When login is attempted with nonexistent user
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password"},
    )

    # Then it should fail
    assert response.status_code == 401
    assert "Invalid credentials" in response.json.get("error", "")


def test_login_with_premium_user(client, test_user, db_session):
    """Test login with premium user returns subscription info."""
    # Given a user with an active subscription
    user, password = test_user

    # Create a mock subscription for the user
    from datetime import datetime, timedelta, timezone

    from app.models.subscription import Subscription

    subscription = Subscription(
        user_id=user.id,
        plan_id="test_premium",
        stripe_subscription_id="sub_test123",
        stripe_customer_id="cus_test123",
        status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(subscription)
    db_session.commit()

    # When the user logs in
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )

    # Then it should return premium status
    assert response.status_code == 200
    assert response.json["user"].get("is_premium") is True
    assert "subscription" in response.json["user"]
    assert response.json["user"]["subscription"].get("plan_id") == "test_premium"


@pytest.fixture
def test_user(app_context, db_session):
    """Create a test user with known password."""
    from werkzeug.security import generate_password_hash

    # Create a test user with known credentials
    email = "auth_test@example.com"
    password = "TestPassword123!"
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
    )

    db_session.add(user)
    db_session.commit()

    yield user, password

    # Clean up
    db_session.delete(user)
    db_session.commit()
