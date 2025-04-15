"""Utility functions for interacting with Stripe."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import stripe
from flask import current_app, url_for

from .. import db
from ..models import Subscription, User

# Configure logger
logger = logging.getLogger(__name__)

# Define product and price IDs
PRODUCT_IDS = {"basic": "prod_basic", "premium": "prod_premium"}

PRICE_IDS = {
    "basic_monthly": "price_basic_monthly",
    "basic_yearly": "price_basic_yearly",
    "premium_monthly": "price_premium_monthly",
    "premium_yearly": "price_premium_yearly",
}

# Define plan details
PLAN_DETAILS = {
    "free": {
        "name": "Free",
        "description": "Basic features with limited usage",
        "price": 0,
        "interval": None,
        "features": ["Create up to 3 meeting requests per month", "Basic meeting locations", "Email notifications"],
    },
    "basic": {
        "name": "Basic",
        "description": "Enhanced features for casual users",
        "price": 4.99,
        "interval": "month",
        "features": [
            "Unlimited meeting requests",
            "Enhanced location recommendations",
            "Priority support",
            "SMS notifications",
        ],
    },
    "premium": {
        "name": "Premium",
        "description": "Pro features for power users",
        "price": 9.99,
        "interval": "month",
        "features": [
            "All Basic features",
            "Advanced location filtering",
            "Custom meeting preferences",
            "Team collaboration",
            "Priority support",
        ],
    },
}


def initialize_stripe():
    """Initialize the Stripe client with configuration."""
    stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
    return stripe


def create_stripe_customer(user):
    """Create a Stripe customer for the user if one doesn't exist."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    stripe_instance = initialize_stripe()
    customer = stripe_instance.Customer.create(email=user.email, metadata={"user_id": str(user.id)})

    # Update user with Stripe customer ID
    user.stripe_customer_id = customer.id
    db.session.commit()

    return customer.id


def get_subscription_by_stripe_id(stripe_subscription_id):
    """Get a subscription by its Stripe subscription ID."""
    return Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()


def create_subscription_record(user_id, stripe_subscription, stripe_customer_id):
    """Create a new subscription record from Stripe subscription data."""
    subscription = Subscription(
        user_id=user_id,
        stripe_subscription_id=stripe_subscription.id,
        stripe_customer_id=stripe_customer_id,
        plan_id=stripe_subscription.items.data[0].price.metadata.get("plan_id", "basic"),
        status=stripe_subscription.status,
        current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start, tz=timezone.utc),
        current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end, tz=timezone.utc),
        cancel_at_period_end=stripe_subscription.cancel_at_period_end,
    )

    db.session.add(subscription)
    db.session.commit()

    return subscription


def cancel_subscription(subscription_id):
    """Cancel a Stripe subscription."""
    stripe_instance = initialize_stripe()

    try:
        # Get the subscription
        subscription = Subscription.query.get(subscription_id)
        if not subscription or not subscription.stripe_subscription_id:
            return False, "Subscription not found"

        # Cancel at period end
        stripe_subscription = stripe_instance.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=True
        )

        # Update local subscription
        subscription.cancel_at_period_end = True
        subscription.status = "active"  # Stripe keeps it active until period end
        subscription.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        return True, "Subscription will be canceled at the end of the billing period"

    except Exception as e:
        current_app.logger.error(f"Error canceling subscription: {str(e)}")
        return False, str(e)


def handle_checkout_completed(session):
    """Handle a checkout.session.completed event."""
    stripe_instance = initialize_stripe()

    # Get the subscription from the session
    subscription_id = session.get("subscription")
    if not subscription_id:
        return False, "No subscription ID in session"

    # Get subscription details from Stripe
    stripe_subscription = stripe_instance.Subscription.retrieve(subscription_id)

    # Get user from metadata
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        return False, "No user ID in session metadata"

    # Create subscription record
    create_subscription_record(
        user_id=user_id, stripe_subscription=stripe_subscription, stripe_customer_id=session.get("customer")
    )

    return True, "Subscription created"


