"""Subscription and payment APIs."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from flask import Blueprint, current_app, g, jsonify, request, url_for

from app import db
from app.decorators import auth_required, token_required
from app.models import Subscription, User
from app.utils.stripe_helpers import PLAN_DETAILS
from app.utils.stripe_helpers import cancel_subscription
from app.utils.stripe_helpers import cancel_subscription as stripe_cancel_subscription
from app.utils.stripe_helpers import (
    create_checkout_session,
    create_stripe_customer,
    get_customer_payment_methods,
    get_stripe_customer,
    get_subscription_prices,
    handle_checkout_completed,
    handle_subscription_updated,
)

# Create Flask blueprint
payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/plans", methods=["GET"])
def get_plans():
    """Get available subscription plans."""
    plans = []
    for plan_id, details in PLAN_DETAILS.items():
        plan = {
            "id": plan_id,
            "name": details["name"],
            "description": details["description"],
            "features": details["features"],
            "price_monthly": details["price_monthly"],
            "price_yearly": details["price_yearly"],
            "currency": details["currency"],
            "popular": details.get("popular", False),
        }
        plans.append(plan)

    return jsonify(plans)


@payments_bp.route("/subscriptions", methods=["GET"])
@token_required
def get_subscriptions(current_user):
    """Get user's subscriptions."""
    subscriptions = [sub.to_dict() for sub in current_user.subscriptions]
    return jsonify(subscriptions)


@payments_bp.route("/subscriptions", methods=["POST"])
@token_required
def create_subscription(current_user):
    """Create a new subscription for the user."""
    data = request.json

    if not data or "plan_id" not in data:
        return jsonify({"error": "Missing required field: plan_id"}), 400

    plan_id = data["plan_id"]
    payment_provider = data.get("payment_provider", "stripe")
    payment_id = data.get("payment_id")  # For webhook reconciliation

    # Special case for free plan - we can create it directly
    if plan_id == "free":
        # Check if user already has this plan
        existing = Subscription.query.filter_by(user_id=current_user.id, plan_id=plan_id, status="active").first()

        if existing:
            return jsonify({"error": "User already has an active free plan"}), 400

        # Create the subscription
        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            plan_id=plan_id,
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
            cancel_at_period_end=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            # Set the payment ID as the stripe subscription ID if provided
            stripe_subscription_id=payment_id,
        )

        # Try to get or create a Stripe customer ID if possible
        try:
            if payment_provider == "stripe":
                # Try to create a Stripe customer for the user
                stripe_customer_id = create_stripe_customer(current_user)
                if stripe_customer_id:
                    subscription.stripe_customer_id = stripe_customer_id
        except Exception as e:
            current_app.logger.error(f"Error creating Stripe customer: {str(e)}")
            # Continue without the Stripe customer ID

        db.session.add(subscription)
        db.session.commit()

        return jsonify(subscription.to_dict()), 201

    # For paid plans, create a checkout session
    if payment_provider == "stripe":
        # Create a Stripe customer for the user if needed
        try:
            customer_id = create_stripe_customer(current_user)
            if not customer_id:
                return jsonify({"error": "Failed to create payment customer"}), 500
        except Exception as e:
            current_app.logger.error(f"Error creating Stripe customer: {str(e)}")
            return jsonify({"error": "Failed to create payment customer"}), 500

        # Create a checkout session
        success_url = return_url or url_for("api.payments.get_subscriptions", _external=True)
        cancel_url = return_url or url_for("api.payments.get_plans", _external=True)
        checkout_session_id = create_checkout_session(current_user, plan_id, success_url, cancel_url)
        checkout_url = f"https://checkout.stripe.com/pay/{checkout_session_id}"

        return (
            jsonify(
                {
                    "checkout_url": checkout_url,
                    "status": "pending_payment",
                    "message": "Please complete payment to activate subscription",
                }
            ),
            201,
        )

    return jsonify({"error": f"Unsupported payment provider: {payment_provider}"}), 400


