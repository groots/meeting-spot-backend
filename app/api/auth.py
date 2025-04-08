"""Authentication endpoints."""

import json
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests
from flask import current_app, redirect, request, url_for
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from werkzeug.security import check_password_hash, generate_password_hash

from .. import db
from ..models import User

api = Namespace("auth", description="Authentication operations")

# Models for request/response validation
login_model = api.model(
    "Login",
    {
        "email": fields.String(required=True, description="User email"),
        "password": fields.String(required=True, description="User password"),
    },
)

register_model = api.model(
    "Register",
    {
        "email": fields.String(required=True, description="User email"),
        "password": fields.String(required=True, description="User password"),
    },
)


@api.route("/linkedin/login")
class LinkedInLogin(Resource):
    @api.doc("linkedin_login")
    def get(self):
        """Initiate LinkedIn OAuth flow."""
        params = {
            "response_type": "code",
            "client_id": current_app.config["LINKEDIN_CLIENT_ID"],
            "redirect_uri": current_app.config["LINKEDIN_CALLBACK_URL"],
            "scope": " ".join(current_app.config["LINKEDIN_SCOPE"]),
            "state": str(uuid.uuid4()),
        }

        linkedin_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"
        return redirect(linkedin_url)


@api.route("/linkedin/callback")
class LinkedInCallback(Resource):
    @api.doc("linkedin_callback")
    def get(self):
        """Handle LinkedIn OAuth callback."""
        code = request.args.get("code")

        if not code:
            return {"error": "Authorization code not provided"}, 400

        # Exchange code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        token_params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": current_app.config["LINKEDIN_CALLBACK_URL"],
            "client_id": current_app.config["LINKEDIN_CLIENT_ID"],
            "client_secret": current_app.config["LINKEDIN_CLIENT_SECRET"],
        }

        token_response = requests.post(token_url, data=token_params)
        if token_response.status_code != 200:
            return {"error": "Failed to obtain access token"}, 400

        access_token = token_response.json().get("access_token")

        # Get user profile
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_url = "https://api.linkedin.com/v2/me"
        email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"

        profile_response = requests.get(profile_url, headers=headers)
        email_response = requests.get(email_url, headers=headers)

        if profile_response.status_code != 200 or email_response.status_code != 200:
            return {"error": "Failed to get user profile"}, 400

        profile_data = profile_response.json()
        email_data = email_response.json()

        linkedin_id = profile_data.get("id")
        email = email_data.get("elements", [{}])[0].get("handle~", {}).get("emailAddress")

        if not linkedin_id or not email:
            return {"error": "Failed to get required profile information"}, 400

        # Find or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email=email,
                google_oauth_id=linkedin_id,  # Reusing this field for LinkedIn ID
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.session.add(user)
            db.session.commit()

        # Create JWT token
        access_token = create_access_token(identity=str(user.id))

        # Redirect to frontend with token
        frontend_url = f"{current_app.config['FRONTEND_URL']}?token={access_token}"
        return redirect(frontend_url)


@api.route("/login")
class Login(Resource):
    @api.doc("login")
    @api.expect(login_model)
    def post(self):
        """Log in a user."""
        data = request.get_json()

        user = User.query.filter_by(email=data["email"]).first()
        if not user or not user.check_password(data["password"]):
            return {"error": "Invalid email or password"}, 401

        access_token = create_access_token(identity=str(user.id))
        return {"access_token": access_token}


@api.route("/register")
class Register(Resource):
    @api.doc("register")
    @api.expect(register_model)
    def post(self):
        """Register a new user."""
        data = request.get_json()

        if User.query.filter_by(email=data["email"]).first():
            return {"error": "Email already registered"}, 400

        user = User(
            id=uuid.uuid4(),
            email=data["email"],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        user.set_password(data["password"])

        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        return {"access_token": access_token}, 201


@api.route("/profile")
class UserProfile(Resource):
    @api.doc("get_profile")
    @jwt_required()
    def get(self):
        """Get current user's profile."""
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return {"error": "User not found"}, 404

        return user.to_dict()
