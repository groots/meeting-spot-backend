"""API blueprints for the application."""

import os
import uuid
from datetime import datetime, timedelta, timezone

import psutil
from flask import Blueprint, current_app, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus
from ..utils.notifications import send_email
from .auth import api as auth_ns
from .contacts import api as contacts_ns
from .meeting_requests import api as meeting_requests_ns
from .payments import api as payments_ns
from .users import api as users_ns
from .v1.cors import cors_ns
from .v1.subscriptions import api as subscriptions_ns

# Create API v1 blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Create API v2 blueprint
api_v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")

# Create a limiter instance
limiter = Limiter(key_func=get_remote_address)

# Create debug blueprint
debug_bp = Blueprint("debug", __name__, url_prefix="/debug")


@debug_bp.route("/health")
def health_check():
    """Comprehensive health check endpoint."""
    health_data = {
        "status": "initializing",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": current_app.config.get("ENV", "unknown"),
        "debug_mode": current_app.debug,
        "components": {},
    }

    # Check database connectivity
    try:
        # Simple query to check database connection
        db_version = db.session.execute(text("SELECT version()")).scalar()
        health_data["components"]["database"] = {
            "status": "healthy",
            "version": db_version,
            "uri": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                # Mask password in the returned URL for security
                ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                ":*****@",
            )
            if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
            else "Not set",
        }
    except SQLAlchemyError as e:
        health_data["components"]["database"] = {"status": "unhealthy", "error": str(e)}

    # Check system resources
    try:
        health_data["components"]["system"] = {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
        }
    except Exception as e:
        health_data["components"]["system"] = {"status": "error", "error": str(e)}

    # Check configuration
    health_data["components"]["configuration"] = {
        "cors_origins": current_app.config.get("CORS_ORIGINS"),
        "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
        "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
        "jwt_secret_key_set": bool(current_app.config.get("JWT_SECRET_KEY")),
        "security_headers": bool(current_app.config.get("SECURITY_HEADERS")),
    }

    # Check CORS configuration
    health_data["components"]["cors"] = {
        "enabled": True,
        "allowed_origins": current_app.config.get("CORS_ORIGINS"),
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_credentials": True,
        "max_age": 3600,
    }

    # Determine overall status
    if all(
        comp.get("status", "healthy") == "healthy"
        for comp in health_data["components"].values()
        if isinstance(comp, dict) and "status" in comp
    ):
        health_data["status"] = "healthy"
    else:
        health_data["status"] = "degraded"

    response = jsonify(health_data)

    # Add CORS headers directly to this response
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            current_app.logger.info(f"Added direct CORS headers to health endpoint response for origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for health endpoint: {origin}")

    return response


# Add a test route directly to the blueprint
@api_v1_bp.route("/test/")
def test_route():
    return jsonify({"message": "API v1 test route working"})


