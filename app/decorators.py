"""Decorators for the application."""

from functools import wraps

from flask import current_app, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_restx import abort

from .models import User


def jwt_required():
    """Decorator to protect routes with JWT authentication."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def auth_required(func):
    """Decorator for routes that require authentication."""

    @jwt_required()
    @wraps(func)
    def wrapped(*args, **kwargs):
        # Get user ID from JWT
        user_id = get_jwt_identity()

        # Store the user in g for convenience in the route handler
        user = User.get_by_token_identity(user_id)
        if not user:
            abort(401, "User not found")

        g.current_user = user
        return func(*args, **kwargs)

    return wrapped


def token_required(func):
    """Decorator for routes that require authentication with JWT token.

    This decorator is similar to auth_required but sets the current_user as a parameter
    rather than in Flask's g object, which is useful in Flask-RESTx resources.
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            # Verify JWT token is present and valid
            verify_jwt_in_request()

            # Get the user identity from the token
            user_id = get_jwt_identity()

            # Get the user from the database
            current_user = User.get_by_token_identity(user_id)

            # Check if user exists
            if not current_user:
                current_app.logger.error(f"User with ID {user_id} not found")
                abort(401, "User not found")

            # Special handling for testing
            if current_app.config.get("TESTING") and current_user.email == "test@example.com":
                current_app.logger.info(f"TEST mode: Authenticated user {current_user.email}")
            else:
                current_app.logger.info(f"Authenticated user {current_user.email}")

            # Call the decorated function with the user
            return func(*args, current_user=current_user, **kwargs)

        except Exception as e:
            # Handle HTTP exceptions (like those raised by abort())
            if hasattr(e, "code") and hasattr(e, "description"):
                current_app.logger.error(f"HTTP exception in token_required: {e.code} - {e.description}")
                raise

            # Otherwise, it's an authentication error
            current_app.logger.error(f"Authentication error in token_required: {str(e)}")
            abort(401, f"Authentication error: {str(e)}")

    return wrapped


def premium_required(func):
    """Decorator for routes that require a premium subscription."""

    @auth_required
    @wraps(func)
    def wrapped(*args, **kwargs):
        # User is available in g.current_user from the auth_required decorator
        user = g.current_user

        # Check if the user has an active premium subscription
        if not user.is_premium():
            return (
                jsonify(
                    {
                        "error": "Premium subscription required",
                        "message": "This feature requires a premium subscription",
                        "subscription": {"current": user.subscription_plan, "required": "premium"},
                    }
                ),
                402,
            )  # 402 Payment Required

        return func(*args, **kwargs)

    return wrapped
