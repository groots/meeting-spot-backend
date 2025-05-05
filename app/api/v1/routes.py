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
