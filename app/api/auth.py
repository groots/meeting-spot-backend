"""Authentication related routes and utilities."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

import jwt
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    request,
    send_from_directory,
    url_for,
)
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .. import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No input data provided", "message": "No input data provided"}), 400

    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required", "message": "Email and password are required"}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "User already exists", "message": "User already exists"}), 409

    # Create new user with only the required fields to avoid issues with missing columns
    user_data = {"email": email, "password_hash": generate_password_hash(password)}

    # Add optional fields only if they're provided and exist in the User model
    optional_fields = {
        "username": data.get("username", email.split("@")[0]),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "phone": data.get("phone", ""),
    }

    for field, value in optional_fields.items():
        if hasattr(User, field) and getattr(User, field) is not None:
            user_data[field] = value

    # Create the new user
    new_user = User(**user_data)

    # Set the password separately
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()

        # Generate token
        access_token = new_user.generate_access_token()

        return (
            jsonify({"message": "User created successfully", "user": new_user.to_dict(), "access_token": access_token}),
            201,
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Error creating user", "message": "Error creating user"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login a user."""
    try:
        data = request.get_json() or {}  # Handle None case

        # Log incoming request data (without password)
        safe_data = {k: v for k, v in data.items() if k != "password"} if data else {}
        current_app.logger.info(f"Login attempt with data: {safe_data}")

        # Empty JSON or no JSON both mean missing credentials
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        password = data.get("password", "")

        if not email or not password:
            current_app.logger.warning(f"Login failed: missing email or password")
            return (
                jsonify({"error": "Email and password are required", "message": "Email and password are required"}),
                400,
            )

        # Find user with detailed error handling
        try:
            # Simplified query that doesn't rely on specific columns
            query = db.session.query(User.id, User.email, User.password_hash).filter(User.email == email)

            try:
                # Try to execute the query
                user_data = query.first()

                if not user_data:
                    current_app.logger.warning(f"Login failed: user not found for email {email}")
                    return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

                # Get the full user object with a simple query to avoid column issues
                user = User.query.get(user_data.id)

            except SQLAlchemyError as e:
                # Try a more minimal query as fallback
                current_app.logger.error(f"Error querying user with columns: {str(e)}")
                current_app.logger.info("Attempting fallback with simpler query")

                # Raw SQL query to avoid SQLAlchemy model mapping issues
                stmt = text("SELECT id, email, password_hash FROM users WHERE email = :email")
                result = db.session.execute(stmt, {"email": email}).fetchone()

                if not result:
                    current_app.logger.warning(f"Login failed: user not found for email {email} in fallback query")
                    return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

                # Get the full user object
                user = User.query.get(result.id)

                if not user:
                    current_app.logger.error(f"User found in raw query but not in ORM query for {email}")
                    return jsonify({"error": "Server error", "message": "Error processing login request"}), 500

        except Exception as db_error:
            current_app.logger.error(f"Database error looking up user: {str(db_error)}")
            return jsonify({"error": "Server error", "message": "Error processing login request"}), 500

        # Check password
        try:
            if not user.check_password(password):
                current_app.logger.warning(f"Login failed: incorrect password for user {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401
        except Exception as pwd_error:
            current_app.logger.error(f"Password check error for user {email}: {str(pwd_error)}")
            return jsonify({"error": "Server error", "message": "Error processing login request"}), 500

        # Generate token
        try:
            access_token = user.generate_access_token()
            current_app.logger.info(f"Login successful for user {email}")
            response_data = {"message": "Login successful", "access_token": access_token}

            # Try to add user data safely
            try:
                response_data["user"] = user.to_dict()
            except Exception as user_dict_error:
                current_app.logger.error(f"Error generating user dict for {email}: {str(user_dict_error)}")
                # Fall back to minimal user data
                response_data["user"] = {
                    "id": str(user.id),
                    "email": user.email,
                }

            return jsonify(response_data), 200
        except Exception as token_error:
            current_app.logger.error(f"Token generation error for user {email}: {str(token_error)}")
            return jsonify({"error": "Server error", "message": "Error generating authentication token"}), 500

    except Exception as e:
        current_app.logger.error(f"Unhandled exception in login endpoint: {str(e)}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current user information."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found", "message": "User not found"}), 404

    return jsonify(user.to_dict()), 200


@auth_bp.route("/me/picture", methods=["POST", "OPTIONS"])
@jwt_required()
def upload_profile_picture():
    """Upload a profile picture for the current user."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    current_user_id = get_jwt_identity()

    # Check if the user exists
    user = User.query.get(current_user_id)
    if not user:
        current_app.logger.error(f"[/me/picture] User not found: {current_user_id}")
        return jsonify({"error": "User not found"}), 404

    # Check if the post request has the file part
    if "file" not in request.files:
        current_app.logger.error(f"[/me/picture] No file part in the request")
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    # If user does not select file, browser also
    # submits an empty part without filename
    if file.filename == "":
        current_app.logger.error(f"[/me/picture] No selected file")
        return jsonify({"error": "No selected file"}), 400

    # Check if the file is allowed
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    filename = file.filename

    if not ("." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions):
        current_app.logger.error(f"[/me/picture] Invalid file type: {filename}")
        return jsonify({"error": "Invalid file type"}), 400

    # Create a safe filename
    file_ext = filename.rsplit(".", 1)[1].lower()
    safe_filename = f"{uuid.uuid4().hex}.{file_ext}"

    # Ensure the profile_pictures directory exists
    profile_pictures_dir = os.path.join(current_app.instance_path, "profile_pictures")
    os.makedirs(profile_pictures_dir, exist_ok=True)

    # Save the file
    file_path = os.path.join(profile_pictures_dir, safe_filename)
    file.save(file_path)

    # Update the user's profile picture URL if the column exists
    try:
        if hasattr(user, "profile_picture_url") and user.profile_picture_url is not None:
            # Set the URL to access the image - the URL is based on the flask route
            profile_picture_url = url_for("api.auth.get_profile_picture", filename=safe_filename, _external=True)
            user.profile_picture_url = profile_picture_url
            db.session.commit()
        else:
            current_app.logger.warning(f"[/me/picture] profile_picture_url column not available for user {user.id}")
    except Exception as e:
        current_app.logger.error(f"[/me/picture] Error updating profile picture URL: {str(e)}")
        # Continue anyway - the file was saved

    return jsonify({"message": "Profile picture uploaded successfully", "filename": safe_filename}), 201


@auth_bp.route("/profile/picture/<filename>")
def get_profile_picture(filename):
    """Get a user's profile picture by filename."""
    # Validate filename to prevent directory traversal
    if not filename or ".." in filename:
        current_app.logger.error(f"[get_profile_picture] Invalid filename: {filename}")
        return jsonify({"error": "Invalid filename"}), 400

    profile_pictures_dir = os.path.join(current_app.instance_path, "profile_pictures")
    return send_from_directory(profile_pictures_dir, filename)
