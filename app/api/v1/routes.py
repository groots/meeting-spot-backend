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
@v1_bp.route("/auth/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    """Handle password reset request."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the main auth blueprint
    from ..auth import reset_password as auth_reset_password

    return auth_reset_password()


@v1_bp.route("/auth/me", methods=["GET", "OPTIONS"])
def get_current_user():
    """Get current user information directly without ORM models."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "GET, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For GET requests, implement direct user lookup
    try:
        # Import JWT modules
        from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request

        # Extract token from Authorization header directly
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            current_app.logger.warning("Missing or invalid Authorization header")
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

        # Get the token
        token = auth_header.replace("Bearer ", "")

        try:
            # Verify the token manually
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()

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
                result[col] = user_data[idx]

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
                        sub_dict[col] = subscription[idx]

                    result["subscription"] = sub_dict
                    result["is_premium"] = True
                else:
                    result["is_premium"] = False

            except Exception as e:
                current_app.logger.error(f"Error fetching subscription: {str(e)}")
                result["is_premium"] = False

            return jsonify(result), 200

        except Exception as jwt_error:
            current_app.logger.error(f"JWT validation error: {str(jwt_error)}")
            return jsonify({"error": "Unauthorized", "message": "Invalid or expired token"}), 401

    except Exception as e:
        current_app.logger.error(f"Error in /auth/me endpoint: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@v1_bp.route("/auth/register/direct", methods=["POST", "OPTIONS"])
def direct_register_v1():
    """Direct register endpoint for v1 routes."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
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


@v1_bp.route("/auth/register", methods=["POST", "OPTIONS"])
def register_v1():
    """Register endpoint for v1 routes that forwards to the auth blueprint."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
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


@v1_bp.route("/auth/login", methods=["POST", "OPTIONS"])
def login_v1():
    """Login endpoint for v1 routes that forwards to the auth blueprint."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the main auth blueprint
    from ..auth import login as auth_login

    try:
        return auth_login()
    except Exception as e:
        import traceback

        stack_trace = traceback.format_exc()
        current_app.logger.error(f"Error forwarding to auth login: {str(e)}\n{stack_trace}")
        # If there's an error, try the direct login
        return direct_login_v1()


@v1_bp.route("/auth/login/direct", methods=["POST", "OPTIONS"])
def direct_login_v1():
    """Direct login endpoint for v1 routes."""
    # Handle OPTIONS request for CORS preflight
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response

    # For POST requests, forward to the direct login in auth blueprint
    from ..auth import direct_login

    return direct_login()
