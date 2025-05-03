"""Subscription and payment APIs."""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from flask import Blueprint, current_app, g, jsonify, request, url_for
from flask_restx import Namespace, Resource, fields
from sqlalchemy import text

from .. import db
from ..decorators import auth_required, token_required
from ..models import Subscription, User
from ..utils.stripe_helpers import PLAN_DETAILS
from ..utils.stripe_helpers import cancel_subscription
from ..utils.stripe_helpers import cancel_subscription as stripe_cancel_subscription
from ..utils.stripe_helpers import (
    create_checkout_session,
    create_stripe_customer,
    get_customer_payment_methods,
    get_stripe_customer,
    get_subscription_prices,
    handle_checkout_completed,
    handle_subscription_updated,
    initialize_stripe,
    is_premium_feature,
)

# Configure logger
logger = logging.getLogger(__name__)

# Create Flask blueprint
payments_bp = Blueprint("payments", __name__)

# Create API namespace
api = Namespace("payments", description="Subscription and payment operations")

# Request and response models
plan_model = api.model(
    "Plan",
    {
        "id": fields.String(required=True, description="Plan ID"),
        "name": fields.String(required=True, description="Plan name"),
        "description": fields.String(required=True, description="Plan description"),
        "price": fields.Float(required=True, description="Plan price"),
        "interval": fields.String(required=False, description="Billing interval"),
        "features": fields.List(fields.String, description="List of features"),
    },
)

subscription_model = api.model(
    "Subscription",
    {
        "id": fields.String(description="The subscription identifier"),
        "user_id": fields.String(description="The user identifier"),
        "plan_id": fields.String(description="Subscription plan type"),
        "status": fields.String(description="Subscription status"),
        "current_period_start": fields.DateTime(description="Start date of subscription"),
        "current_period_end": fields.DateTime(description="End date of subscription"),
        "cancel_at_period_end": fields.Boolean(description="Whether subscription will cancel at end of period"),
        "created_at": fields.DateTime(description="Creation timestamp"),
        "updated_at": fields.DateTime(description="Last update timestamp"),
    },
)

checkout_model = api.model(
    "CheckoutSession",
    {
        "price_id": fields.String(required=True, description="Stripe Price ID"),
        "success_url": fields.String(required=True, description="URL to redirect after successful payment"),
        "cancel_url": fields.String(required=True, description="URL to redirect after canceled payment"),
    },
)

checkout_response = api.model(
    "CheckoutResponse",
    {
        "checkout_url": fields.String(required=True, description="URL for Stripe Checkout"),
        "session_id": fields.String(required=True, description="Stripe Checkout Session ID"),
    },
)

payment_method_model = api.model(
    "PaymentMethod",
    {
        "id": fields.String(required=True, description="Payment method ID"),
        "brand": fields.String(required=True, description="Card brand"),
        "last4": fields.String(required=True, description="Last 4 digits of card"),
        "exp_month": fields.Integer(required=True, description="Expiration month"),
        "exp_year": fields.Integer(required=True, description="Expiration year"),
        "is_default": fields.Boolean(required=True, description="Whether this is the default payment method"),
    },
)

webhook_response = api.model(
    "WebhookResponse",
    {
        "received": fields.Boolean(required=True, description="Whether webhook was received successfully"),
        "type": fields.String(required=False, description="Type of webhook event"),
    },
)

create_subscription_model = api.model(
    "CreateSubscription",
    {
        "plan_id": fields.String(required=True, description="Subscription plan type"),
        "payment_provider": fields.String(required=True, description="Payment provider"),
        "payment_id": fields.String(description="Payment ID from provider"),
    },
)

payment_webhook_model = api.model(
    "PaymentWebhook",
    {
        "event_type": fields.String(required=True, description="Event type from payment provider"),
        "payment_id": fields.String(required=True, description="Payment ID from provider"),
        "data": fields.Raw(description="Event data from provider"),
    },
)


@api.route("/plans")
class PlanList(Resource):
    """Resource for retrieving available subscription plans."""

    @api.doc("list_plans")
    @api.marshal_list_with(plan_model)
    def get(self):
        """Get all available subscription plans."""
        # Return the plan details from stripe_helpers
        return [{"id": plan_id, **details} for plan_id, details in PLAN_DETAILS.items()]