@payments_bp.route("/subscriptions/<string:id>", methods=["GET"])
@token_required
def get_subscription(id, current_user):
    """Get details of a specific subscription."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404(
        description=f"Subscription {id} not found"
    )
    return jsonify(subscription.to_dict())


@payments_bp.route("/subscriptions/<string:id>", methods=["DELETE"])
@token_required
def cancel_subscription_endpoint(id, current_user):
    """Cancel a subscription."""
    subscription = Subscription.query.filter_by(id=id, user_id=current_user.id).first_or_404(
        description=f"Subscription {id} not found"
    )

    if subscription.status != "active":
        return jsonify({"error": "Cannot cancel a subscription that is not active"}), 400

    # For Stripe subscriptions, use the Stripe API
    if subscription.stripe_subscription_id:
        try:
            result = stripe_cancel_subscription(subscription.stripe_subscription_id)
            if result:
                # The webhook will update the subscription status
                return jsonify(
                    {
                        "id": id,
                        "status": "canceling",
                        "cancel_at_period_end": True,
                        "message": "Subscription will be canceled at the end of the billing period",
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error canceling Stripe subscription: {str(e)}")
            # Continue with direct cancellation

    # For other providers or subscriptions without stripe_subscription_id, cancel directly
    subscription.status = "canceled"
    subscription.cancel_at_period_end = True
    subscription.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(
        {"id": id, "status": "canceled", "cancel_at_period_end": True, "message": "Subscription has been canceled"}
    )


@payments_bp.route("/checkout", methods=["POST"])
@token_required
def create_checkout(current_user):
    """Create a checkout session for a subscription."""
    data = request.json

    if not data or "plan_id" not in data:
        return jsonify({"error": "Missing required field: plan_id"}), 400

    plan_id = data["plan_id"]
    return_url = data.get("return_url")

    # Create a Stripe customer for the user if needed
    try:
        customer_id = create_stripe_customer(current_user)
        if not customer_id:
            return jsonify({"error": "Failed to create payment customer"}), 500
    except Exception as e:
        current_app.logger.error(f"Error creating Stripe customer: {str(e)}")
        return jsonify({"error": "Failed to create payment customer"}), 500

    # Create a checkout session
    success_url = return_url or url_for("api.payments.get_subscriptions", _external=True)
    cancel_url = return_url or url_for("api.payments.get_plans", _external=True)
    checkout_session_id = create_checkout_session(current_user, plan_id, success_url, cancel_url)
    checkout_url = f"https://checkout.stripe.com/pay/{checkout_session_id}"

    return (
        jsonify(
            {
                "checkout_url": checkout_url,
                "status": "pending_payment",
                "message": "Please complete payment to activate subscription",
            }
        ),
        201,
    )


@payments_bp.route("/payment-methods", methods=["GET"])
@token_required
def list_payment_methods(current_user):
    """List user's payment methods."""
    try:
        payment_methods = get_customer_payment_methods(current_user)
        return jsonify(payment_methods)
    except Exception as e:
        current_app.logger.error(f"Error retrieving payment methods: {str(e)}")
        return jsonify([])


@payments_bp.route("/webhook", methods=["POST"])
def webhook():
    """Handle payment webhook events."""
    # Get the webhook payload and signature
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    # Process based on event type
    try:
        data = json.loads(payload)
        event_type = data.get("event_type", data.get("type"))

        current_app.logger.info(f"Processing payment webhook event: {event_type}")

        if not event_type:
            current_app.logger.error("No event type in webhook payload")
            return jsonify({"error": "Invalid webhook payload"}), 400

        # Handle different event types
        if event_type == "checkout.session.completed":
            handle_checkout_completed(data)
        elif event_type == "customer.subscription.created":
            # For subscription.created events, we handle this as part of the checkout.session.completed
            # Just log it for now
            current_app.logger.info(f"Received subscription created event: {data.get('id')}")
        elif event_type == "customer.subscription.updated":
            handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            # Handle subscription cancellation manually
            subscription_id = data.get("id")
            if subscription_id:
                subscription = Subscription.query.filter_by(stripe_subscription_id=subscription_id).first()
                if subscription:
                    subscription.status = "canceled"
                    subscription.updated_at = datetime.now(timezone.utc)
                    db.session.commit()
                    current_app.logger.info(f"Subscription {subscription_id} marked as canceled")
        else:
            current_app.logger.error(f"Unhandled webhook event type: {event_type}")

        return jsonify({"status": "success"})

    except Exception as e:
        current_app.logger.error(f"Error processing webhook: {str(e)}")
        current_app.logger.exception(e)
        return jsonify({"error": str(e)}), 400


@payments_bp.route("/prices", methods=["GET"])
def get_prices():
    """Get subscription prices."""
    try:
        prices = get_subscription_prices()
        return jsonify(prices)
    except Exception as e:
        current_app.logger.error(f"Error getting prices: {str(e)}")
        return jsonify({"error": str(e)}), 500
