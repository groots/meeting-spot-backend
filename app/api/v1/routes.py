from flask import Blueprint, current_app, jsonify, make_response, request
from sqlalchemy import text

from .. import db
from .meetings import api as meetings_api
from .places import api as places_api
from .subscriptions import api as subscriptions_api
from .users import api as users_api

v1_bp = Blueprint("v1", __name__, url_prefix="/v1")

# Import the API router from Flask-RESTX
from flask_restx import Api

api = Api(v1_bp, version="1.0", title="Find A Meeting Spot API", description="API for Find A Meeting Spot app")

# Add namespaces
api.add_namespace(users_api)
api.add_namespace(places_api)
api.add_namespace(meetings_api)
api.add_namespace(subscriptions_api)


# Add health check endpoint
@v1_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify API is up and running."""
    try:
        # Check database connection
        result = db.session.execute(text("SELECT 1")).fetchone()
        db_status = "ok" if result and result[0] == 1 else "error"

        return jsonify({"status": "ok", "version": "1.0", "database": db_status, "api": "Find A Meeting Spot API"}), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "version": "1.0",
                    "database": "error",
                    "error": str(e),
                    "api": "Find A Meeting Spot API",
                }
            ),
            500,
        )


# Add auth endpoints
@v1_bp.route("/auth/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    """Handle password reset request."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the main auth blueprint
    from ..auth import reset_password as auth_reset_password

    return auth_reset_password()


@v1_bp.route("/auth/me", methods=["GET", "OPTIONS"])
def get_current_user():
    """Get current user information directly without ORM models."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For GET requests, implement direct user lookup
    from flask_jwt_extended import get_jwt_identity, jwt_required

    @jwt_required()
    def get_user_by_id():
        try:
            current_user_id = get_jwt_identity()
            current_app.logger.info(f"Fetching user info for ID: {current_user_id}")

            # Direct SQL query to find user by ID
            stmt = text(
                """
                SELECT id, email, username, first_name, last_name, created_at, updated_at,
                       profile_picture_url, google_oauth_id, phone
                FROM users WHERE id = :user_id
            """
            )

            user_data = db.session.execute(stmt, {"user_id": current_user_id}).fetchone()

            if not user_data:
                current_app.logger.warning(f"User not found with ID: {current_user_id}")
                return jsonify({"error": "User not found"}), 404

            # Convert row to dictionary
            result = {}
            for idx, col in enumerate(user_data.keys()):
                result[col] = user_data[idx]

            # Check if user has premium subscription
            try:
                sub_stmt = text(
                    """
                    SELECT id, status, plan_type, current_period_end
                    FROM subscriptions
                    WHERE user_id = :user_id AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """
                )

                subscription = db.session.execute(sub_stmt, {"user_id": current_user_id}).fetchone()

                if subscription:
                    sub_dict = {}
                    for idx, col in enumerate(subscription.keys()):
                        sub_dict[col] = subscription[idx]

                    result["subscription"] = sub_dict
                    result["is_premium"] = True
                else:
                    result["is_premium"] = False

            except Exception as e:
                current_app.logger.error(f"Error fetching subscription: {str(e)}")
                result["is_premium"] = False

            return jsonify(result), 200

        except Exception as e:
            current_app.logger.error(f"Error in /auth/me endpoint: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    return get_user_by_id()