@api.route("/subscriptions")
class SubscriptionsList(Resource):
    @api.doc("list_subscriptions")
    @token_required
    def get(self, current_user):
        """Get current user's subscriptions"""
        try:
            # Check if user is authenticated
            try:
                current_user_id = current_user.id
                current_app.logger.info(f"Getting subscriptions for user {current_user_id}")

                try:
                    # First try the ORM approach
                    subscriptions = Subscription.query.filter_by(user_id=current_user_id).all()
                    return [sub.to_dict() for sub in subscriptions]

                except Exception as e:
                    # Check if this is the facebook_oauth_id error
                    error_str = str(e).lower()
                    current_app.logger.warning(f"Database error occurred: {error_str}")

                    # Use a more generic check for the column error
                    if "column" in error_str and "facebook_oauth_id" in error_str:
                        current_app.logger.info("Falling back to direct SQL due to facebook_oauth_id column issue")

                        # Use direct SQL to avoid the ORM issue
                        sql = text(
                            """
                            SELECT id, user_id, plan_id, stripe_subscription_id, stripe_customer_id,
                                   status, current_period_start, current_period_end,
                                   cancel_at_period_end, created_at, updated_at
                            FROM subscription
                            WHERE user_id = :user_id
                        """
                        )

                        with db.engine.connect() as conn:
                            result = conn.execute(sql, {"user_id": current_user_id})
                            subscriptions = []

                            for row in result:
                                sub = {
                                    "id": str(row[0]),
                                    "user_id": str(row[1]),
                                    "plan_id": row[2],
                                    "stripe_subscription_id": row[3],
                                    "stripe_customer_id": row[4],
                                    "status": row[5],
                                    "current_period_start": row[6].isoformat() if row[6] else None,
                                    "current_period_end": row[7].isoformat() if row[7] else None,
                                    "cancel_at_period_end": bool(row[8]),
                                    "created_at": row[9].isoformat() if row[9] else None,
                                    "updated_at": row[10].isoformat() if row[10] else None,
                                }
                                subscriptions.append(sub)

                        current_app.logger.info(f"Found {len(subscriptions)} subscriptions via direct SQL")
                        return subscriptions
                    else:
                        # Log the actual error for debugging
                        current_app.logger.error(f"Database error in subscriptions endpoint: {error_str}")
                        raise

            except Exception as e:
                current_app.logger.error(f"Error fetching subscriptions: {str(e)}")
                return {"error": "Error fetching subscriptions", "message": str(e)}, 500

        except Exception as e:
            current_app.logger.error(f"Unexpected error in subscription list endpoint: {str(e)}")
            return {"error": "Authentication error", "message": str(e)}, 401

    @api.doc("create_subscription")
    @api.expect(create_subscription_model)
    @api.marshal_with(subscription_model, code=201)
    @token_required
    def post(self, current_user):
        """Create a new subscription (direct creation without payment)"""
        # This endpoint should only be used for free plans or testing
        data = request.json

        if data["plan_id"] != "free":
            return {"message": "For paid plans, use the /checkout endpoint"}, 400

        # Check if user already has an active subscription
        active_sub = Subscription.query.filter_by(user_id=current_user.id, status="active").first()

        if active_sub:
            # End current subscription
            active_sub.status = "canceled"
            active_sub.updated_at = datetime.now(timezone.utc)
            active_sub.cancel_at_period_end = True

        # Create new subscription
        new_subscription = Subscription(
            user_id=current_user.id,
            plan_id=data["plan_id"],
            status="active",
            stripe_subscription_id=data.get("payment_id"),
            stripe_customer_id=data.get("payment_provider"),
            current_period_start=datetime.now(timezone.utc),
            current_period_end=None,  # Free plan has no end date
            cancel_at_period_end=False,
        )

        db.session.add(new_subscription)
        db.session.commit()

        return new_subscription.to_dict(), 201


