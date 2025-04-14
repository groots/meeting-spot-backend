"""CORS Middleware for Flask application.

This module provides functions to add CORS headers to all responses.
"""

from flask import Flask, current_app, request


def setup_cors(app):
    """Set up CORS for the Flask application.

    This adds proper CORS headers to all responses and handles OPTIONS requests.

    Args:
        app: The Flask application instance
    """

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to all responses."""
        # Get the origin from the request
        origin = request.headers.get("Origin")

        # If origin is present AND in allowed origins, set CORS headers
        if origin and origin in current_app.config.get("CORS_ORIGINS", ["http://localhost:3000"]):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"

        return response

    @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
    @app.route("/<path:path>", methods=["OPTIONS"])
    def handle_options_requests(path):
        """Handle OPTIONS requests for all routes."""
        return "", 200
