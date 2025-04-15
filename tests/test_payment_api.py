import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models import Subscription, User


@pytest.mark.usefixtures("client", "db_session")
class TestPaymentApi:
    """Test class for payment API endpoints."""

    def test_get_subscriptions_unauthorized(self, client):
        """Test that unauthorized users cannot access subscriptions."""
        response = client.get("/api/v1/payments/subscriptions")
        assert response.status_code == 401

    def test_create_subscription_unauthorized(self, client):
        """Test that unauthorized users cannot create subscriptions."""
        response = client.post(
            "/api/v1/payments/subscriptions",
            json={"plan_id": "basic", "payment_provider": "stripe"},
        )
        assert response.status_code == 401

    def test_get_subscriptions(self, client, db_session, test_user, auth_headers):
        """Test retrieving user subscriptions."""
        # Create a subscription for the test user
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            plan_id="basic",
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            cancel_at_period_end=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(subscription)
        db_session.commit()

        # Get subscriptions
        response = client.get("/api/v1/payments/subscriptions", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["plan_id"] == "basic"
        assert data[0]["status"] == "active"

    def test_create_subscription(self, client, db_session, test_user, auth_headers):
        """Test creating a new subscription."""
        response = client.post(
            "/api/v1/payments/subscriptions",
            json={"plan_id": "premium", "payment_provider": "stripe", "payment_id": "test_payment"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["plan_id"] == "premium"
        assert data["status"] == "active"

        # Check that it was saved to the database
        subscription = Subscription.query.filter_by(user_id=test_user.id).first()
        assert subscription is not None
        assert subscription.plan_id == "premium"

        # Check that the user's subscription info was updated
        user = User.query.get(test_user.id)
        assert user.subscription_plan == "premium"
        assert user.subscription_status == "active"

    def test_cancel_subscription(self, client, db_session, test_user, auth_headers):
        """Test canceling a subscription."""
        # Create a subscription for the test user
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            plan_id="basic",
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            cancel_at_period_end=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(subscription)
        db_session.commit()

        # Cancel the subscription
        response = client.delete(f"/api/v1/payments/subscriptions/{subscription.id}", headers=auth_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "canceled"
        assert data["cancel_at_period_end"] is True

        # Check that it was updated in the database
        updated_sub = Subscription.query.get(subscription.id)
        assert updated_sub.status == "canceled"
        assert updated_sub.cancel_at_period_end is True

        # Check that the user's subscription status was updated
        user = User.query.get(test_user.id)
        assert user.subscription_status == "canceled"

    def test_webhook_handler(self, client):
        """Test the payment webhook handler."""
        with patch("app.api.payments.current_app.logger.info") as mock_logger:
            response = client.post(
                "/api/v1/payments/webhook",
                json={
                    "event_type": "payment.succeeded",
                    "payment_id": "test_payment_id",
                    "data": {"customer": "test_customer"},
                },
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["message"] == "Webhook received"

            # Verify logger was called
            mock_logger.assert_called_once()
