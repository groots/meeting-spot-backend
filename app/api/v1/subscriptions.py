from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource

from app.models.user import User

api = Namespace("subscriptions", description="Subscription operations")


@api.route("/my-subscription")
class MySubscription(Resource):
    """Endpoint for retrieving the current user's subscription information"""

    @jwt_required()
    def get(self):
        """Get current user's subscription details."""
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)

        if not user:
            return {"message": "User not found"}, 404

        # Get subscription information from the user
        subscription_data = {
            "subscription_plan": user.subscription_plan,
            "subscription_status": user.subscription_status,
            "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            "is_premium": user.is_premium(),
        }

        # Get detailed subscription information if available
        if hasattr(user, "subscriptions") and user.subscriptions:
            subscription = user.subscriptions[0]  # Get the first subscription
            subscription_data.update(
                {
                    "id": str(subscription.id),
                    "plan_id": subscription.plan_id,
                    "status": subscription.status,
                    "current_period_start": subscription.current_period_start.isoformat()
                    if subscription.current_period_start
                    else None,
                    "current_period_end": subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                }
            )

        return {"subscription": subscription_data}, 200


@api.route("/upgrade")
class UpgradeSubscription(Resource):
    """Endpoint for initiating a subscription upgrade"""

    @jwt_required()
    def post(self):
        """Initiate a subscription upgrade."""
        user_id = get_jwt_identity()
        user = User.get_by_token_identity(user_id)

        if not user:
            return {"message": "User not found"}, 404

        # For now just return a placeholder response
        # In a real implementation, this would initiate a payment flow
        return {
            "message": "Upgrade initiated",
            "checkout_url": "https://example.com/checkout",
        }, 200
