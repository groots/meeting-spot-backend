"""Authentication related routes and utilities."""

import os
import traceback
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


# Helper function to debug database connections and models
def debug_database():
    """Check database connection and model structure."""
    try:
        # Check if we can connect to the database
        result = db.session.execute(text("SELECT 1")).fetchone()
        if result and result[0] == 1:
            current_app.logger.info("Database connection successful")
        else:
            current_app.logger.error("Database connection returned unexpected result")
            return "Database connection issue"

        # Check User model structure
        inspector = inspect(db.engine)
        if not inspector.has_table("users"):
            current_app.logger.error("Table 'users' does not exist")
            return "Table 'users' does not exist"

        # Get columns in the users table
        columns = [col["name"] for col in inspector.get_columns("users")]
        current_app.logger.info(f"User table columns: {columns}")

        # Check for required columns
        required_columns = ["id", "email", "password_hash"]
        missing_columns = [col for col in required_columns if col not in columns]
        if missing_columns:
            current_app.logger.error(f"Missing required columns: {missing_columns}")
            return f"Missing required columns: {missing_columns}"

        return None  # No issues found
    except Exception as e:
        current_app.logger.error(f"Database diagnostic error: {str(e)}")
        return f"Database diagnostic error: {str(e)}"


# Direct token generation without using User model
def generate_direct_token(user_id, email):
    """Generate a JWT token directly without using the User model."""
    try:
        # Create a simple claims dictionary with essential user info
        claims = {"email": email}

        # Generate the token directly using Flask-JWT-Extended
        access_token = create_access_token(identity=str(user_id), additional_claims=claims)

        return access_token
    except Exception as e:
        current_app.logger.error(f"Direct token generation error: {str(e)}")
        raise


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

        # Perform database diagnostic check
        db_issue = debug_database()
        if db_issue:
            current_app.logger.error(f"Database diagnostic failed before login: {db_issue}")
            return jsonify({"error": "Server error", "message": f"Database issue: {db_issue}"}), 500

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
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error looking up user: {str(db_error)}\n{stack_trace}")
            return (
                jsonify({"error": "Server error", "message": "Error processing login request: database lookup failed"}),
                500,
            )

        # Check password
        try:
            if not user.check_password(password):
                current_app.logger.warning(f"Login failed: incorrect password for user {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401
        except Exception as pwd_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Password check error for user {email}: {str(pwd_error)}\n{stack_trace}")
            return (
                jsonify(
                    {"error": "Server error", "message": "Error processing login request: password verification failed"}
                ),
                500,
            )

        # Generate token
        try:
            access_token = user.generate_access_token()
            current_app.logger.info(f"Login successful for user {email}")
            response_data = {"message": "Login successful", "access_token": access_token}

            # Try to add user data safely
            try:
                response_data["user"] = user.to_dict()
            except Exception as user_dict_error:
                stack_trace = traceback.format_exc()
                current_app.logger.error(
                    f"Error generating user dict for {email}: {str(user_dict_error)}\n{stack_trace}"
                )
                # Fall back to minimal user data
                response_data["user"] = {
                    "id": str(user.id),
                    "email": user.email,
                }

            return jsonify(response_data), 200
        except Exception as token_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Token generation error for user {email}: {str(token_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Error generating authentication token"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in login endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred during login"}), 500


# Direct login endpoint that bypasses ORM models
@auth_bp.route("/login/direct", methods=["POST"])
def direct_login():
    """Direct login that bypasses ORM models for more reliability."""
    try:
        data = request.get_json() or {}

        # Log incoming request data (without password)
        safe_data = {k: v for k, v in data.items() if k != "password"} if data else {}
        current_app.logger.info(f"Direct login attempt with data: {safe_data}")

        # Get credentials
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        password = data.get("password", "")

        if not email or not password:
            current_app.logger.warning("Direct login failed: missing email or password")
            return jsonify({"error": "Email and password are required"}), 400

        # Check database connection
        try:
            # Basic connection test
            db.session.execute(text("SELECT 1")).fetchone()

            # Direct SQL query to find user
            stmt = text("SELECT id, email, password_hash FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": email}).fetchone()

            if not result:
                current_app.logger.warning(f"Direct login failed: user not found for email {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Extract user data
            user_id, user_email, password_hash = result

            # Verify password directly
            if not check_password_hash(password_hash, password):
                current_app.logger.warning(f"Direct login failed: incorrect password for user {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Generate token directly
            access_token = generate_direct_token(user_id, user_email)

            # Create minimal user response
            user_data = {
                "id": str(user_id),
                "email": user_email,
            }

            # Try to get additional fields if possible
            try:
                extended_query = text(
                    """
                    SELECT id, email, first_name, last_name, username
                    FROM users WHERE id = :user_id
                """
                )
                extended_result = db.session.execute(extended_query, {"user_id": user_id}).fetchone()

                if extended_result:
                    # Add fields that exist
                    for i, col_name in enumerate(["id", "email", "first_name", "last_name", "username"]):
                        if i < len(extended_result) and extended_result[i] is not None:
                            user_data[col_name] = extended_result[i]
            except Exception as e:
                current_app.logger.warning(f"Could not get extended user data: {str(e)}")

            # Success response
            current_app.logger.info(f"Direct login successful for user {email}")
            return jsonify({"message": "Login successful", "access_token": access_token, "user": user_data}), 200

        except Exception as db_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error in direct login: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in direct login endpoint: {str(e)}\n{stack_trace}")
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


@auth_bp.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    """Handle password reset request."""
    try:
        # Handle OPTIONS request for CORS preflight
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
            return response

        data = request.get_json() or {}

        # Log incoming request data
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        if not email:
            current_app.logger.warning("Reset password failed: missing email")
            return jsonify({"error": "Email is required", "message": "Email is required"}), 400

        # Check database connection
        try:
            # Basic connection test
            db.session.execute(text("SELECT 1")).fetchone()

            # Check if user exists using direct SQL
            stmt = text("SELECT id, email FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": email}).fetchone()

            # Important: Always return success even if user doesn't exist (security best practice)
            success_message = "If your email exists in our system, you will receive password reset instructions."

            if not result:
                # Don't reveal that the user doesn't exist for security reasons
                current_app.logger.info(f"Reset password requested for non-existent email: {email}")
                current_app.logger.info(f"[SECURITY] No email will be sent since user doesn't exist")
                return jsonify({"message": success_message}), 200

            # Generate a secure token
            user_id = result[0]
            from ..utils.security import generate_reset_token

            token = generate_reset_token(user_id)

            # Log the token generation for debugging
            current_app.logger.info(f"Reset password token generated for user ID: {user_id}")

            # Send the password reset email
            from ..utils.notifications import send_password_reset_email

            email_sent = send_password_reset_email(email, token)

            if email_sent:
                current_app.logger.info(f"Password reset email sent to: {email}")
            else:
                current_app.logger.warning(f"Failed to send password reset email to: {email}")
                # Still return success to user (don't reveal email sending issues)

            return jsonify({"message": success_message}), 200

        except Exception as db_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error in reset password: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in reset password endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@auth_bp.route("/register/direct", methods=["POST"])
def direct_register():
    """Direct register endpoint that bypasses ORM models for more reliability."""
    try:
        data = request.get_json() or {}

        # Log incoming request data (without password)
        safe_data = {k: v for k, v in data.items() if k != "password"} if data else {}
        current_app.logger.info(f"Direct register attempt with data: {safe_data}")

        # Get required fields
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        password = data.get("password", "")

        if not email or not password:
            current_app.logger.warning("Direct register failed: missing email or password")
            return jsonify({"error": "Email and password are required"}), 400

        # Check database connection
        try:
            # Basic connection test
            db.session.execute(text("SELECT 1")).fetchone()

            # Check if user already exists using direct SQL
            stmt = text("SELECT id FROM users WHERE email = :email")
            existing_user = db.session.execute(stmt, {"email": email}).fetchone()

            if existing_user:
                current_app.logger.warning(f"Direct register failed: email already exists: {email}")
                return jsonify({"error": "User already exists", "message": "User already exists"}), 409

            # Get optional fields
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            username = data.get("username", email.split("@")[0])
            phone = data.get("phone", "")

            # Generate a new user ID
            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # Hash the password
            password_hash = generate_password_hash(password)

            # Create columns and values lists for the SQL query
            columns = ["id", "email", "password_hash", "created_at", "updated_at"]
            values = [user_id, email, password_hash, now, now]
            placeholders = [":id", ":email", ":password_hash", ":created_at", ":updated_at"]

            # Add optional columns if they're provided
            if first_name:
                columns.append("first_name")
                values.append(first_name)
                placeholders.append(":first_name")

            if last_name:
                columns.append("last_name")
                values.append(last_name)
                placeholders.append(":last_name")

            if username:
                columns.append("username")
                values.append(username)
                placeholders.append(":username")

            if phone:
                columns.append("phone")
                values.append(phone)
                placeholders.append(":phone")

            # Construct the SQL query
            params = dict(zip(columns, values))
            columns_str = ", ".join(columns)
            placeholders_str = ", ".join(placeholders)

            insert_sql = text(f"INSERT INTO users ({columns_str}) VALUES ({placeholders_str})")

            # Execute the query
            db.session.execute(insert_sql, params)
            db.session.commit()

            # Generate token directly
            access_token = generate_direct_token(user_id, email)

            # Create minimal user response
            user_data = {
                "id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "created_at": now,
                "updated_at": now,
            }

            # Success response
            current_app.logger.info(f"Direct register successful for email: {email}")
            return (
                jsonify({"message": "User created successfully", "user": user_data, "access_token": access_token}),
                201,
            )

        except Exception as db_error:
            db.session.rollback()
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error in direct register: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in direct register endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@auth_bp.route("/google/callback/direct", methods=["POST"])
def direct_google_callback():
    """Direct Google auth callback that doesn't rely on ORM models."""
    try:
        data = request.get_json() or {}
        token = data.get("token")

        if not token:
            current_app.logger.warning("Google callback failed: Missing token")
            return jsonify({"error": "Missing token"}), 400

        # Verify the Google token (in a real implementation)
        # For now, we'll just extract email from the token
        # In a real implementation, you would verify with Google's API

        try:
            # Get user info from token (simplified - in a real app you would verify with Google)
            # Extract header.payload.signature
            token_parts = token.split(".")
            if len(token_parts) != 3:
                current_app.logger.error("Invalid token format")
                return jsonify({"error": "Invalid token"}), 400

            # Decode the payload (middle part)
            import base64
            import json

            # Ensure proper base64 padding
            payload = token_parts[1]
            payload += "=" * ((4 - len(payload) % 4) % 4)

            # Decode
            try:
                decoded_payload = base64.b64decode(payload)
                user_info = json.loads(decoded_payload)

                # Extract email
                email = user_info.get("email")
                if not email:
                    current_app.logger.error("No email in token payload")
                    return jsonify({"error": "Invalid token"}), 400

                # Optional: extract other user info
                name = user_info.get("name", "")
                given_name = user_info.get("given_name", "")
                family_name = user_info.get("family_name", "")
                picture = user_info.get("picture", "")
                google_id = user_info.get("sub", "")

            except Exception as decode_error:
                current_app.logger.error(f"Error decoding token: {str(decode_error)}")
                return jsonify({"error": "Could not decode token"}), 400

            # Check if user exists
            stmt = text("SELECT id, email FROM users WHERE email = :email OR google_oauth_id = :google_id")
            existing_user = db.session.execute(stmt, {"email": email, "google_id": google_id}).fetchone()

            if existing_user:
                # User exists, generate token
                user_id = existing_user[0]

                # Make sure google_oauth_id is set
                if google_id:
                    update_stmt = text(
                        "UPDATE users SET google_oauth_id = :google_id WHERE id = :user_id AND google_oauth_id IS NULL"
                    )
                    db.session.execute(update_stmt, {"google_id": google_id, "user_id": user_id})
                    db.session.commit()

                # Generate token directly
                access_token = generate_direct_token(user_id, email)

                return (
                    jsonify(
                        {
                            "message": "Google authentication successful",
                            "access_token": access_token,
                            "user": {"id": user_id, "email": email, "name": name},
                        }
                    ),
                    200,
                )
            else:
                # Create a new user
                user_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat()

                # Create columns and values lists for the SQL query
                columns = ["id", "email", "created_at", "updated_at", "google_oauth_id"]
                values = [user_id, email, now, now, google_id]
                placeholders = [":id", ":email", ":created_at", ":updated_at", ":google_oauth_id"]

                # Add optional columns if they're provided
                if given_name:
                    columns.append("first_name")
                    values.append(given_name)
                    placeholders.append(":first_name")

                if family_name:
                    columns.append("last_name")
                    values.append(family_name)
                    placeholders.append(":last_name")

                if picture:
                    columns.append("profile_picture_url")
                    values.append(picture)
                    placeholders.append(":profile_picture_url")

                # Construct the SQL query
                params = dict(zip(columns, values))
                columns_str = ", ".join(columns)
                placeholders_str = ", ".join(placeholders)

                insert_sql = text(f"INSERT INTO users ({columns_str}) VALUES ({placeholders_str})")

                # Execute the query
                db.session.execute(insert_sql, params)
                db.session.commit()

                # Generate token directly
                access_token = generate_direct_token(user_id, email)

                return (
                    jsonify(
                        {
                            "message": "Google authentication successful",
                            "access_token": access_token,
                            "user": {
                                "id": user_id,
                                "email": email,
                                "first_name": given_name,
                                "last_name": family_name,
                                "name": name,
                            },
                        }
                    ),
                    201,
                )

        except Exception as auth_error:
            db.session.rollback()
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Error in Google authentication: {str(auth_error)}\n{stack_trace}")
            return jsonify({"error": "Error authenticating with Google"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in Google callback: {str(e)}\n{stack_trace}")
        return jsonify({"error": "An error occurred during Google authentication"}), 500
