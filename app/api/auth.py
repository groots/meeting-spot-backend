import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import google.auth.transport.requests
from flask import current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from google.oauth2 import id_token
from werkzeug.security import check_password_hash

from .. import db
from ..models import User

api = Namespace("auth", description="Authentication operations")

# Swagger models
login_model = api.model(
    "Login",
    {
        "email": fields.String(required=True, description="User's email address"),
        "password": fields.String(required=True, description="User's password"),
    },
)

register_model = api.model(
    "Register",
    {
        "email": fields.String(required=True, description="User email"),
        "password": fields.String(required=True, description="User password"),
        "name": fields.String(required=False, description="User name (ignored)"),
    },
)

google_callback_model = api.model(
    "GoogleCallback",
    {
        "token": fields.String(required=True, description="Google OAuth token (credential)"),
    },
)

forgot_password_model = api.model(
    "ForgotPassword",
    {
        "email": fields.String(required=True, description="User's email address"),
    },
)

reset_password_model = api.model(
    "ResetPassword",
    {
        "token": fields.String(required=True, description="Password reset token"),
        "password": fields.String(required=True, description="New password"),
    },
)


@api.route("/login")
class Login(Resource):
    @api.doc("login")
    @api.expect(login_model)
    @api.response(200, "Login successful")
    @api.response(401, "Invalid credentials")
    def post(self) -> None:
        """Login user and return access token"""
        data = request.get_json()

        if not data or not data.get("email") or not data.get("password"):
            return {"error": "Missing required fields"}, 400

        user = User.query.filter_by(email=data["email"]).first()
        if not user or not check_password_hash(user.password_hash, data["password"]):
            return {"error": "Invalid credentials"}, 401

        access_token = create_access_token(identity=str(user.id))
        return {"access_token": access_token, "user": user.to_dict()}


@api.route("/register")
class Register(Resource):
    @api.expect(register_model)
    @api.doc(
        "register_user",
        responses={201: "User created successfully", 400: "Invalid input or email already exists", 500: "Server error"},
    )
    def post(self) -> None:
        """Register a new user"""
        data = request.get_json()

        # Validate required fields
        if not data.get("email") or not data.get("password"):
            return {"message": "Email and password are required"}, 400

        # Check if user already exists
        if User.query.filter_by(email=data["email"]).first():
            return {"message": "User already exists"}, 409

        try:
            # Log registration attempt for debugging
            current_app.logger.info(f"Registration attempt for email: {data['email']}")

            # Create new user
            user = User(email=data["email"])
            user.set_password(data["password"])

            # Log user object created
            current_app.logger.info(f"User object created with ID: {user.id}")

            # Add and commit to database
            db.session.add(user)
            current_app.logger.info("User added to session, about to commit")
            db.session.commit()
            current_app.logger.info("User committed to database successfully")

            # Generate access token
            access_token = create_access_token(identity=str(user.id))
            current_app.logger.info(f"Access token generated for user {user.id}")

            return {
                "message": "User registered successfully",
                "access_token": access_token,
                "user": user.to_dict(),
            }, 201

        except Exception as e:
            db.session.rollback()
            # Enhanced error logging
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "data": {k: v if k != "password" else "[REDACTED]" for k, v in data.items()} if data else None,
            }
            current_app.logger.error(f"Error registering user: {error_details}")
            return {"message": "Error registering user", "error_type": type(e).__name__}, 500


@api.route("/me")
class UserProfile(Resource):
    @api.doc("get_profile")
    @api.response(200, "Profile retrieved successfully")
    @api.response(401, "Unauthorized")
    @jwt_required()
    def get(self) -> None:
        """Get the current user's profile"""
        current_user_id = get_jwt_identity()
        user = User.query.get(uuid.UUID(current_user_id))

        if not user:
            return {"error": "User not found"}, 404

        return user.to_dict()

    @api.doc("delete_account")
    @api.response(200, "Account successfully deleted")
    @api.response(401, "Unauthorized")
    @api.response(404, "User not found")
    @api.response(500, "Server error")
    @jwt_required()
    def delete(self) -> None:
        """Delete the current user's account and all associated data"""
        try:
            # Get the current user from the JWT token
            current_user_id = get_jwt_identity()
            user = User.query.get(uuid.UUID(current_user_id))

            if not user:
                return {"error": "User not found"}, 404

            # Store email for response
            email = user.email

            # Delete the user and all their data
            # Cascade will handle related data through relationship settings
            db.session.delete(user)
            db.session.commit()

            # Log the deletion
            current_app.logger.info(f"User account deleted: {email}")

            return {
                "message": "Your account and all associated data have been successfully deleted",
                "email": email,
            }, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user account: {str(e)}")
            return {"error": "An error occurred while deleting your account"}, 500


