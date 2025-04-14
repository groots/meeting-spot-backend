"""CORS Middleware for Flask application.

This module provides a simple, reliable approach to handling CORS in Cloud Run.
"""

import logging

from flask import current_app, request


def setup_cors(app):
    """Set up CORS for the Flask application using a direct approach that works reliably in Cloud Run.

    This implementation adds explicit CORS headers to all responses rather than relying on flask-cors,
    which can sometimes be stripped by Cloud Run.

    Args:
        app: The Flask application instance
    """
    cors_logger = logging.getLogger("cors")

    # Create a list of default allowed origins if not specified
    if not app.config.get("CORS_ORIGINS"):
        app.config["CORS_ORIGINS"] = [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5000",
            "http://localhost:5001",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8081",
            "https://find-a-meeting-spot.web.app",
            "https://find-a-meeting-spot.firebaseapp.com",
            "https://find-a-meeting-spot.ue.r.appspot.com",
            "https://findameetingspot.com",
            "https://www.findameetingspot.com",
        ]

    cors_logger.info(f"Initializing CORS with allowed origins: {app.config['CORS_ORIGINS']}")

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to all responses."""
        origin = request.headers.get("Origin")

        # Log the request for debugging
        cors_logger.info(f"Processing request: {request.method} {request.path} from origin: {origin}")

        # Only add CORS headers if the origin is provided
        if origin:
            # Check if origin is in our allowed origins list
            allowed_origins = app.config.get("CORS_ORIGINS", [])

            # Only add Access-Control-Allow-Origin if the origin is allowed
            if "*" in allowed_origins or origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers[
                    "Access-Control-Allow-Headers"
                ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "3600"
                response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"
                cors_logger.info(f"Applied CORS headers for origin: {origin}")
            else:
                cors_logger.info(f"Origin not allowed: {origin}")

        return response

    @app.route("/<path:path>", methods=["OPTIONS"])
    @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
    def handle_options(path=""):
        """Handle OPTIONS requests explicitly.
        This is often required for Cloud Run to properly handle preflight requests.
        """
        origin = request.headers.get("Origin")
        cors_logger.info(f"Handling OPTIONS request for path: {path} from origin: {origin}")

        # Create a response with 200 OK status
        response = current_app.make_default_options_response()

        # Add CORS headers only if the origin is allowed
        if origin:
            allowed_origins = app.config.get("CORS_ORIGINS", [])

            if "*" in allowed_origins or origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers[
                    "Access-Control-Allow-Headers"
                ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "3600"
                response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"
                cors_logger.info(f"Applied OPTIONS CORS headers for origin: {origin}")
            else:
                cors_logger.info(f"Origin not allowed for OPTIONS: {origin}")

        return response
