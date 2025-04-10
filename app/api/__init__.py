"""API blueprints for the application."""

import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from sqlalchemy.exc import SQLAlchemyError

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus
from ..utils.notifications import send_email
from .auth import api as auth_ns
from .meeting_requests import api as meeting_requests_ns
from .users import api as users_ns
from .v1.cors import cors_ns

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Create API v2 blueprint
api_v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# Create a limiter instance
limiter = Limiter(key_func=get_remote_address)

# Create debug blueprint
debug_bp = Blueprint("debug", __name__, url_prefix="/debug")


# Add a test route directly to the blueprint
@api_v1_bp.route("/test/")
def test_route():
    return jsonify({"message": "API v1 test route working"})


# Add an email test route
@debug_bp.route("/test-email")
def test_email():
    try:
        result = send_email(
            "squish.roots@gmail.com",
            "Test Email from Find A Meeting Spot",
            "This is a test email sent from the development environment using Mailgun with mg.findameetingspot.com domain.",
        )
        if result:
            return jsonify({"message": "Email sent successfully"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Create API v1 instance
api_v1 = Api(
    api_v1_bp,
    version="1.0",
    title="Find a Meeting Spot API v1",
    description="API v1 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Create API v2 instance
api_v2 = Api(
    api_v2_bp,
    version="2.0",
    title="Find a Meeting Spot API v2",
    description="API v2 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Register namespaces for v1
api_v1.add_namespace(auth_ns, path="/auth")
api_v1.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v1.add_namespace(users_ns, path="/users")
api_v1.add_namespace(cors_ns, path="/cors")

# Register namespaces for v2
api_v2.add_namespace(auth_ns, path="/auth")
api_v2.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v2.add_namespace(users_ns, path="/users")

# No need to import routes since we're using Flask-RESTX namespaces


@debug_bp.route("/db-check")
def db_check():
    """Check database connectivity."""
    try:
        # Attempt to execute a simple query
        db_version = db.session.execute("SELECT version()").scalar()
        return jsonify(
            {
                "status": "success",
                "message": "Database connection successful",
                "db_version": db_version,
                "database_url": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                    # Mask password in the returned URL for security
                    ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                    ":*****@",
                )
                if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
                else current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set"),
                "flask_env": current_app.config.get("ENV", "Not set"),
                "debug_mode": current_app.debug,
                "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
                "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
            }
        )
    except SQLAlchemyError as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Database connection failed",
                    "error": str(e),
                    "database_url": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                        # Mask password in the returned URL for security
                        ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                        ":*****@",
                    )
                    if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
                    else current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set"),
                    "flask_env": current_app.config.get("ENV", "Not set"),
                    "debug_mode": current_app.debug,
                    "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
                    "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
                }
            ),
            500,
        )


# Register debug blueprint with the app
def init_app(app):
    """Initialize API blueprints with the Flask app."""
    # Set up rate limiting
    limiter.init_app(app)

    # Register API blueprints
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_v2_bp)

    # Register debug endpoints
    app.register_blueprint(debug_bp)

    return app
