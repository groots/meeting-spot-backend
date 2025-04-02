import uuid
from typing import Any, Dict, List, Optional, Union

from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.security import generate_password_hash

from .. import db
from ..models import User

api = Namespace("users", description="User operations")

# Swagger models
user_model = api.model(
    "User",
    {
        "id": fields.String(description="Unique identifier for the user"),
        "email": fields.String(description="User's email address"),
        "google_oauth_id": fields.String(description="Google OAuth ID if using Google sign-in"),
        "created_at": fields.DateTime(description="When the user was created"),
        "updated_at": fields.DateTime(description="When the user was last updated"),
    },
)

create_user_model = api.model(
    "CreateUser",
    {
        "email": fields.String(required=True, description="User's email address"),
        "password": fields.String(required=True, description="User's password"),
        "google_oauth_id": fields.String(description="Google OAuth ID if using Google sign-in"),
    },
)


@api.route("/")
class UserList(Resource):
    @api.doc("create_user")
    @api.expect(create_user_model)
    @api.response(201, "User created successfully")
    @api.response(400, "Invalid input")
    def post(self) -> None:
        """Create a new user"""
        data = request.get_json()

        # Validate required fields
        if not data.get("email") or not data.get("password"):
            return {"error": "Missing required fields"}, 400

        # Check if user already exists
        if User.query.filter_by(email=data["email"]).first():
            return {"error": "Email already registered"}, 400

        # Create new user
        new_user = User(
            id=uuid.uuid4(),
            email=data["email"],
            password_hash=generate_password_hash(data["password"]),
            google_oauth_id=data.get("google_oauth_id"),
        )

        db.session.add(new_user)
        db.session.commit()

        return new_user.to_dict(), 201


@api.route("/<string:user_id>")
@api.param("user_id", "The user identifier")
class UserResource(Resource):
    @api.doc("get_user")
    @api.response(200, "User found")
    @api.response(404, "User not found")
    def get(self, user_id) -> None:
        """Get a user by ID"""
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return {"error": "Invalid user ID format"}, 400

        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404

        return user.to_dict()
