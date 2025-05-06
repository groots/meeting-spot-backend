import os

import requests
from flask import Blueprint, current_app, jsonify, make_response, request
from sqlalchemy import text

from .. import db
from .meetings import api as meetings_api
from .places import api as places_api
from .subscriptions import api as subscriptions_api
from .users import api as users_api

v1_bp = Blueprint("v1", __name__, url_prefix="/v1")

# Import the API router from Flask-RESTX
from flask_restx import Api

api = Api(v1_bp, version="1.0", title="Find A Meeting Spot API", description="API for Find A Meeting Spot app")

# Add namespaces
api.add_namespace(users_api)
api.add_namespace(places_api)
api.add_namespace(meetings_api)
api.add_namespace(subscriptions_api)


# Add health check endpoint
@v1_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify API is up and running."""
    try:
        # Check database connection
        result = db.session.execute(text("SELECT 1")).fetchone()
        db_status = "ok" if result and result[0] == 1 else "error"

        return jsonify({"status": "ok", "version": "1.0", "database": db_status, "api": "Find A Meeting Spot API"}), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "version": "1.0",
                    "database": "error",
                    "error": str(e),
                    "api": "Find A Meeting Spot API",
                }
            ),
            500,
        )


# Add auth endpoints
@v1_bp.route("/auth/reset-password", methods=["GET", "POST", "OPTIONS"])
def reset_password():
    """Handle password reset request with direct implementation."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response

    # For POST requests, implement directly without external dependencies
    try:
        import secrets
        import uuid
        from datetime import datetime, timedelta, timezone

        data = request.get_json() or {}

        # Log incoming request data (without sensitive information)
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        current_app.logger.info(f"Direct Reset password request for email: {email}")

        if not email:
            current_app.logger.warning("Direct Reset password failed: missing email")
            return jsonify({"error": "Email is required", "message": "Email is required"}), 400

        # Success message (always return same message for security)
        success_message = "If your email exists in our system, you will receive password reset instructions."

        # Basic database check
        try:
            # Check if user exists using direct SQL
            stmt = text("SELECT id, email FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": email}).fetchone()

            if not result:
                current_app.logger.info(f"Reset password: User not found for email: {email}")
                # Still return success for security reasons
                return jsonify({"message": success_message}), 200

            # Found user, generate a token directly
            user_id = str(result[0])

            # Generate a reset token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            # Store token in database if password_resets table exists
            try:
                # Check if password_resets table exists
                check_table = text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'password_resets')"
                )
                table_exists = db.session.execute(check_table).scalar()

                if table_exists:
                    # Store token in database
                    token_id = str(uuid.uuid4())
                    reset_stmt = text(
                        """
                        INSERT INTO password_resets (id, user_id, token, created_at, expires_at, used)
                        VALUES (:id, :user_id, :token, :created_at, :expires_at, :used)
                    """
                    )
                    db.session.execute(
                        reset_stmt,
                        {
                            "id": token_id,
                            "user_id": user_id,
                            "token": reset_token,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "expires_at": expires_at.isoformat(),
                            "used": False,
                        },
                    )
                    db.session.commit()
                    current_app.logger.info(f"Reset token stored in database for user {user_id}")
                else:
                    current_app.logger.warning("password_resets table doesn't exist, token will not be persisted")

            except Exception as token_db_error:
                current_app.logger.error(f"Error storing reset token: {str(token_db_error)}")
                # Continue anyway, the email can still be sent
                db.session.rollback()

            # Get frontend URL from config
            frontend_url = current_app.config.get("FRONTEND_URL", "https://findameetingspot.com")
            reset_url = f"{frontend_url}/auth/reset-password/{reset_token}"

            # Create email content
            subject = "Reset Your Find A Meeting Spot Password"
            body = f"""Hello,

You've requested to reset your password for Find A Meeting Spot.

Please click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email or contact support if you have concerns.

Thanks,
The Find A Meeting Spot Team
"""
            # Get Mailgun configuration
            api_key = current_app.config.get("MAILGUN_API_KEY")
            domain = current_app.config.get("MAILGUN_DOMAIN")

            # Also check environment variables directly
            if not api_key:
                api_key = os.environ.get("MAILGUN_API_KEY")
            if not domain:
                domain = os.environ.get("MAILGUN_DOMAIN")

            # Log email preparation details
            current_app.logger.info(f"Preparing reset email to: {email}")
            current_app.logger.info(f"Mailgun Domain: {domain}")
            current_app.logger.info(f"API Key present: {'Yes' if api_key else 'No'}")

            # Send email if configuration is available
            if api_key and domain:
                try:
                    # Mailgun API endpoint
                    url = f"https://api.mailgun.net/v3/{domain}/messages"

                    # Prepare the email data
                    email_data = {
                        "from": f"Find A Meeting Spot <noreply@{domain}>",
                        "to": email,
                        "subject": subject,
                        "text": body,
                        "html": body.replace("\n", "<br>"),  # Basic HTML conversion
                    }

                    # Send the email
                    current_app.logger.info(f"Sending email request to Mailgun")
                    response = requests.post(url, auth=("api", api_key), data=email_data)

                    # Log response
                    current_app.logger.info(f"Mailgun API response status code: {response.status_code}")

                    if response.status_code != 200:
                        current_app.logger.error(f"Mailgun API error: {response.text}")
                    else:
                        current_app.logger.info(f"Password reset email sent successfully to {email}")

                except Exception as email_error:
                    current_app.logger.error(f"Error sending reset email: {str(email_error)}")
            else:
                current_app.logger.warning("Email not sent - missing Mailgun configuration")

            # Return success for security reasons (don't reveal if email was sent)
            return jsonify({"message": success_message}), 200

        except Exception as db_error:
            current_app.logger.error(f"Database error in reset password: {str(db_error)}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        import traceback

        current_app.logger.error(f"Unhandled exception in reset password: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@v1_bp.route("/auth/me", methods=["GET", "OPTIONS"])
def get_current_user():
    """Get current user information directly without ORM models."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response

    # For GET requests, implement direct user lookup
    try:
        import traceback

        import jwt

        # Extract token from Authorization header directly
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            current_app.logger.warning("Missing or invalid Authorization header")
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

        # Get the token
        token = auth_header.replace("Bearer ", "")

        # Try to decode the token directly
        try:
            # Get the secret key from config
            secret_key = current_app.config.get("SECRET_KEY")
            if not secret_key:
                current_app.logger.error("SECRET_KEY not configured")
                return jsonify({"error": "Server configuration error"}), 500

            # Manually decode the token
            try:
                current_app.logger.info(f"Decoding token: {token[:10]}...")
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                current_user_id = payload.get("sub") or payload.get("user_id")

                if not current_user_id:
                    current_app.logger.warning("Could not extract user identity from token")
                    return jsonify({"error": "Invalid token", "message": "Invalid token"}), 401

                current_app.logger.info(f"Fetching user info for ID: {current_user_id}")

                # Direct SQL query to find user by ID
                stmt = text(
                    """
                    SELECT id, email, username, first_name, last_name, created_at, updated_at,
                           profile_picture_url, google_oauth_id, phone
                    FROM users WHERE id = :user_id
                """
                )

                user_data = db.session.execute(stmt, {"user_id": current_user_id}).fetchone()

                if not user_data:
                    current_app.logger.warning(f"User not found with ID: {current_user_id}")
                    return jsonify({"error": "User not found", "message": "User not found"}), 404

                # Convert row to dictionary
                result = {}
                for idx, col in enumerate(user_data.keys()):
                    # Convert values to strings as needed
                    value = user_data[idx]
                    if col in ["id", "created_at", "updated_at"] and value is not None:
                        result[col] = str(value)
                    else:
                        result[col] = value

                # Check if user has premium subscription
                try:
                    sub_stmt = text(
                        """
                        SELECT id, status, plan_type, current_period_end
                        FROM subscriptions
                        WHERE user_id = :user_id AND status = 'active'
                        ORDER BY created_at DESC LIMIT 1
                    """
                    )

                    subscription = db.session.execute(sub_stmt, {"user_id": current_user_id}).fetchone()

                    if subscription:
                        sub_dict = {}
                        for idx, col in enumerate(subscription.keys()):
                            value = subscription[idx]
                            if col in ["id", "current_period_end"] and value is not None:
                                sub_dict[col] = str(value)
                            else:
                                sub_dict[col] = value

                        result["subscription"] = sub_dict
                        result["is_premium"] = True
                    else:
                        result["is_premium"] = False

                except Exception as e:
                    current_app.logger.error(f"Error fetching subscription: {str(e)}")
                    result["is_premium"] = False

                return jsonify(result), 200

            except jwt.ExpiredSignatureError:
                current_app.logger.warning("Token has expired")
                return jsonify({"error": "Unauthorized", "message": "Token has expired"}), 401
            except jwt.InvalidTokenError as jwt_error:
                current_app.logger.error(f"Invalid token: {str(jwt_error)}")
                return jsonify({"error": "Unauthorized", "message": "Invalid token"}), 401

        except Exception as decode_error:
            current_app.logger.error(f"Error decoding token: {str(decode_error)}")
            return jsonify({"error": "Unauthorized", "message": "Invalid token format"}), 401

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error in /auth/me endpoint: {str(e)}\n{stack_trace}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@v1_bp.route("/auth/register/direct", methods=["GET", "POST", "OPTIONS"])
def direct_register_v1():
    """Direct register endpoint for v1 routes."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, handle registration directly
    try:
        import uuid
        from datetime import datetime, timezone

        from werkzeug.security import generate_password_hash

        from ..auth import generate_direct_token

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
            import traceback

            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error in direct register: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in direct register endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@v1_bp.route("/auth/register", methods=["GET", "POST", "OPTIONS"])
def register_v1():
    """Register endpoint for v1 routes that forwards to the auth blueprint."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the main auth blueprint
    from ..auth import register as auth_register

    try:
        return auth_register()
    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error forwarding to auth register: {str(e)}\n{stack_trace}")
        # If there's an error, try the direct register
        return direct_register_v1()


@v1_bp.route("/auth/login", methods=["GET", "POST", "OPTIONS"])
def login_v1():
    """Login endpoint for v1 routes that handles login directly."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    try:
        import traceback

        from werkzeug.security import check_password_hash

        from ..auth import generate_direct_token

        data = request.get_json() or {}

        # Log incoming request data (without password)
        safe_data = {k: v for k, v in data.items() if k != "password"} if data else {}
        current_app.logger.info(f"V1 Login attempt with data: {safe_data}")

        # Get credentials
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        password = data.get("password", "")

        if not email or not password:
            current_app.logger.warning("V1 Login failed: missing email or password")
            return jsonify({"error": "Email and password are required"}), 400

        # Check database connection
        try:
            # Basic connection test
            db.session.execute(text("SELECT 1")).fetchone()

            # Direct SQL query to find user
            stmt = text("SELECT id, email, password_hash FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": email}).fetchone()

            if not result:
                current_app.logger.warning(f"V1 Login failed: user not found for email {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Extract user data
            user_id, user_email, password_hash = result

            # Verify password directly
            if not check_password_hash(password_hash, password):
                current_app.logger.warning(f"V1 Login failed: incorrect password for user {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Generate token directly with extended expiry
            access_token = generate_direct_token(user_id, user_email)

            # Get additional user fields if possible
            user_data = {"id": str(user_id), "email": user_email}

            try:
                extended_query = text(
                    """
                    SELECT id, email, first_name, last_name, username, phone, profile_picture_url,
                           created_at, updated_at
                    FROM users WHERE id = :user_id
                """
                )
                extended_result = db.session.execute(extended_query, {"user_id": user_id}).fetchone()

                if extended_result:
                    for idx, col_name in enumerate(extended_result.keys()):
                        if extended_result[idx] is not None:
                            value = extended_result[idx]
                            if col_name in ["id", "created_at", "updated_at"]:
                                user_data[col_name] = str(value)
                            else:
                                user_data[col_name] = value
            except Exception as e:
                current_app.logger.warning(f"V1 Could not get extended user data: {str(e)}")

            # Success response
            current_app.logger.info(f"V1 Login successful for user {email}")
            response = jsonify({"message": "Login successful", "access_token": access_token, "user": user_data})
            return response, 200

        except Exception as db_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"V1 Database error in login: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"V1 Unhandled exception in login endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500


@v1_bp.route("/auth/login/direct", methods=["GET", "POST", "OPTIONS"])
def direct_login_v1():
    """Direct login endpoint for v1 routes."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the direct login in auth blueprint
    try:
        from ..auth import direct_login

        return direct_login()
    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error in direct login: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Error processing login", "message": str(e)}), 500


@v1_bp.route("/auth/google/callback", methods=["GET", "POST", "OPTIONS"])
def google_callback_v1():
    """Google authentication callback for v1 routes."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Max-Age", "3600")
        return response

    # For POST or GET requests, forward to the auth blueprint
    try:
        current_app.logger.info(f"Google callback received via {request.method}. Processing...")
        from ..auth import direct_google_callback

        return direct_google_callback()
    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error in Google callback: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Error authenticating with Google", "message": str(e)}), 500


@v1_bp.route("/auth/direct-login", methods=["GET", "POST", "OPTIONS"])
def standalone_direct_login():
    """Standalone direct login endpoint that doesn't depend on auth module."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Max-Age", "3600")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    try:
        import traceback
        import uuid
        from datetime import datetime, timedelta, timezone

        import jwt
        from werkzeug.security import check_password_hash

        data = request.get_json() or {}

        # Log incoming request data (without password)
        safe_data = {k: v for k, v in data.items() if k != "password"} if data else {}
        current_app.logger.info(f"Standalone direct login attempt with data: {safe_data}")

        # Get credentials
        email = data.get("email", "").lower().strip() if data.get("email") else ""
        password = data.get("password", "")

        if not email or not password:
            current_app.logger.warning("Standalone direct login failed: missing email or password")
            return jsonify({"error": "Email and password are required"}), 400

        # Check database connection
        try:
            # Basic connection test
            db.session.execute(text("SELECT 1")).fetchone()

            # Direct SQL query to find user
            stmt = text("SELECT id, email, password_hash FROM users WHERE email = :email")
            result = db.session.execute(stmt, {"email": email}).fetchone()

            if not result:
                current_app.logger.warning(f"Standalone direct login failed: user not found for email {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Extract user data
            user_id, user_email, password_hash = result

            # Verify password directly
            if not check_password_hash(password_hash, password):
                current_app.logger.warning(f"Standalone direct login failed: incorrect password for user {email}")
                return jsonify({"error": "Invalid credentials", "message": "Invalid email or password"}), 401

            # Generate JWT token directly
            secret_key = current_app.config.get("SECRET_KEY")
            if not secret_key:
                current_app.logger.error("SECRET_KEY not configured")
                return jsonify({"error": "Server error", "message": "Server configuration error"}), 500

            # Create expiration time (24 hours from now)
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(hours=24)

            # Create token payload
            payload = {"sub": str(user_id), "email": user_email, "iat": now, "exp": expiry}

            # Generate the JWT token
            access_token = jwt.encode(payload, secret_key, algorithm="HS256")

            # Get additional user fields if possible
            user_data = {"id": str(user_id), "email": user_email}

            try:
                extended_query = text(
                    """
                    SELECT id, email, first_name, last_name, username, phone, profile_picture_url,
                           created_at, updated_at
                    FROM users WHERE id = :user_id
                """
                )
                extended_result = db.session.execute(extended_query, {"user_id": user_id}).fetchone()

                if extended_result:
                    for idx, col_name in enumerate(extended_result.keys()):
                        if extended_result[idx] is not None:
                            value = extended_result[idx]
                            if col_name in ["id", "created_at", "updated_at"]:
                                user_data[col_name] = str(value)
                            else:
                                user_data[col_name] = value
            except Exception as e:
                current_app.logger.warning(f"Standalone direct login: Could not get extended user data: {str(e)}")

            # Success response
            current_app.logger.info(f"Standalone direct login successful for user {email}")
            response = jsonify({"message": "Login successful", "access_token": access_token, "user": user_data})
            return response, 200

        except Exception as db_error:
            stack_trace = traceback.format_exc()
            current_app.logger.error(f"Database error in standalone direct login: {str(db_error)}\n{stack_trace}")
            return jsonify({"error": "Server error", "message": "Database error"}), 500

    except Exception as e:
        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Unhandled exception in standalone direct login endpoint: {str(e)}\n{stack_trace}")
        return jsonify({"error": "Server error", "message": "An unexpected error occurred"}), 500
