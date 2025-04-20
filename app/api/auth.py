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

facebook_callback_model = api.model(
    "FacebookCallback",
    {
        "access_token": fields.String(required=True, description="Facebook access token"),
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
        try:
            current_app.logger.info("Login attempt started")
            data = request.get_json()

            if not data or not data.get("email") or not data.get("password"):
                current_app.logger.warning("Login failed: Missing required fields")
                return {"error": "Missing required fields"}, 400

            # Log the email (without password) for debugging
            current_app.logger.info(f"Login attempt for email: {data.get('email')}")

            # Use a direct SQL approach to avoid ORM issues with missing columns
            try:
                from sqlalchemy import Column, MetaData, String, Table, Text, select

                # Get the user safely using core SQL, only selecting needed columns
                metadata = MetaData()
                users = Table(
                    "users",
                    metadata,
                    Column("id", String(36), primary_key=True),
                    Column("email", String(120)),
                    Column("password_hash", Text),
                    Column("created_at", Text),
                    Column("updated_at", Text),
                    autoload_with=db.engine,
                )

                # Build targeted query that doesn't depend on all columns
                query = select(
                    users.c.id, users.c.email, users.c.password_hash, users.c.created_at, users.c.updated_at
                ).where(users.c.email == data["email"])

                with db.engine.connect() as conn:
                    result = conn.execute(query).fetchone()

                if not result:
                    current_app.logger.info(f"Login failed: User not found for email {data.get('email')}")
                    return {"error": "Invalid credentials"}, 401

                # Create a minimal user object with just what we need
                # Handle both SQLAlchemy 1.4+ Row objects and older versions
                try:
                    current_app.logger.info(f"Processing result: Type={type(result)}")
                    if result is None:
                        current_app.logger.error("Critical error: Result should not be None at this point")
                        return {"error": "Internal server error: Failed to load user data"}, 500

                    # Log the actual result structure for debugging
                    current_app.logger.info(
                        f"Result keys: {dir(result) if hasattr(result, '__dict__') else 'No dir available'}"
                    )
                    current_app.logger.info(f"Result data sample: {str(result)[:200]}")

                    if hasattr(result, "_mapping"):
                        # SQLAlchemy 1.4+
                        current_app.logger.info("Using _mapping for SQLAlchemy 1.4+ result")
                        user_data = dict(result._mapping)
                    else:
                        # Older SQLAlchemy or dict-like object
                        current_app.logger.info("Using direct dict conversion for result")
                        user_data = dict(result)

                    # Log the extracted data (except password)
                    safe_user_data = {k: v for k, v in user_data.items() if k != "password_hash"}
                    current_app.logger.info(f"Extracted user_data: {safe_user_data}")

                    user_id = user_data["id"]
                    password_hash = user_data["password_hash"]
                    current_app.logger.info(f"User found with ID: {user_id}")
                except (TypeError, KeyError, AttributeError) as e:
                    current_app.logger.error(f"Error extracting user data: {str(e)}")
                    current_app.logger.error(f"Result type: {type(result)}")
                    current_app.logger.error(f"Result: {result}")
                    # Additional debug information
                    current_app.logger.error(f"Traceback: {traceback.format_exc()}")
                    return {"error": "Error processing user data", "error_type": type(e).__name__}, 500

            except Exception as user_error:
                current_app.logger.error(f"Error querying user: {str(user_error)}")
                current_app.logger.error(traceback.format_exc())
                return {"error": "Error querying user database", "error_type": type(user_error).__name__}, 500

            # Check if password hash exists
            if not password_hash:
                current_app.logger.warning(f"Login failed: User {user_id} has no password hash (OAuth user?)")
                return {"error": "This account does not have a password set. Please login with OAuth."}, 401

            # Verify password using werkzeug's check_password_hash directly
            try:
                if not check_password_hash(password_hash, data["password"]):
                    current_app.logger.info(f"Login failed: Invalid password for user {user_id}")
                    return {"error": "Invalid credentials"}, 401

                current_app.logger.info(f"Password verified for user {user_id}")
            except Exception as pwd_error:
                current_app.logger.error(f"Error checking password: {str(pwd_error)}")
                current_app.logger.error(traceback.format_exc())
                return {"error": "Error validating credentials", "error_type": type(pwd_error).__name__}, 500

            # Generate access token
            try:
                access_token = create_access_token(identity=str(user_id))
                current_app.logger.info(f"Access token generated for user {user_id}")
            except Exception as token_error:
                current_app.logger.error(f"Error generating token: {str(token_error)}")
                current_app.logger.error(traceback.format_exc())
                return {"error": "Error generating access token", "error_type": type(token_error).__name__}, 500

            # Create a minimal user dictionary with the available data
            try:
                user_dict = {
                    "id": str(user_id),
                    "email": user_data["email"],
                    "created_at": user_data["created_at"],
                    "updated_at": user_data["updated_at"],
                    "is_oauth_user": False,  # We know this is a password login
                }

                # Try to get premium status if available
                try:
                    # Query for active subscription
                    subscription_table = Table("subscriptions", metadata, autoload_with=db.engine)
                    sub_query = select(subscription_table).where(
                        (subscription_table.c.user_id == user_id) & (subscription_table.c.status == "active")
                    )

                    with db.engine.connect() as conn:
                        sub_result = conn.execute(sub_query).fetchone()

                    user_dict["is_premium"] = bool(sub_result)

                    if sub_result:
                        # Handle both SQLAlchemy 1.4+ Row objects and older versions
                        try:
                            if hasattr(sub_result, "_mapping"):
                                # SQLAlchemy 1.4+
                                sub_data = dict(sub_result._mapping)
                            else:
                                # Older SQLAlchemy or dict-like object
                                sub_data = dict(sub_result)

                            user_dict["subscription"] = {
                                "id": str(sub_data.get("id")),
                                "plan_id": sub_data.get("plan_id"),
                                "status": sub_data.get("status"),
                                "current_period_end": sub_data.get("current_period_end"),
                            }
                        except (TypeError, AttributeError) as e:
                            current_app.logger.error(f"Error extracting subscription data: {str(e)}")
                            current_app.logger.error(f"Sub result type: {type(sub_result)}")
                            user_dict["subscription"] = {"error": "Could not process subscription data"}
                        except Exception as sub_error:
                            current_app.logger.warning(f"Could not fetch subscription data: {str(sub_error)}")
                            user_dict["is_premium"] = False
                            user_dict["subscription"] = None
                except Exception as sub_error:
                    current_app.logger.warning(f"Could not fetch subscription data: {str(sub_error)}")
                    user_dict["is_premium"] = False
                    user_dict["subscription"] = None

                current_app.logger.info(f"User data retrieved successfully for user {user_id}")
            except Exception as dict_error:
                current_app.logger.error(f"Error creating user dict: {str(dict_error)}")
                current_app.logger.error(traceback.format_exc())

                # Use minimal data if there was an error
                user_dict = {"id": str(user_id), "email": user_data["email"]}
                current_app.logger.info("Using minimal user dict as fallback")

            current_app.logger.info(f"Login successful for user {user_id}")
            return {"access_token": access_token, "user": user_dict}

        except Exception as e:
            # Catch-all for any other errors
            current_app.logger.error(f"Unexpected error during login: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return {"error": "An error occurred during login", "error_type": type(e).__name__}, 500


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


@api.route("/debug-google")
class GoogleConfigDebugSimple(Resource):
    @api.doc("debug_google_config")
    def get(self):
        """Simple debug endpoint to check Google OAuth configuration"""
        try:
            return {
                "message": "Debug endpoint working",
                "google_client_id_configured": bool(current_app.config.get("GOOGLE_CLIENT_ID")),
                "time": datetime.now().isoformat(),
            }, 200
        except Exception as e:
            return {"error": str(e)}, 500

    def options(self):
        """Handle OPTIONS requests for CORS"""
        response = current_app.make_default_options_response()

        # Get the origin from the request
        origin = request.headers.get("Origin")

        # Set CORS headers
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"

        return response


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


@api.route("/facebook/callback")
class FacebookCallback(Resource):
    @api.expect(facebook_callback_model)
    @api.doc(
        "facebook_callback",
        responses={
            200: "Login successful",
            400: "Invalid token",
            500: "Server error",
        },
    )
    def post(self):
        """Handle Facebook OAuth callback"""
        try:
            data = request.get_json()
            if not data or not data.get("access_token"):
                return {"message": "Access token is required"}, 400

            # Log received token length for debugging (without exposing token)
            token_length = len(data["access_token"]) if data.get("access_token") else 0
            current_app.logger.info(f"Received Facebook token of length: {token_length}")

            # Check if FACEBOOK_APP_ID is configured
            facebook_app_id = current_app.config.get("FACEBOOK_APP_ID")
            if not facebook_app_id:
                current_app.logger.error("FACEBOOK_APP_ID is not configured in application settings")
                return {"message": "Facebook OAuth is not properly configured"}, 500

            # Validate the Facebook token by making a request to the Facebook Graph API
            import requests

            try:
                fb_response = requests.get(
                    f"https://graph.facebook.com/me?fields=id,email&access_token={data['access_token']}"
                )
                if not fb_response.ok:
                    current_app.logger.error(f"Error validating Facebook token: {fb_response.text}")
                    return {"message": "Invalid Facebook token"}, 400

                fb_data = fb_response.json()
                current_app.logger.info(f"Facebook token validated successfully for user: {fb_data.get('id')}")
            except Exception as token_error:
                current_app.logger.error(f"Error validating Facebook token: {str(token_error)}")
                current_app.logger.error(f"Token validation error details: {traceback.format_exc()}")
                return {"message": f"Invalid token: {str(token_error)}"}, 400

            # Get user info from Facebook response
            facebook_id = fb_data.get("id")
            email = fb_data.get("email")

            if not facebook_id:
                current_app.logger.error("Facebook ID not found in response")
                return {"message": "Failed to get user ID from Facebook"}, 400

            if not email:
                current_app.logger.error("Email not found in Facebook response")
                # We could either fail or create a user without email
                # For security, let's require an email
                return {
                    "message": "Email not provided by Facebook. Please ensure your Facebook account has a verified email."
                }, 400

            current_app.logger.info(f"Extracted email from Facebook: {email}")

            # Check if user exists by Facebook ID
            user = User.query.filter_by(facebook_oauth_id=facebook_id).first()
            if not user:
                # Check if email is already registered
                user = User.query.filter_by(email=email).first()
                if user:
                    # Link Facebook account to existing user
                    current_app.logger.info(f"Linking Facebook account to existing user: {email}")
                    user.facebook_oauth_id = facebook_id
                else:
                    # Create new user
                    current_app.logger.info(f"Creating new user with Facebook OAuth: {email}")
                    user = User(email=email, facebook_oauth_id=facebook_id)
                    db.session.add(user)

                db.session.commit()
            else:
                current_app.logger.info(f"Found existing Facebook-linked user: {email}")

            # Generate access token
            access_token = create_access_token(identity=user.id)
            current_app.logger.info(f"Generated access token for user {user.id}")

            return {
                "message": "Facebook authentication successful",
                "access_token": access_token,
                "user": user.to_dict(),
            }, 200

        except Exception as e:
            # Other errors
            current_app.logger.error(f"Facebook authentication error: {str(e)}")
            current_app.logger.error(f"Facebook auth error details: {traceback.format_exc()}")
            return {"message": f"Authentication failed: {str(e)}"}, 500


@api.route("/facebook/deauthorize")
class FacebookDeauthorize(Resource):
    @api.doc(
        "facebook_deauthorize",
        responses={
            200: "Deauthorization handled successfully",
            400: "Invalid request",
            500: "Server error",
        },
    )
    def post(self):
        """Handle Facebook app deauthorization callback

        This endpoint is called by Facebook when a user removes the app
        from their Facebook account. It should remove Facebook connection
        from the user account but keep the account itself.
        """
        try:
            # Facebook sends a signed_request parameter that contains user_id
            signed_request = request.form.get("signed_request")
            if not signed_request:
                current_app.logger.error("No signed_request in Facebook deauthorize callback")
                return {"success": True}, 200  # Return 200 even for errors to acknowledge receipt

            # Parse the signed request from Facebook
            # Format: encoded_signature.encoded_payload
            try:
                encoded_signature, encoded_payload = signed_request.split(".")
                import base64
                import json

                # Decode the payload (we don't validate the signature in this implementation)
                # In production, you should validate the signature using your app secret
                # Padding the base64 string if needed
                payload = encoded_payload.replace("-", "+").replace("_", "/")
                payload += "=" * (4 - len(payload) % 4) if len(payload) % 4 else ""

                payload_data = json.loads(base64.b64decode(payload).decode("utf-8"))
                current_app.logger.info(f"Received deauthorize request: {json.dumps(payload_data)}")

                user_id = payload_data.get("user_id")
                if not user_id:
                    current_app.logger.error("No user_id in Facebook deauthorize payload")
                    return {"success": True}, 200

                # Find the user by Facebook ID and remove the connection
                user = User.query.filter_by(facebook_oauth_id=user_id).first()
                if user:
                    current_app.logger.info(f"Removing Facebook connection for user {user.email}")
                    user.facebook_oauth_id = None
                    db.session.commit()
                else:
                    current_app.logger.info(f"No user found with Facebook ID {user_id}")

                return {"success": True}, 200

            except Exception as e:
                current_app.logger.error(f"Error parsing Facebook signed request: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return {"success": True}, 200

        except Exception as e:
            current_app.logger.error(f"Facebook deauthorize error: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return {"success": True}, 200  # Always acknowledge receipt to Facebook