@api.route("/subscriptions/<string:id>")
@api.param("id", "The subscription identifier")
class SubscriptionResource(Resource):
    @api.doc("get_subscription")
    @api.marshal_with(subscription_model)
    @token_required
    def get(self, id, current_user):
        """Get a specific subscription"""
        try:
            uuid_obj = uuid.UUID(id)
        except ValueError:
            api.abort(400, "Invalid subscription ID format")

        subscription = Subscription.query.filter_by(id=uuid_obj, user_id=current_user.id).first_or_404(
            description=f"Subscription {id} not found"
        )
        return subscription.to_dict()

    @api.doc("cancel_subscription")
    @api.marshal_with(subscription_model)
    @token_required
    def delete(self, id, current_user):
        """Cancel a subscription"""
        try:
            uuid_obj = uuid.UUID(id)
        except ValueError:
            api.abort(400, "Invalid subscription ID format")

        subscription = Subscription.query.filter_by(id=uuid_obj, user_id=current_user.id).first_or_404(
            description=f"Subscription {id} not found"
        )

        if subscription.status != "active":
            api.abort(400, "Only active subscriptions can be canceled")

        # If it's a Stripe subscription, cancel via Stripe
        if subscription.stripe_subscription_id:
            success, message = stripe_cancel_subscription(subscription.id)
            if not success:
                api.abort(400, message)
        else:
            # For free or test subscriptions, just update the status
            subscription.status = "canceled"
            subscription.cancel_at_period_end = True
            subscription.updated_at = datetime.now(timezone.utc)
            db.session.commit()

        return subscription.to_dict()


@api.route("/checkout")
class CheckoutResource(Resource):
    @api.doc("create_checkout_session")
    @api.expect(checkout_model)
    @token_required
    def post(self, current_user):
        """Create a Stripe checkout session"""
        data = request.json
        stripe = initialize_stripe()

        try:
            # Ensure user has a Stripe customer ID
            customer_id = create_stripe_customer(current_user)

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": data.get("price_id"),
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=data.get("success_url"),
                cancel_url=data.get("cancel_url"),
                metadata={"user_id": str(current_user.id)},
            )

            return {"checkout_url": checkout_session.url}, 200

        except Exception as e:
            current_app.logger.error(f"Stripe error: {str(e)}")
            return {"error": str(e)}, 400


@api.route("/payment-methods")
class PaymentMethodsResource(Resource):
    """Resource for managing payment methods."""

    @api.doc("get_payment_methods")
    @auth_required
    @api.marshal_list_with(payment_method_model)
    def get(self):
        """Get user's payment methods."""
        user = g.current_user

        # Get payment methods from Stripe
        payment_methods = get_customer_payment_methods(user)

        return payment_methods


@api.route("/webhook")
class PaymentWebhook(Resource):
    @api.doc("payment_webhook")
    def post(self):
        """Handle Stripe webhook events."""
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature")

        if not sig_header:
            current_app.logger.warning("No Stripe signature header")
            return {"received": False}, 400

        stripe = initialize_stripe()

        try:
            # Verify the event with Stripe
            webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

            # Handle different event types
            event_type = event["type"]
            data = event["data"]["object"]

            if event_type == "checkout.session.completed":
                handle_checkout_completed(data)
            elif event_type in ["subscription.created", "subscription.updated"]:
                handle_subscription_updated(data)
            # Add other event types as needed

            return {"received": True, "type": event_type}
        except stripe.error.SignatureVerificationError:
            current_app.logger.error("Invalid Stripe signature")
            return {"error": "Invalid signature"}, 400
        except Exception as e:
            current_app.logger.error(f"Error handling webhook: {e}")
            return {"error": str(e)}, 400


@api.route("/prices")
class PriceResource(Resource):
    """Resource for retrieving Stripe prices."""

    @api.doc("get_prices")
    def get(self):
        """Get all available subscription prices from Stripe."""
        prices = get_subscription_prices()
        return jsonify(prices)


# OPTIONS route classes for CORS support
@api.route("/plans", doc=False)
class PlansOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the plans endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/subscriptions", doc=False)
class SubscriptionsOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the subscriptions endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/subscriptions/<string:id>", doc=False)
class SubscriptionIdOptions(Resource):
    def options(self, id):
        """Handle OPTIONS requests for the subscription ID endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/checkout", doc=False)
class CheckoutOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the checkout endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/payment-methods", doc=False)
class PaymentMethodsOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the payment methods endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/webhook", doc=False)
class WebhookOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the webhook endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Stripe-Signature"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


@api.route("/prices", doc=False)
class PricesOptions(Resource):
    def options(self):
        """Handle OPTIONS requests for the prices endpoint."""
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
