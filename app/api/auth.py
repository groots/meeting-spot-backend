"""Authentication operations."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import google.auth.transport.requests as google_requests
import google.oauth2.id_token
from flask import current_app, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from werkzeug.security import check_password_hash, generate_password_hash

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
    },
)

google_callback_model = api.model(
    "GoogleCallback",
    {
        "token": fields.String(required=True, description="Google ID token"),
    },
)


@api.route("/google/callback")
class GoogleCallback(Resource):
    @api.expect(google_callback_model)
    @api.doc(
        "google_callback",
        responses={200: "Login successful", 400: "Invalid token", 500: "Server error"},
    )
    def post(self) -> None:
        """Handle Google OAuth callback"""
        try:
            data = request.get_json()
            if not data or "token" not in data:
                return {"error": "Missing token"}, 400

            # Verify the token
            request_session = google_requests.Request()
            id_info = google.oauth2.id_token.verify_oauth2_token(
                data["token"], request_session, current_app.config["GOOGLE_CLIENT_ID"]
            )

            if not id_info:
                return {"error": "Invalid token"}, 400

            # Get user info from token
            google_id = id_info["sub"]
            email = id_info["email"]

            # Find or create user
            user = User.query.filter_by(google_oauth_id=google_id).first()
            if not user:
                # Check if user exists with this email
                user = User.query.filter_by(email=email).first()
                if user:
                    # Update existing user with Google ID
                    user.google_oauth_id = google_id
                else:
                    # Create new user
                    user = User(
                        id=uuid.uuid4(),
                        email=email,
                        google_oauth_id=google_id,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    db.session.add(user)

            db.session.commit()

            # Create access token
            access_token = create_access_token(identity=str(user.id))
            return {"access_token": access_token, "user": user.to_dict()}

        except ValueError as e:
            return {"error": f"Invalid token: {str(e)}"}, 400
        except Exception as e:
            return {"error": f"Server error: {str(e)}"}, 500


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
        responses={201: "User created successfully", 400: "Email already exists"},
    )
    def post(self) -> None:
        """Register a new user"""
        data = request.get_json()

        if User.query.filter_by(email=data["email"]).first():
            return {"message": "Email already exists"}, 400

        user = User(email=data["email"])
        user.set_password(data["password"])

        db.session.add(user)
        db.session.commit()

        return {"message": "User created successfully"}, 201


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
