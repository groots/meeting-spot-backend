"""Middleware for ensuring required environment variables and configurations are set."""

import logging
import os

from flask import Flask, current_app, request

# Default encryption key to use if none is set in the environment
DEFAULT_ENCRYPTION_KEY = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"


def ensure_encryption_key(app: Flask) -> None:
    """Ensure encryption key is set in app config."""
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
        app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY


def register_middleware(app: Flask) -> None:
    """Register middleware with the Flask app."""

    # Make sure encryption key is set
    ensure_encryption_key(app)

    # Register before_request handlers
    @app.before_request
    def check_encryption_key():
        """Check if encryption key is properly set in the config."""
        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
            current_app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

    # Log the encryption key status (don't log the actual key)
    if app.config.get("ENCRYPTION_KEY"):
        app.logger.info("ENCRYPTION_KEY is configured")
    else:
        app.logger.error("ENCRYPTION_KEY could not be set; this may cause issues with encrypted data")

    @app.after_request
    def add_special_headers(response):
        """Add additional headers for cross-origin popups and authentication flows."""
        # Add Cross-Origin-Opener-Policy header to allow popups
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin-allow-popups")

        # Set more permissive headers for auth endpoints
        if request.path.startswith("/api/v1/auth/"):
            # Allow credentials
            response.headers.setdefault("Access-Control-Allow-Credentials", "true")

            # Handle preflight requests specifically
            if request.method == "OPTIONS":
                response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                response.headers.setdefault(
                    "Access-Control-Allow-Headers", "Content-Type, Authorization, Accept, X-Requested-With, Origin"
                )
                response.headers.setdefault("Access-Control-Max-Age", "3600")

        return response