def handle_subscription_updated(subscription):
    """Handle a subscription.updated event."""
    # Find the local subscription
    local_subscription = get_subscription_by_stripe_id(subscription.id)
    if not local_subscription:
        return False, "Subscription not found"

    # Update with new values
    local_subscription.status = subscription.status
    local_subscription.current_period_start = datetime.fromtimestamp(subscription.current_period_start, tz=timezone.utc)
    local_subscription.current_period_end = datetime.fromtimestamp(subscription.current_period_end, tz=timezone.utc)
    local_subscription.cancel_at_period_end = subscription.cancel_at_period_end
    local_subscription.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    return True, "Subscription updated"


def get_stripe_customer(user: User) -> str:
    """
    Get a Stripe customer ID for a user.
    Creates one if the user doesn't have one.
    """
    stripe_instance = initialize_stripe()

    # If user already has a Stripe customer ID, return it
    if user.stripe_customer_id:
        return user.stripe_customer_id

    # Otherwise, create a new customer
    try:
        customer = stripe_instance.Customer.create(
            email=user.email,
            name=user.email.split("@")[0],  # Use part of email as name
            metadata={"user_id": str(user.id)},
        )

        # Update user with new Stripe customer ID
        user.stripe_customer_id = customer.id
        from .. import db

        db.session.commit()

        return customer.id
    except Exception as e:
        logger.error(f"Error creating Stripe customer: {e}")
        raise


def create_checkout_session(user: User, price_id: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout session for a subscription."""
    stripe_instance = initialize_stripe()
    customer_id = get_stripe_customer(user)

    try:
        # Create a new Checkout Session
        session = stripe_instance.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user.id),
            },
        )

        return session.id
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise


def get_subscription_prices() -> List[Dict[str, Any]]:
    """Get the list of subscription prices from Stripe."""
    stripe_instance = initialize_stripe()

    try:
        # List all active prices
        prices = stripe_instance.Price.list(active=True, limit=10, expand=["data.product"])

        # Transform the prices into a more usable format
        price_list = []
        for price in prices.data:
            product = price.get("product", {})
            if isinstance(product, str):
                # If product is just an ID, fetch the product details
                product = stripe_instance.Product.retrieve(product)

            price_data = {
                "id": price.id,
                "product_id": product.id,
                "name": product.name,
                "description": product.get("description", ""),
                "amount": price.unit_amount / 100,  # Convert cents to dollars
                "currency": price.currency,
                "interval": price.get("recurring", {}).get("interval", ""),
                "interval_count": price.get("recurring", {}).get("interval_count", 1),
            }
            price_list.append(price_data)

        return price_list
    except Exception as e:
        logger.error(f"Error retrieving subscription prices: {e}")
        return []


def get_customer_payment_methods(user: User) -> List[Dict[str, Any]]:
    """Get the payment methods for a customer."""
    stripe_instance = initialize_stripe()

    if not user.stripe_customer_id:
        return []

    try:
        payment_methods = stripe_instance.PaymentMethod.list(customer=user.stripe_customer_id, type="card")

        # Transform into a more usable format
        methods = []
        for method in payment_methods.data:
            card = method.get("card", {})
            methods.append(
                {
                    "id": method.id,
                    "brand": card.get("brand", ""),
                    "last4": card.get("last4", ""),
                    "exp_month": card.get("exp_month", 0),
                    "exp_year": card.get("exp_year", 0),
                    "is_default": method.metadata.get("is_default", False) if method.metadata else False,
                }
            )

        return methods
    except Exception as e:
        logger.error(f"Error retrieving payment methods: {e}")
        return []


def is_premium_feature(feature_name: str) -> bool:
    """Check if a feature requires a premium subscription."""
    premium_features = {
        "advanced_filtering": True,
        "unlimited_requests": True,
        "team_collaboration": True,
        "priority_support": True,
        "custom_preferences": True,
        "sms_notifications": True,
        "contacts": True,
        "analytics": True,
        "export": True,
        "templates": True,
        "team_access": True,
    }

    return premium_features.get(feature_name, False)