# Add an email test route
@debug_bp.route("/test-email")
def test_email():
    try:
        result = send_email(
            "squish.roots@gmail.com",
            "Test Email from Find A Meeting Spot",
            "This is a test email sent from the development environment using Mailgun with mg.findameetingspot.com domain.",
        )
        if result:
            return jsonify({"message": "Email sent successfully"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Create API v1 instance
api_v1 = Api(
    api_v1_bp,
    version="1.0",
    title="Find a Meeting Spot API v1",
    description="API v1 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Create API v2 instance
api_v2 = Api(
    api_v2_bp,
    version="2.0",
    title="Find a Meeting Spot API v2",
    description="API v2 for finding meeting spots between two locations",
    doc="/docs",  # Always enable Swagger UI
    serve_challenge_on_401=True,
    default_mediatype="application/json",
    catch_all_404s=True,
)

# Register namespaces for v1
api_v1.add_namespace(auth_ns, path="/auth")
api_v1.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v1.add_namespace(users_ns, path="/users")
api_v1.add_namespace(cors_ns, path="/cors")
api_v1.add_namespace(payments_ns, path="/payments")
api_v1.add_namespace(contacts_ns, path="/contacts")
api_v1.add_namespace(subscriptions_ns, path="/subscriptions")

# Register namespaces for v2
api_v2.add_namespace(auth_ns, path="/auth")
api_v2.add_namespace(meeting_requests_ns, path="/meeting-requests")
api_v2.add_namespace(users_ns, path="/users")
api_v2.add_namespace(payments_ns, path="/payments")
api_v2.add_namespace(contacts_ns, path="/contacts")

# No need to import routes since we're using Flask-RESTX namespaces


@debug_bp.route("/db-check")
def db_check():
    """Check database connectivity."""
    try:
        # Attempt to execute a simple query
        db_version = db.session.execute(text("SELECT version()")).scalar()
        response = jsonify(
            {
                "status": "success",
                "message": "Database connection successful",
                "db_version": db_version,
                "database_url": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                    # Mask password in the returned URL for security
                    ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                    ":*****@",
                )
                if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
                else current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set"),
                "flask_env": current_app.config.get("ENV", "Not set"),
                "debug_mode": current_app.debug,
                "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
                "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
            }
        )

        # Add CORS headers directly to this response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            current_app.logger.info(f"Added direct CORS headers to db-check response for origin: {origin}")

        return response
    except SQLAlchemyError as e:
        error_response = (
            jsonify(
                {
                    "status": "error",
                    "message": "Database connection failed",
                    "error": str(e),
                    "database_url": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                        # Mask password in the returned URL for security
                        ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                        ":*****@",
                    )
                    if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
                    else current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set"),
                    "flask_env": current_app.config.get("ENV", "Not set"),
                    "debug_mode": current_app.debug,
                    "encryption_key_set": bool(current_app.config.get("ENCRYPTION_KEY")),
                    "google_maps_api_key_set": bool(current_app.config.get("GOOGLE_MAPS_API_KEY")),
                }
            ),
            500,
        )

        # Add CORS headers to error response too
        origin = request.headers.get("Origin")
        if origin:
            error_response[0].headers["Access-Control-Allow-Origin"] = origin
            error_response[0].headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            error_response[0].headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            error_response[0].headers["Access-Control-Allow-Credentials"] = "true"

        return error_response


@debug_bp.route("/db-check", methods=["OPTIONS"])
def db_check_options():
    """Handle OPTIONS requests for db-check endpoint."""
    response = current_app.make_default_options_response()
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            current_app.logger.info(f"Added CORS headers to OPTIONS response for /debug/db-check, origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for db-check OPTIONS: {origin}")
    return response


@debug_bp.route("/health", methods=["OPTIONS"])
def health_options():
    """Handle OPTIONS requests for health endpoint."""
    response = current_app.make_default_options_response()
    origin = request.headers.get("Origin")
    if origin:
        allowed_origins = current_app.config.get("CORS_ORIGINS", [])
        if "*" in allowed_origins or origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            current_app.logger.info(f"Added CORS headers to OPTIONS response for /debug/health, origin: {origin}")
        else:
            current_app.logger.info(f"Origin not allowed for health OPTIONS: {origin}")
    return response


@debug_bp.route("/fix-schema")
def fix_schema():
    """Fix database schema by adding the selected_place_id column to meeting_requests."""
    try:
        # Use raw SQL to add the column with SQLAlchemy's text function
        query = text("ALTER TABLE meeting_requests ADD COLUMN IF NOT EXISTS selected_place_id UUID;")
        result = db.session.execute(query)
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "message": "Added selected_place_id column to meeting_requests table",
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error fixing schema: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                }
            ),
            500,
        )


@debug_bp.route("/check-tables")
def check_tables():
    """Check if specific database tables exist."""
    try:
        # Get all table names in the public schema
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        # Create response with table existence information
        response_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tables": tables,
            "table_exists": {
                "password_resets": "password_resets" in tables,
                "meeting_contacts": "meeting_contacts" in tables,
                "users": "users" in tables,
                "subscriptions": "subscriptions" in tables,
                "meeting_requests": "meeting_requests" in tables,
                "contacts": "contacts" in tables,
                "places": "places" in tables,
            },
            "database_info": {
                "uri": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not set").replace(
                    # Mask password in the returned URL for security
                    ":" + current_app.config.get("SQLALCHEMY_DATABASE_URI", "").split(":")[2].split("@")[0] + "@",
                    ":*****@",
                )
                if ":" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
                else "Not set"
            },
        }

        # If password_resets table doesn't exist, add migration information
        if not response_data["table_exists"]["password_resets"]:
            response_data["migration_help"] = {
                "message": "The password_resets table is missing. This is likely because the migration that creates this table hasn't been applied.",
                "suggested_fix": "Run 'flask db upgrade' to apply all pending migrations.",
            }

        response = jsonify(response_data)

        # Add CORS headers directly to this response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@debug_bp.route("/check-tables", methods=["OPTIONS"])
def check_tables_options():
    """Handle OPTIONS requests for the check-tables endpoint."""
    response = jsonify({"status": "ok"})

    # Add CORS headers
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"

    return response


