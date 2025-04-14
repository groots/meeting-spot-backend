"""CORS Middleware for Flask application.

This module provides functions to add CORS headers to all responses.
"""

import logging

from flask import Flask, current_app, request


def setup_cors(app):
    """Set up CORS for the Flask application.

    This adds proper CORS headers to all responses and handles OPTIONS requests.

    Args:
        app: The Flask application instance
    """
    cors_logger = logging.getLogger("cors")

    @app.after_request
    def add_cors_headers(response):
        """Add CORS headers to all responses."""
        # Get the origin from the request
        origin = request.headers.get("Origin")

        # Log the origin for debugging
        if origin:
            cors_logger.info(f"Processing request with Origin: {origin}")

        # SPECIAL CASE 1: Always allow CORS for debug endpoints
        if origin and request.path.startswith("/debug/"):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"
            cors_logger.info(f"Applied permissive CORS headers for debug endpoint: {request.path}")
            return response

        # SPECIAL CASE 2: Always allow CORS for API endpoints in development
        elif origin and request.path.startswith("/api/") and app.config.get("DEBUG", False):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"
            cors_logger.info(f"Applied permissive CORS headers for API in development: {request.path}")
            return response

        # For other endpoints, only allow from permitted origins
        elif origin:
            allowed_origins = current_app.config.get("CORS_ORIGINS", ["http://localhost:3000"])

            # Check if origin is in allowed origins or if wildcard is allowed
            if origin in allowed_origins or "*" in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers[
                    "Access-Control-Allow-Headers"
                ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "3600"
                response.headers["Access-Control-Expose-Headers"] = "Content-Type, Authorization, Content-Length"
                cors_logger.info(f"Applied CORS headers for permitted origin: {origin}")
            else:
                cors_logger.warning(f"CORS request denied for origin: {origin}, path: {request.path}")
                cors_logger.warning(f"Allowed origins: {allowed_origins}")

        return response

    @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
    @app.route("/<path:path>", methods=["OPTIONS"])
    def handle_options_requests(path):
        """Handle OPTIONS requests for all routes."""
        origin = request.headers.get("Origin")
        resp = current_app.make_default_options_response()

        # Log the OPTIONS request
        cors_logger.info(f"Handling OPTIONS request for path: {path}, origin: {origin}")

        # Always allow OPTIONS for debug endpoints
        if path.startswith("debug/") and origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            resp.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Max-Age"] = "3600"
            cors_logger.info(f"Applied CORS headers for OPTIONS to debug endpoint: {path}")
        # Special case for API endpoints in development
        elif path.startswith("api/") and origin and current_app.config.get("DEBUG", False):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            resp.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Max-Age"] = "3600"
            cors_logger.info(f"Applied CORS headers for OPTIONS to API endpoint: {path}")
        # For other paths, check against allowed origins
        elif origin:
            allowed_origins = current_app.config.get("CORS_ORIGINS", ["http://localhost:3000"])
            if origin in allowed_origins or "*" in allowed_origins:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                resp.headers[
                    "Access-Control-Allow-Headers"
                ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Max-Age"] = "3600"
                cors_logger.info(f"Applied CORS headers for OPTIONS to regular endpoint: {path}")

        return resp