@api.route("/google/callback")
class GoogleCallback(Resource):
    @api.expect(google_callback_model)
    @api.doc(
        "google_callback",
        responses={
            200: "Login successful",
            400: "Invalid token",
            500: "Server error",
        },
    )
    def post(self):
        """Handle Google OAuth callback"""
        try:
            data = request.get_json()
            if not data or not data.get("token"):
                return {"message": "Token is required"}, 400

            # Log received token length for debugging (without exposing token)
            token_length = len(data["token"]) if data.get("token") else 0
            current_app.logger.info(f"Received Google token of length: {token_length}")

            # Check if GOOGLE_CLIENT_ID is configured
            google_client_id = current_app.config.get("GOOGLE_CLIENT_ID")
            if not google_client_id:
                current_app.logger.error("GOOGLE_CLIENT_ID is not configured in application settings")
                return {"message": "Google OAuth is not properly configured"}, 500

            current_app.logger.info(
                f"Using Google Client ID: {google_client_id[:10]}...{google_client_id[-10:] if len(google_client_id) > 20 else ''}"
            )

            # Verify the Google token
            try:
                idinfo = id_token.verify_oauth2_token(
                    data["token"], google.auth.transport.requests.Request(), google_client_id
                )

                # Log successful token verification
                current_app.logger.info("Google token successfully verified")

            except Exception as token_error:
                current_app.logger.error(f"Error verifying Google token: {str(token_error)}")
                return {"message": f"Invalid token: {str(token_error)}"}, 400

            # Get user info from the token
            google_id = idinfo["sub"]
            email = idinfo["email"]
            current_app.logger.info(f"Extracted email from token: {email}")

            # Check if user exists
            user = User.query.filter_by(google_oauth_id=google_id).first()
            if not user:
                # Check if email is already registered
                user = User.query.filter_by(email=email).first()
                if user:
                    # Link Google account to existing user
                    current_app.logger.info(f"Linking Google account to existing user: {email}")
                    user.google_oauth_id = google_id
                else:
                    # Create new user
                    current_app.logger.info(f"Creating new user with Google OAuth: {email}")
                    user = User(email=email, google_oauth_id=google_id)
                    db.session.add(user)

                db.session.commit()
            else:
                current_app.logger.info(f"Found existing Google-linked user: {email}")

            # Generate access token
            access_token = create_access_token(identity=user.id)
            current_app.logger.info(f"Generated access token for user {user.id}")

            return {
                "message": "Google authentication successful",
                "access_token": access_token,
                "user": user.to_dict(),
            }, 200

        except ValueError as e:
            # Invalid token
            current_app.logger.error(f"Invalid Google token: {str(e)}")
            current_app.logger.error(f"Token validation error details: {traceback.format_exc()}")
            return {"message": f"Invalid token: {str(e)}"}, 400
        except Exception as e:
            # Other errors
            current_app.logger.error(f"Google authentication error: {str(e)}")
            current_app.logger.error(f"Google auth error details: {traceback.format_exc()}")
            return {"message": f"Authentication failed: {str(e)}"}, 500


@api.route("/debug/google-config")
class GoogleConfigDebug(Resource):
    def get(self):
        """Debug endpoint to check Google OAuth configuration"""
        try:
            response = {
                "google_client_id_configured": bool(current_app.config.get("GOOGLE_CLIENT_ID")),
                "google_client_id_length": len(current_app.config.get("GOOGLE_CLIENT_ID", "")),
                "google_client_id_prefix": current_app.config.get("GOOGLE_CLIENT_ID", "")[:10] + "..."
                if current_app.config.get("GOOGLE_CLIENT_ID")
                else "Not set",
                "config_source": current_app.config.get("CONFIG_SOURCE", "Unknown"),
                "environment": current_app.config.get("ENV", "Unknown"),
                "development_config_loaded": hasattr(current_app, "_development_config_loaded")
                and current_app._development_config_loaded,
                "google_auth_module_available": "google.oauth2" in sys.modules,
                "missing_required_configs": [],
            }

            # Check for required configurations
            required_configs = ["GOOGLE_CLIENT_ID", "JWT_SECRET_KEY"]
            for config in required_configs:
                if not current_app.config.get(config):
                    response["missing_required_configs"].append(config)

            # Add environment variables that might help with debugging
            env_prefix = "GOOGLE_"
            env_vars = {k: v for k, v in os.environ.items() if k.startswith(env_prefix) and "secret" not in k.lower()}
            response["relevant_env_vars"] = env_vars

            return response, 200

        except Exception as e:
            return {
                "error": f"Error retrieving Google OAuth configuration: {str(e)}",
                "traceback": traceback.format_exc(),
            }, 500