@debug_bp.route("/apply-migrations")
def apply_migrations():
    """Apply missing database migrations."""
    try:
        from flask_migrate import upgrade

        # Log before starting
        current_app.logger.info("Starting migration application via debug endpoint")

        # Get current migration status
        inspector = inspect(db.engine)
        tables_before = inspector.get_table_names()

        # Apply all migrations
        with current_app.app_context():
            upgrade()

        # Check what changed
        inspector = inspect(db.engine)
        tables_after = inspector.get_table_names()
        new_tables = [table for table in tables_after if table not in tables_before]

        # Build response
        response_data = {
            "status": "success",
            "message": "Migrations applied successfully",
            "tables": {"before": tables_before, "after": tables_after, "new_tables": new_tables},
        }

        response = jsonify(response_data)

        # Add CORS headers directly to this response
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
    except Exception as e:
        current_app.logger.error(f"Error applying migrations: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to apply migrations", "error": str(e)}), 500


@debug_bp.route("/apply-migrations", methods=["OPTIONS"])
def apply_migrations_options():
    """Handle OPTIONS requests for the apply-migrations endpoint."""
    response = jsonify({"status": "ok"})

    # Add CORS headers
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"

    return response


@debug_bp.route("/fix-production-tables")
def fix_production_tables():
    """Fix production database tables by creating them in the correct order."""
    try:
        import uuid

        from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, MetaData, String, Table, Text
        from sqlalchemy.dialects.postgresql import UUID

        current_app.logger.info("Starting fix-production-tables process")

        # Get current table status
        inspector = inspect(db.engine)
        tables_before = inspector.get_table_names()
        current_app.logger.info(f"Tables before: {tables_before}")

        # Check if users table exists
        if "users" not in tables_before:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Critical error: 'users' table not found in database",
                        "error": "The 'users' table must exist before other tables can be created. Please ensure the initial migration that creates the users table has been applied.",
                        "tables_found": tables_before,
                    }
                ),
                500,
            )

        # Create metadata for new tables
        metadata = MetaData(schema=None)  # Explicitly use default schema
        engine = db.engine

        # First, check the structure of the users table to get the correct column types
        users_columns = inspector.get_columns("users")
        users_column_names = [col["name"] for col in users_columns]
        users_pk = inspector.get_pk_constraint("users")
        users_pk_cols = users_pk.get("constrained_columns", [])

        current_app.logger.info(f"Users table columns: {users_column_names}")
        current_app.logger.info(f"Users primary key: {users_pk_cols}")

        # Is 'id' the primary key?
        if "id" not in users_pk_cols:
            current_app.logger.warning(
                f"Warning: 'id' is not the primary key in users table. Primary key is: {users_pk_cols}"
            )

        # Check if the id column is a UUID
        id_column_type = next((col["type"] for col in users_columns if col["name"] == "id"), None)
        current_app.logger.info(f"Users table 'id' column type: {id_column_type}")

        # Define tables that need to be created
        tables_to_create = []

        # 1. First check and create contacts table if it doesn't exist
        if "contacts" not in tables_before:
            current_app.logger.info("Creating contacts table")
            contacts = Table(
                "contacts",
                metadata,
                Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                Column("name", String(255), nullable=False),
                Column("email", String(255), nullable=True),
                Column("phone", String(50), nullable=True),
                Column("company", String(255), nullable=True),
                Column("notes", Text, nullable=True),
                Column("created_at", DateTime(timezone=True), nullable=False, server_default=db.func.now()),
                Column("updated_at", DateTime(timezone=True), nullable=True),
            )
            tables_to_create.append(contacts)

        # 2. Check and create password_resets table
        if "password_resets" not in tables_before:
            current_app.logger.info("Creating password_resets table")
            password_resets = Table(
                "password_resets",
                metadata,
                Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                Column("token", String(255), unique=True, nullable=False),
                Column("created_at", DateTime, nullable=False, server_default=db.func.now()),
                Column("expires_at", DateTime, nullable=False),
                Column("used", Boolean, default=False, nullable=False),
            )
            tables_to_create.append(password_resets)

        # 3. Check and create places table
        if "places" not in tables_before:
            current_app.logger.info("Creating places table")
            places = Table(
                "places",
                metadata,
                Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column("name", String(255), nullable=False),
                Column("address", String(255), nullable=False),
                Column("latitude", Float, nullable=False),
                Column("longitude", Float, nullable=False),
                Column("google_place_id", String(255), unique=True, nullable=True),
                Column(
                    "suggested_by_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
                ),
                Column("created_at", DateTime(timezone=True), nullable=False, server_default=db.func.now()),
                Column("updated_at", DateTime(timezone=True), nullable=True),
            )
            tables_to_create.append(places)

        # 4. Check and create subscriptions table
        if "subscriptions" not in tables_before:
            current_app.logger.info("Creating subscriptions table")
            subscriptions = Table(
                "subscriptions",
                metadata,
                Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
                Column("stripe_subscription_id", String(255), unique=True, nullable=True),
                Column("stripe_customer_id", String(255), nullable=True),
                Column("plan_id", String(50), nullable=False),
                Column("status", String(50), nullable=False),
                Column("current_period_start", DateTime(timezone=True), nullable=True),
                Column("current_period_end", DateTime(timezone=True), nullable=True),
                Column("cancel_at_period_end", Boolean, default=False),
                Column("created_at", DateTime(timezone=True), nullable=False, server_default=db.func.now()),
                Column("updated_at", DateTime(timezone=True), nullable=False, server_default=db.func.now()),
            )
            tables_to_create.append(subscriptions)

        # 5. Now that we know contacts exists, create meeting_contacts table
        if "meeting_requests" in tables_before:
            if "contacts" in tables_before or "contacts" in [t.name for t in tables_to_create]:
                if "meeting_contacts" not in tables_before:
                    current_app.logger.info("Creating meeting_contacts table")
                    meeting_contacts = Table(
                        "meeting_contacts",
                        metadata,
                        Column(
                            "meeting_request_id",
                            UUID(as_uuid=True),
                            ForeignKey("meeting_requests.request_id", ondelete="CASCADE"),
                            primary_key=True,
                        ),
                        Column(
                            "contact_id",
                            UUID(as_uuid=True),
                            ForeignKey("contacts.id", ondelete="CASCADE"),
                            primary_key=True,
                        ),
                        Column("created_at", DateTime(timezone=True), nullable=False, server_default=db.func.now()),
                    )
                    tables_to_create.append(meeting_contacts)
        else:
            current_app.logger.warning(
                "Cannot create meeting_contacts table because meeting_requests table does not exist"
            )

        # 6. Create meeting_request_suggested_places table if needed
        if "meeting_requests" in tables_before:
            if "places" in tables_before or "places" in [t.name for t in tables_to_create]:
                if "meeting_request_suggested_places" not in tables_before:
                    current_app.logger.info("Creating meeting_request_suggested_places table")
                    meeting_request_suggested_places = Table(
                        "meeting_request_suggested_places",
                        metadata,
                        Column(
                            "meeting_request_id",
                            UUID(as_uuid=True),
                            ForeignKey("meeting_requests.request_id", ondelete="CASCADE"),
                        ),
                        Column("place_id", UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE")),
                        Column("created_at", DateTime, server_default=db.func.now()),
                    )
                    tables_to_create.append(meeting_request_suggested_places)
        else:
            current_app.logger.warning(
                "Cannot create meeting_request_suggested_places table because meeting_requests table does not exist"
            )

        # Create the tables in the order they were added
        for table in tables_to_create:
            current_app.logger.info(f"Creating table: {table.name}")
            try:
                table.create(engine, checkfirst=True)
                current_app.logger.info(f"Successfully created table: {table.name}")
            except Exception as e:
                current_app.logger.error(f"Error creating table {table.name}: {str(e)}")
                # Continue with other tables even if one fails

        # Get updated table status
        inspector = inspect(db.engine)
        tables_after = inspector.get_table_names()

        # Build response
        response_data = {
            "status": "success",
            "message": "Database tables fixed successfully",
            "tables_created": [t.name for t in tables_to_create],
            "tables": {
                "before": tables_before,
                "after": tables_after,
                "new_tables": [t for t in tables_after if t not in tables_before],
            },
            "users_table_info": {"columns": users_column_names, "primary_key": users_pk_cols},
        }

        current_app.logger.info(f"Tables fixed successfully: {response_data['tables_created']}")

        # Update alembic_version table to mark these migrations as applied
        if tables_to_create and len(response_data["new_tables"]) > 0:
            try:
                with engine.connect() as conn:
                    # Use the latest migration revision as the current version
                    # This will mark all migrations as applied
                    conn.execute(text("UPDATE alembic_version SET version_num = '84151472c340'"))
                    conn.commit()
                    response_data["alembic_version_updated"] = True
                    current_app.logger.info("Updated alembic_version table to latest revision")
            except Exception as e:
                current_app.logger.error(f"Error updating alembic_version: {str(e)}")
                response_data["alembic_version_updated"] = False
                response_data["alembic_error"] = str(e)

        response = jsonify(response_data)

        # Add CORS headers
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response
    except Exception as e:
        current_app.logger.error(f"Error fixing production tables: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to fix production tables", "error": str(e)}), 500


@debug_bp.route("/fix-production-tables", methods=["OPTIONS"])
def fix_production_tables_options():
    """Handle OPTIONS requests for the fix-production-tables endpoint."""
    response = jsonify({"status": "ok"})

    # Add CORS headers
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"

    return response


# Register debug blueprint with the app
def init_app(app):
    """Initialize API blueprints with the Flask app."""
    # Set up rate limiting
    limiter.init_app(app)

    # Register API blueprints
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(api_v2_bp)

    # Register debug endpoints
    app.register_blueprint(debug_bp)

    return app
