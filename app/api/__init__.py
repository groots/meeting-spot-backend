"""API blueprints for the application."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import psutil
from flask import Blueprint, current_app, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from sqlalchemy import text
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


@debug_bp.route("/health")
def health_check():
    """Comprehensive health check endpoint."""
    health_data = {
        "status": "initializing",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": current_app.config.get("ENV", "unknown"),
        "debug_mode": current_app.debug,
        "components": {},
    }

    # Check database connectivity
    try:
        # Simple query to check database connection
        db_version = db.session.execute(text("SELECT version()")).scalar()
        health_data["components"]["database"] = {
            "status": "healthy",
            "version": db_version,
            "uri": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                # Mask password in the returned URL for security
                ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                ":*****@",
            )
            if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
            else "Not set",
        }
    except SQLAlchemyError as e:
        health_data["components"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Check system resources
    try:
        health_data["components"]["system"] = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
        }
    except Exception as e:
        health_data["components"]["system"] = {"status": "error", "error": str(e)}

    # Check configuration
    health_data["components"]["configuration"] = {
        "cors_origins": current_app.config.get("CORS_ORIGINS"),
        "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
        "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
        "jwt_secret_key_set": bool(current_app.config.get("JWT_SECRET_KEY")),
        "security_headers": bool(current_app.config.get("SECURITY_HEADERS")),
    }

    # Check CORS configuration
    health_data["components"]["cors"] = {
        "enabled": True,
        "allowed_origins": current_app.config.get("CORS_ORIGINS"),
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_credentials": True,
        "max_age": 3600,
    }

    # Determine overall status
    if all(
        comp.get("status", "healthy") == "healthy"
        for comp in health_data["components"].values()
        if isinstance(comp, dict) and "status" in comp
    ):
        health_data["status"] = "healthy"
    else:
        health_data["status"] = "degraded"

    response = jsonify(health_data)

    # Add CORS headers directly to this response
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            current_app.logger.info(f"Added direct CORS headers to health endpoint response for origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for health endpoint: {origin}")

    return response


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
        db_version = db.session.execute(text("SELECT version()")).scalar()
        response = jsonify(
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

        # Add CORS headers directly to this response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            current_app.logger.info(f"Added direct CORS headers to db-check response for origin: {origin}")

        return response
    except SQLAlchemyError as e:
        error_response = (
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

        # Add CORS headers to error response too
        origin = request.headers.get("Origin")
        if origin:
            error_response[0].headers["Access-Control-Allow-Origin"] = origin
            error_response[0].headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            error_response[0].headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            error_response[0].headers["Access-Control-Allow-Credentials"] = "true"

        return error_response


@debug_bp.route("/db-check", methods=["OPTIONS"])
def db_check_options():
    """Handle OPTIONS requests for db-check endpoint."""
    response = current_app.make_default_options_response()
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            current_app.logger.info(f"Added CORS headers to OPTIONS response for /debug/db-check, origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for db-check OPTIONS: {origin}")
    return response


@debug_bp.route("/health", methods=["OPTIONS"])
def health_options():
    """Handle OPTIONS requests for health endpoint."""
    response = current_app.make_default_options_response()
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            current_app.logger.info(f"Added CORS headers to OPTIONS response for /debug/health, origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for health OPTIONS: {origin}")
    return response


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