@api.route("/forgot-password")
class ForgotPassword(Resource):
    @api.expect(forgot_password_model)
    @api.doc(
        "forgot_password",
        responses={
            200: "Password reset email sent",
            400: "Invalid input",
            404: "User not found",
            500: "Server error",
        },
    )
    def post(self):
        """Request a password reset email"""
        from app.models.password_reset import PasswordReset
        from app.utils.notifications import send_email

        data = request.get_json()
        if not data or not data.get("email"):
            return {"message": "Email is required"}, 400

        email = data["email"].lower().strip()
        user = User.query.filter_by(email=email).first()

        # Always return success to prevent email enumeration
        if not user:
            current_app.logger.info(f"Password reset requested for non-existent email: {email}")
            return {"message": "If your email is registered, you will receive a password reset link"}, 200

        try:
            # Create a password reset token
            reset = PasswordReset.create_for_user(user.id)
            db.session.commit()

            # Generate the reset URL
            frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
            reset_url = f"{frontend_url}/auth/reset-password/{reset.token}"

            # Send the email
            subject = "Reset Your Password - Find a Meeting Spot"
            body = f"""Hello,

You have requested to reset your password for your Find a Meeting Spot account.

To reset your password, please click the following link:
{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.

Best regards,
Find a Meeting Spot Team
"""
            success = send_email(user.email, subject, body)

            if not success:
                db.session.rollback()
                current_app.logger.error(f"Failed to send password reset email to {user.email}")
                return {"message": "Failed to send password reset email"}, 500

            return {"message": "If your email is registered, you will receive a password reset link"}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating password reset: {str(e)}")
            return {"message": "An error occurred while processing your request"}, 500


@api.route("/reset-password")
class RequestPasswordReset(Resource):
    @api.expect(forgot_password_model)
    @api.doc(
        "request_password_reset",
        responses={
            200: "Password reset email sent",
            400: "Invalid input",
            500: "Server error",
        },
    )
    def post(self):
        """Request a password reset email (alternate endpoint)"""
        from app.models.password_reset import PasswordReset
        from app.utils.notifications import send_email

        data = request.get_json()
        if not data or not data.get("email"):
            return {"message": "Email is required"}, 400

        email = data["email"].lower().strip()
        user = User.query.filter_by(email=email).first()

        # Always return success to prevent email enumeration
        if not user:
            current_app.logger.info(f"Password reset requested for non-existent email: {email}")
            return {"message": "If your email is registered, you will receive a password reset link"}, 200

        try:
            # Create a password reset token
            reset = PasswordReset.create_for_user(user.id)
            db.session.commit()

            # Generate the reset URL
            frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
            reset_url = f"{frontend_url}/auth/reset-password/{reset.token}"

            # Send the email
            subject = "Reset Your Password - Find a Meeting Spot"
            body = f"""Hello,

You have requested to reset your password for your Find a Meeting Spot account.

To reset your password, please click the following link:
{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.

Best regards,
Find a Meeting Spot Team
"""
            success = send_email(user.email, subject, body)

            if not success:
                db.session.rollback()
                current_app.logger.error(f"Failed to send password reset email to {user.email}")
                return {"message": "Failed to send password reset email"}, 500

            return {"message": "If your email is registered, you will receive a password reset link"}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating password reset: {str(e)}")
            return {"message": "An error occurred while processing your request"}, 500


@api.route("/reset-password/confirm")
class ResetPasswordConfirm(Resource):
    @api.expect(reset_password_model)
    @api.doc(
        "reset_password_confirm",
        responses={
            200: "Password reset successful",
            400: "Invalid input or token",
            500: "Server error",
        },
    )
    def post(self):
        """Reset user password using a token (confirm route)"""
        from app.models.password_reset import PasswordReset

        data = request.get_json()
        if not data or not data.get("token") or not data.get("password"):
            return {"message": "Token and password are required"}, 400

        token = data["token"].strip()
        password = data["password"]

        # Validate password strength
        if len(password) < 8:
            return {"message": "Password must be at least 8 characters long"}, 400

        # Find the reset token
        reset = PasswordReset.get_by_token(token)
        if not reset or not reset.is_valid():
            return {"message": "Invalid or expired token"}, 400

        try:
            # Get the user
            user = User.query.get(reset.user_id)
            if not user:
                return {"message": "User not found"}, 404

            # Update the password
            user.set_password(password)

            # Mark the token as used
            reset.use()

            # Save changes
            db.session.commit()

            return {"message": "Password reset successful"}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting password: {str(e)}")
            return {"message": "An error occurred while resetting your password"}, 500
