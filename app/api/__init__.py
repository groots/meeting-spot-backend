"""API blueprints for the application."""

import json
import logging
import os
import re
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, Union

import psutil
from flask import Blueprint, Response, current_app, g, jsonify, render_template, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import class_mapper

from .. import db
from ..models import ContactType, MeetingRequest, MeetingRequestStatus, User
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

# Global variables for request tracking and performance monitoring
_request_history = []
_request_lock = threading.Lock()
_max_requests = 100
_performance_metrics = {"endpoints": {}, "start_time": time.time()}
_performance_lock = threading.Lock()


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

        # First, try to fix the users.password_hash column length issue
        try:
            current_app.logger.info("Checking password_hash column length in users table")
            # Get the column info
            columns = inspector.get_columns("users")
            password_hash_col = next((col for col in columns if col["name"] == "password_hash"), None)

            if password_hash_col:
                # Try to determine the current length
                col_type_str = str(password_hash_col["type"])
                current_app.logger.info(f"Current password_hash column type: {col_type_str}")

                # If it's VARCHAR(128), upgrade it to VARCHAR(256)
                if "128" in col_type_str:
                    current_app.logger.info("Increasing password_hash column length to 256")
                    db.session.execute(text("ALTER TABLE users ALTER COLUMN password_hash TYPE varchar(256)"))
                    db.session.commit()
                    current_app.logger.info("Successfully updated password_hash column length")
        except Exception as e:
            current_app.logger.error(f"Error updating password_hash column: {str(e)}")
            # Continue even if this fails

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

        # Calculate new tables
        new_tables = [t for t in tables_after if t not in tables_before]

        # Build response
        response_data = {
            "status": "success",
            "message": "Database tables fixed successfully",
            "tables_created": [t.name for t in tables_to_create],
            "tables": {
                "before": tables_before,
                "after": tables_after,
                "new_tables": new_tables,
            },
            "users_table_info": {"columns": users_column_names, "primary_key": users_pk_cols},
        }

        current_app.logger.info(f"Tables fixed successfully: {response_data['tables_created']}")

        # Update alembic_version table to mark these migrations as applied
        if tables_to_create and len(new_tables) > 0:
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


@debug_bp.route("/check-database")
def check_database():
    """Comprehensive check of database status"""
    try:
        response_data = {
            "status": "running checks",
            "database_info": {},
            "tables": {},
            "schema_issues": [],
            "last_errors": [],
            "migrations": {},
        }

        # Basic connection check
        try:
            db.session.execute(text("SELECT 1"))
            response_data["database_info"]["connection"] = "OK"
        except Exception as e:
            response_data["database_info"]["connection"] = "FAILED"
            response_data["database_info"]["connection_error"] = str(e)
            return jsonify(response_data), 500

        # Get database info
        try:
            result = db.session.execute(text("SELECT version()")).scalar()
            response_data["database_info"]["version"] = result
        except Exception as e:
            response_data["database_info"]["version_error"] = str(e)

        # Get current schema name
        try:
            result = db.session.execute(text("SELECT current_schema()")).scalar()
            response_data["database_info"]["current_schema"] = result
        except Exception as e:
            response_data["database_info"]["schema_error"] = str(e)

        # List all schemas
        try:
            results = db.session.execute(text("SELECT schema_name FROM information_schema.schemata")).fetchall()
            response_data["database_info"]["schemas"] = [r[0] for r in results]
        except Exception as e:
            response_data["database_info"]["schemas_error"] = str(e)

        # Get table list
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        response_data["tables"]["list"] = tables

        # Get data about crucial tables
        crucial_tables = ["users", "password_resets", "contacts", "meeting_requests", "subscriptions"]
        for table in crucial_tables:
            if table in tables:
                try:
                    # Get column info
                    columns = inspector.get_columns(table)
                    col_info = [
                        {"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]} for col in columns
                    ]

                    # Get foreign keys
                    fks = inspector.get_foreign_keys(table)

                    # Get row count
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

                    response_data["tables"][table] = {
                        "exists": True,
                        "columns": col_info,
                        "foreign_keys": fks,
                        "row_count": count,
                    }
                except Exception as e:
                    response_data["tables"][table] = {"exists": True, "error": str(e)}
            else:
                response_data["tables"][table] = {"exists": False}
                response_data["schema_issues"].append(f"Missing table: {table}")

        # Check migrations
        try:
            # Check alembic_version table
            if "alembic_version" in tables:
                version = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
                response_data["migrations"]["current_version"] = version

                # Get all migration scripts from the filesystem
                # This won't work in production, but will work in dev
                try:
                    migrations_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "migrations", "versions"
                    )
                    migration_files = os.listdir(migrations_dir) if os.path.exists(migrations_dir) else []
                    response_data["migrations"]["available_files"] = migration_files
                except Exception as e:
                    response_data["migrations"]["files_error"] = str(e)
            else:
                response_data["migrations"]["error"] = "alembic_version table does not exist"
                response_data["schema_issues"].append("Missing alembic_version table")
        except Exception as e:
            response_data["migrations"]["error"] = str(e)

        # Check recent application logs
        try:
            # Only works if running in a container or VM where logs are accessible
            log_path = os.environ.get("APP_LOG_PATH", "/var/log/app.log")
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    # Get last 20 lines with ERROR or CRITICAL
                    error_lines = []
                    for line in f.readlines()[-1000:]:
                        if "ERROR" in line or "CRITICAL" in line:
                            error_lines.append(line.strip())
                    response_data["last_errors"] = error_lines[-20:] if error_lines else []
        except Exception as e:
            response_data["log_error"] = str(e)

        # Return response
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
        return jsonify({"status": "error", "message": "Failed to check database", "error": str(e)}), 500


@debug_bp.route("/sql-fix")
def sql_fix():
    """Apply direct SQL fixes to fix critical database issues."""
    try:
        results = {"status": "success", "steps": []}

        # Fix password_hash column length
        try:
            db.session.execute(text("ALTER TABLE users ALTER COLUMN password_hash TYPE varchar(256)"))
            db.session.commit()
            results["steps"].append(
                {
                    "action": "alter_column",
                    "result": "success",
                    "details": "Updated password_hash column to VARCHAR(256)",
                }
            )
        except Exception as e:
            results["steps"].append({"action": "alter_column", "result": "error", "details": str(e)})

        # Create password_resets table if it doesn't exist
        try:
            db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS password_resets (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE NOT NULL
                )
            """
                )
            )
            db.session.commit()
            results["steps"].append(
                {"action": "create_table", "result": "success", "details": "Created password_resets table"}
            )
        except Exception as e:
            results["steps"].append(
                {"action": "create_table", "result": "error", "details": str(e), "table": "password_resets"}
            )

        # Create contacts table if it doesn't exist
        try:
            db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS contacts (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    company VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """
                )
            )
            db.session.commit()
            results["steps"].append(
                {"action": "create_table", "result": "success", "details": "Created contacts table"}
            )
        except Exception as e:
            results["steps"].append(
                {"action": "create_table", "result": "error", "details": str(e), "table": "contacts"}
            )

        # Create meeting_contacts table if it doesn't exist
        try:
            db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS meeting_contacts (
                    meeting_request_id UUID REFERENCES meeting_requests(request_id) ON DELETE CASCADE,
                    contact_id UUID REFERENCES contacts(id) ON DELETE CASCADE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    PRIMARY KEY (meeting_request_id, contact_id)
                )
            """
                )
            )
            db.session.commit()
            results["steps"].append(
                {"action": "create_table", "result": "success", "details": "Created meeting_contacts table"}
            )
        except Exception as e:
            results["steps"].append(
                {"action": "create_table", "result": "error", "details": str(e), "table": "meeting_contacts"}
            )

        # Create subscriptions table if it doesn't exist
        try:
            db.session.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    stripe_subscription_id VARCHAR(255) UNIQUE,
                    stripe_customer_id VARCHAR(255),
                    plan_id VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    current_period_start TIMESTAMP WITH TIME ZONE,
                    current_period_end TIMESTAMP WITH TIME ZONE,
                    cancel_at_period_end BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """
                )
            )
            db.session.commit()
            results["steps"].append(
                {"action": "create_table", "result": "success", "details": "Created subscriptions table"}
            )
        except Exception as e:
            results["steps"].append(
                {"action": "create_table", "result": "error", "details": str(e), "table": "subscriptions"}
            )

        # Update alembic version
        try:
            db.session.execute(text("UPDATE alembic_version SET version_num = '84151472c340'"))
            db.session.commit()
            results["steps"].append(
                {"action": "update_migration", "result": "success", "details": "Updated alembic_version to latest"}
            )
        except Exception as e:
            results["steps"].append({"action": "update_migration", "result": "error", "details": str(e)})

        # Add CORS headers
        response = jsonify(results)
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to apply SQL fixes", "error": str(e)}), 500


@debug_bp.route("/emergency-fix")
def emergency_fix():
    """Last-resort fix for critical database issues with detailed error logging."""
    results = {"status": "success", "steps": [], "details": {}}

    try:
        # Step 1: Get database connection info
        try:
            conn_info = db.engine.url
            results["details"]["connection"] = str(conn_info).replace(
                conn_info.password, "*****" if conn_info.password else ""
            )
            results["steps"].append({"step": "check_connection", "status": "success"})
        except Exception as e:
            results["steps"].append({"step": "check_connection", "status": "error", "message": str(e)})

        # Step 2: Check if we can execute basic SQL
        try:
            test_sql = db.session.execute(text("SELECT 1 as test")).scalar()
            results["details"]["basic_sql"] = test_sql
            results["steps"].append({"step": "basic_sql", "status": "success"})
        except Exception as e:
            results["steps"].append({"step": "basic_sql", "status": "error", "message": str(e)})

        # Step 3: Get current user role & permissions
        try:
            role_info = db.session.execute(text("SELECT current_user, current_database(), session_user")).fetchone()
            results["details"]["current_user"] = role_info[0]
            results["details"]["current_database"] = role_info[1]
            results["details"]["session_user"] = role_info[2]
            results["steps"].append({"step": "check_role", "status": "success"})
        except Exception as e:
            results["steps"].append({"step": "check_role", "status": "error", "message": str(e)})

        # Step 4: Check users table
        try:
            users_info = db.session.execute(
                text(
                    """
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_hash'
            """
                )
            ).fetchone()

            if users_info:
                results["details"]["password_hash_info"] = {"data_type": users_info[1], "max_length": users_info[2]}

                # If password_hash column is too small, try to fix it
                if users_info[2] < 256:
                    try:
                        # First try with ALTER command
                        db.session.execute(text("ALTER TABLE users ALTER COLUMN password_hash TYPE varchar(256)"))
                        db.session.commit()
                        results["steps"].append({"step": "fix_password_hash", "status": "success", "method": "alter"})
                    except Exception as e1:
                        # If ALTER fails, try with a function that creates a new column
                        try:
                            # Roll back the failed transaction
                            db.session.rollback()

                            # Create a function to handle the column size increase
                            db.session.execute(
                                text(
                                    """
                                CREATE OR REPLACE FUNCTION increase_password_hash_length() RETURNS void AS $$
                                BEGIN
                                    -- Add a new column
                                    ALTER TABLE users ADD COLUMN password_hash_new VARCHAR(256);

                                    -- Copy data
                                    UPDATE users SET password_hash_new = password_hash;

                                    -- Drop old column
                                    ALTER TABLE users DROP COLUMN password_hash;

                                    -- Rename new column
                                    ALTER TABLE users RENAME COLUMN password_hash_new TO password_hash;
                                END;
                                $$ LANGUAGE plpgsql;
                            """
                                )
                            )

                            # Execute the function
                            db.session.execute(text("SELECT increase_password_hash_length()"))
                            db.session.commit()

                            # Drop the function
                            db.session.execute(text("DROP FUNCTION increase_password_hash_length()"))
                            db.session.commit()

                            results["steps"].append(
                                {"step": "fix_password_hash", "status": "success", "method": "function"}
                            )
                        except Exception as e2:
                            db.session.rollback()
                            results["steps"].append(
                                {
                                    "step": "fix_password_hash",
                                    "status": "error",
                                    "message": f"ALTER error: {str(e1)}, Function error: {str(e2)}",
                                }
                            )
            else:
                results["steps"].append(
                    {"step": "check_users_table", "status": "error", "message": "password_hash column not found"}
                )
        except Exception as e:
            results["steps"].append({"step": "check_users_table", "status": "error", "message": str(e)})

        # Step 5: Create password_resets table if missing
        try:
            tables = db.session.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'password_resets'
            """
                )
            ).fetchone()

            if not tables:
                try:
                    db.session.execute(
                        text(
                            """
                        CREATE TABLE IF NOT EXISTS password_resets (
                            id UUID PRIMARY KEY,
                            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            token VARCHAR(255) UNIQUE NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            expires_at TIMESTAMP NOT NULL,
                            used BOOLEAN DEFAULT FALSE NOT NULL
                        )
                    """
                        )
                    )
                    db.session.commit()
                    results["steps"].append({"step": "create_password_resets", "status": "success"})
                except Exception as e:
                    db.session.rollback()
                    results["steps"].append({"step": "create_password_resets", "status": "error", "message": str(e)})
            else:
                results["steps"].append(
                    {"step": "check_password_resets", "status": "success", "message": "Table exists"}
                )
        except Exception as e:
            results["steps"].append({"step": "check_password_resets", "status": "error", "message": str(e)})

        # Step 6: Check final schema state
        try:
            # Get updated password_hash info
            updated_info = db.session.execute(
                text(
                    """
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_hash'
            """
                )
            ).fetchone()

            if updated_info:
                results["details"]["updated_password_hash"] = {
                    "data_type": updated_info[1],
                    "max_length": updated_info[2],
                }

            # Check all tables
            tables = db.session.execute(
                text(
                    """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """
                )
            ).fetchall()

            results["details"]["tables"] = [t[0] for t in tables]
            results["steps"].append({"step": "final_check", "status": "success"})
        except Exception as e:
            results["steps"].append({"step": "final_check", "status": "error", "message": str(e)})

        return jsonify(results)
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        return jsonify(results)


@debug_bp.route("/debug-reset-password")
def debug_reset_password():
    """Debug the reset-password endpoint flow"""
    try:
        from app.models.password_reset import PasswordReset
        from app.models.user import User

        results = {"status": "success", "tests": [], "reset_flow": {}}

        # Step 1: Check if we can import and use the PasswordReset model
        try:
            reset_model_info = {
                "module": str(PasswordReset.__module__),
                "class": PasswordReset.__name__,
                "tablename": getattr(PasswordReset, "__tablename__", "unknown"),
                "methods": [
                    m for m in dir(PasswordReset) if not m.startswith("_") and callable(getattr(PasswordReset, m))
                ],
            }
            results["reset_flow"]["model_info"] = reset_model_info
            results["tests"].append({"test": "check_model", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_model", "status": "error", "message": str(e)})

        # Step 2: Check if we can query the table
        try:
            # Try to create a sample token (but don't save it)
            import secrets
            from datetime import datetime, timedelta

            sample_token = secrets.token_urlsafe(32)
            sample_reset = PasswordReset(
                user_id="00000000-0000-0000-0000-000000000000", token=sample_token, expires_in=1  # Dummy ID  # 1 hour
            )

            # Check if the token was created properly
            token_info = {
                "token_length": len(sample_token),
                "token_format": sample_token[:10] + "...",
                "expires_at": str(sample_reset.expires_at) if hasattr(sample_reset, "expires_at") else "unknown",
                "used": sample_reset.used if hasattr(sample_reset, "used") else "unknown",
            }
            results["reset_flow"]["token_info"] = token_info

            # Try to query existing resets (if any)
            reset_count = PasswordReset.query.count()
            results["reset_flow"]["reset_count"] = reset_count
            results["tests"].append({"test": "query_table", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "query_table", "status": "error", "message": str(e)})

        # Step 3: Check if we can create and find a user
        try:
            # Try to find a test user
            test_user = User.query.filter_by(email="test@example.com").first()

            if not test_user:
                # Create a test user for diagnostics
                test_user = User(email="test@example.com")
                test_user.set_password("password123")

                # Don't actually save this test user to the database
                # db.session.add(test_user)
                # db.session.commit()

            user_info = {
                "found": test_user is not None,
                "email": test_user.email if test_user else None,
                "id": str(test_user.id) if test_user else None,
                "password_hash_length": len(test_user.password_hash)
                if test_user and hasattr(test_user, "password_hash")
                else 0,
            }

            results["reset_flow"]["user_info"] = user_info
            results["tests"].append({"test": "check_user", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_user", "status": "error", "message": str(e)})

        # Step 4: Check if we can simulate the reset flow
        try:
            # Import what we need from the reset password route
            from flask import jsonify, request

            from app.utils.email import send_reset_password_email

            # Get the create_for_user method
            create_method = getattr(PasswordReset, "create_for_user", None)
            get_by_token_method = getattr(PasswordReset, "get_by_token", None)

            method_info = {
                "create_method_exists": create_method is not None,
                "get_by_token_exists": get_by_token_method is not None,
            }

            results["reset_flow"]["method_info"] = method_info

            # Check if the email utility exists
            email_info = {
                "function_exists": callable(send_reset_password_email)
                if "send_reset_password_email" in locals()
                else False
            }

            results["reset_flow"]["email_info"] = email_info
            results["tests"].append({"test": "check_flow", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_flow", "status": "error", "message": str(e)})

        # Step 5: Check for any errors in the logs related to reset password
        try:
            # This only works if logging to the database or if we have access to the logs
            # Just a placeholder for now
            results["reset_flow"]["recent_errors"] = "Cannot access logs from this endpoint"
            results["tests"].append({"test": "check_logs", "status": "skipped"})
        except Exception as e:
            results["tests"].append({"test": "check_logs", "status": "error", "message": str(e)})

        # Return the results
        return jsonify(results)
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to debug reset password", "error": str(e)}), 500


@debug_bp.route("/debug-register")
def debug_register():
    """Debug the register endpoint flow"""
    try:
        from app.api.auth import RegisterSchema
        from app.models.user import User

        results = {"status": "success", "tests": [], "register_flow": {}}

        # Step 1: Check if User model works
        try:
            user_model_info = {
                "module": str(User.__module__),
                "class": User.__name__,
                "tablename": getattr(User, "__tablename__", "unknown"),
                "methods": [m for m in dir(User) if not m.startswith("_") and callable(getattr(User, m))],
            }
            results["register_flow"]["model_info"] = user_model_info

            # Check user table structure
            inspector = inspect(db.engine)
            columns = inspector.get_columns("users")
            col_info = [{"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]} for col in columns]
            results["register_flow"]["table_structure"] = col_info

            results["tests"].append({"test": "check_model", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_model", "status": "error", "message": str(e)})

        # Step 2: Test user creation (no commit)
        try:
            # Create a test user without saving to DB
            test_user = User(email="test_register@example.com", profile_name="Test Register")
            test_user.set_password("password123")

            # Check password hash
            password_hash_info = {
                "length": len(test_user.password_hash),
                "starts_with": test_user.password_hash[:20] + "..." if test_user.password_hash else "None",
            }
            results["register_flow"]["password_hash"] = password_hash_info

            # Check methods required for registration
            set_password_method = getattr(User, "set_password", None)
            to_dict_method = getattr(User, "to_dict", None)

            method_info = {
                "set_password_exists": set_password_method is not None,
                "to_dict_exists": to_dict_method is not None,
            }

            results["register_flow"]["method_info"] = method_info
            results["tests"].append({"test": "user_creation", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "user_creation", "status": "error", "message": str(e)})

        # Step 3: Test database insertion (no commit)
        try:
            # Try adding to session but don't commit
            temp_user = User(email="temp_test@example.com", profile_name="Temporary Test")
            temp_user.set_password("temppass123")

            # Just add to session to test if the model can be added
            db.session.add(temp_user)
            # Rollback immediately to avoid actually creating the user
            db.session.rollback()

            results["tests"].append({"test": "db_insertion", "status": "success"})
        except Exception as e:
            db.session.rollback()
            results["tests"].append({"test": "db_insertion", "status": "error", "message": str(e)})

        # Step 4: Check other dependencies
        try:
            # Check if we can import and use the RegisterSchema
            schema_info = {
                "module": str(RegisterSchema.__module__),
                "class": RegisterSchema.__name__,
                "fields": list(RegisterSchema().fields.keys()) if hasattr(RegisterSchema(), "fields") else [],
            }
            results["register_flow"]["schema_info"] = schema_info

            # Check JWT config
            try:
                from flask_jwt_extended import create_access_token

                jwt_config = {"jwt_available": True, "create_token_callable": callable(create_access_token)}
                results["register_flow"]["jwt_config"] = jwt_config
            except ImportError:
                results["register_flow"]["jwt_config"] = {"jwt_available": False}

            results["tests"].append({"test": "check_dependencies", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_dependencies", "status": "error", "message": str(e)})

        # Step 5: Check for any existing users (basic count)
        try:
            user_count = User.query.count()
            results["register_flow"]["user_count"] = user_count
            results["tests"].append({"test": "check_existing_users", "status": "success"})
        except Exception as e:
            results["tests"].append({"test": "check_existing_users", "status": "error", "message": str(e)})

        # Return the results
        return jsonify(results)
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to debug register endpoint", "error": str(e)}), 500


@debug_bp.route("/debug-gcp-logs")
def debug_gcp_logs():
    """Fetch recent logs from Google Cloud Logging"""
    try:
        import datetime

        from google.cloud import logging
        from google.cloud.logging_v2.types import ListLogEntriesRequest

        # Number of log entries to fetch (default to 50)
        limit = request.args.get("limit", 50, type=int)
        # Type of logs to fetch: "error", "all", or specific string to filter
        log_type = request.args.get("type", "error")
        # Service to fetch logs for (default to "registration" but can be any service)
        service = request.args.get("service", "registration")

        # Initialize the logging client
        logging_client = logging.Client()

        # Build the filter string
        filter_parts = []

        # Filter by project (should automatically use the current project)
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            filter_parts.append(f"resource.type=gae_app AND resource.labels.project_id={project_id}")

        # Filter by log severity if requested
        if log_type == "error":
            filter_parts.append("severity>=ERROR")
        elif log_type != "all" and log_type:
            # Allow custom text filtering - use text search instead of trying to filter on jsonPayload
            filter_parts.append(f"textPayload:*{log_type}*")

        # Filter by service name if specified
        if service:
            # Use text search instead of trying to access jsonPayload directly
            filter_parts.append(f"textPayload:*{service}*")

        # Combine all filter parts
        filter_str = " AND ".join(filter_parts) if filter_parts else ""

        # Get logs from the last 24 hours by default
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(hours=24)

        # Construct the request
        request_dict = {
            "filter_": filter_str,  # Changed from "filter" to "filter_"
            "order_by": "timestamp desc",  # Most recent first
            "page_size": limit,
        }

        # Set time range if we have project ID
        if project_id:
            request_dict["resource_names"] = [f"projects/{project_id}"]

        # Add more details in the response for debugging
        response_data = {
            "status": "success",
            "filter": filter_str,
            "request_params": request_dict,
            "count": 0,
            "logs": [],
        }

        # Execute query
        entries = logging_client.list_entries(**request_dict)

        # Format logs for API response
        logs = []
        for entry in entries:
            log_entry = {
                "timestamp": entry.timestamp.isoformat() if hasattr(entry, "timestamp") and entry.timestamp else None,
                "severity": entry.severity,
                "log_name": entry.log_name,
            }

            # Extract the payload (could be text or JSON)
            if hasattr(entry, "payload") and entry.payload:
                if isinstance(entry.payload, dict):
                    log_entry["payload"] = entry.payload
                else:
                    log_entry["payload"] = str(entry.payload)
            elif hasattr(entry, "text_payload") and entry.text_payload:
                log_entry["payload"] = entry.text_payload
            elif hasattr(entry, "json_payload") and entry.json_payload:
                log_entry["payload"] = dict(entry.json_payload)
            else:
                log_entry["payload"] = "No payload"

            # Add trace info if available
            if hasattr(entry, "trace") and entry.trace:
                log_entry["trace"] = entry.trace

            # Add resource info if available
            if hasattr(entry, "resource") and entry.resource:
                log_entry["resource"] = {
                    "type": entry.resource.type,
                    "labels": dict(entry.resource.labels) if hasattr(entry.resource, "labels") else {},
                }

            logs.append(log_entry)

        response_data["count"] = len(logs)
        response_data["logs"] = logs

        # Return formatted response
        return jsonify(response_data)

    except ImportError as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to import Google Cloud Logging library",
                    "error": str(e),
                    "resolution": "Install google-cloud-logging package",
                }
            ),
            500,
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Failed to fetch GCP logs",
                    "error": str(e),
                    "filter_string": filter_str if "filter_str" in locals() else "Not created yet",
                }
            ),
            500,
        )


@debug_bp.route("/dashboard")
def debug_dashboard():
    """Render a dashboard with tabs for all debug endpoints."""
    base_url = request.url_root.rstrip("/") + "/debug"

    # Define the tabs and groups of endpoints
    endpoint_groups = [
        {
            "id": "general",
            "name": "General",
            "description": "General health and diagnostics",
            "endpoints": [
                {
                    "path": "/health",
                    "name": "Health Check",
                    "description": "Comprehensive health check of the application, database and system resources.",
                },
                {
                    "path": "/db-check",
                    "name": "Database Check",
                    "description": "Check database connectivity and configuration.",
                },
                {
                    "path": "/check-tables",
                    "name": "Check Tables",
                    "description": "Check if specific database tables exist.",
                },
                {
                    "path": "/fix-production-tables",
                    "name": "Fix Production Tables",
                    "description": "Fix production database tables by creating them in the correct order.",
                },
                {
                    "path": "/check-database",
                    "name": "Check Database",
                    "description": "Comprehensive check of database status.",
                },
            ],
        },
        {
            "id": "metrics",
            "name": "Metrics & Monitoring",
            "description": "Performance metrics and system monitoring",
            "endpoints": [
                {
                    "path": "/performance",
                    "name": "API Performance",
                    "description": "Monitor API performance metrics, response times, and error rates.",
                },
                {
                    "path": "/requests",
                    "name": "Request Inspector",
                    "description": "View recent API requests, their headers, parameters, and responses.",
                },
                {
                    "path": "/system-resources",
                    "name": "System Resources",
                    "description": "Monitor system resources like CPU, memory, and disk usage.",
                },
            ],
        },
        {
            "id": "logs",
            "name": "Logs & Errors",
            "description": "Application logs and error tracking",
            "endpoints": [
                {
                    "path": "/debug-gcp-logs",
                    "name": "GCP Logs",
                    "description": "Fetch and view logs from Google Cloud Logging.",
                },
                {
                    "path": "/error-tracker",
                    "name": "Error Tracker",
                    "description": "Track and view recent application errors.",
                },
            ],
        },
        {
            "id": "auth",
            "name": "Authentication",
            "description": "Authentication and authorization debugging",
            "endpoints": [
                {
                    "path": "/auth-debug",
                    "name": "Auth Debugger",
                    "description": "Debug JWT tokens and authentication configuration.",
                },
                {
                    "path": "/debug-register",
                    "name": "Register Debug",
                    "description": "Debug the registration flow and user creation.",
                },
                {
                    "path": "/debug-reset-password",
                    "name": "Reset Password Debug",
                    "description": "Debug the password reset flow.",
                },
            ],
        },
        {
            "id": "environment",
            "name": "Environment",
            "description": "Environment variables and system configuration",
            "endpoints": [
                {
                    "path": "/environment",
                    "name": "Environment Variables",
                    "description": "View environment variables and configuration settings.",
                }
            ],
        },
        {
            "id": "database",
            "name": "Database",
            "description": "Database profiling and debugging",
            "endpoints": [
                {
                    "path": "/db-profiler",
                    "name": "Database Profiler",
                    "description": "Profile database performance and slow queries.",
                },
                {
                    "path": "/apply-migrations",
                    "name": "Apply Migrations",
                    "description": "Apply missing database migrations.",
                },
                {
                    "path": "/sql-fix",
                    "name": "SQL Fix",
                    "description": "Apply direct SQL fixes to fix critical database issues.",
                },
            ],
        },
    ]

    # All endpoints for the search function
    all_endpoints = []
    for group in endpoint_groups:
        for endpoint in group["endpoints"]:
            all_endpoints.append(endpoint)

    # Generate HTML page
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Dashboard - Find a Meeting Spot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            header {
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
            }
            h1 {
                margin: 0;
                font-size: 24px;
            }
            h2 {
                color: #3498db;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
                margin-top: 30px;
            }
            h3 {
                color: #2c3e50;
                margin-top: 20px;
            }
            .tabs {
                display: flex;
                overflow-x: auto;
                margin-top: 20px;
                border-bottom: 1px solid #ddd;
                background-color: #f8f9fa;
            }
            .tab {
                padding: 12px 24px;
                cursor: pointer;
                transition: background-color 0.3s;
                font-weight: 500;
                white-space: nowrap;
                border-bottom: 3px solid transparent;
            }
            .tab:hover {
                background-color: #eaeaea;
            }
            .tab.active {
                background-color: white;
                border-bottom: 3px solid #3498db;
                color: #3498db;
            }
            .tab-content {
                display: none;
                padding: 20px;
                background-color: white;
                border-radius: 0 0 4px 4px;
            }
            .tab-content.active {
                display: block;
            }
            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .endpoint-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                transition: transform 0.2s, box-shadow 0.2s;
                background-color: #f8f9fa;
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            .endpoint-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .endpoint-title {
                font-weight: bold;
                color: #2980b9;
                margin-bottom: 5px;
            }
            .endpoint-path {
                color: #16a085;
                font-family: monospace;
                padding: 3px 6px;
                background-color: #e8f4f8;
                border-radius: 4px;
                display: inline-block;
                margin-bottom: 8px;
            }
            .endpoint-description {
                color: #555;
                font-size: 0.9em;
                flex-grow: 1;
            }
            .action-buttons {
                margin-top: 10px;
                display: flex;
                gap: 10px;
            }
            .btn {
                display: inline-block;
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 0.9em;
                transition: background-color 0.2s;
                border: none;
                cursor: pointer;
            }
            .btn:hover {
                background-color: #2980b9;
            }
            .copy-btn {
                background-color: #7f8c8d;
            }
            .copy-btn:hover {
                background-color: #5f6c6d;
            }
            .note {
                background-color: #f8f4e5;
                border-left: 4px solid #f1c40f;
                padding: 10px 15px;
                margin: 20px 0;
                border-radius: 0 4px 4px 0;
            }
            .search-container {
                display: flex;
                margin: 20px 0;
                max-width: 600px;
            }
            .search-input {
                flex-grow: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px 0 0 4px;
                font-size: 16px;
            }
            .search-btn {
                border-radius: 0 4px 4px 0;
                border: 1px solid #2980b9;
                background-color: #3498db;
                color: white;
                padding: 0 15px;
                cursor: pointer;
            }
            .search-results {
                display: none;
                margin-top: 20px;
            }
            .footer {
                margin-top: 30px;
                text-align: center;
                color: #7f8c8d;
                font-size: 0.8em;
                padding: 10px;
                background-color: #f8f9fa;
                border-top: 1px solid #eee;
            }
            .tab-description {
                color: #666;
                margin-bottom: 20px;
            }
            .iframe-view {
                width: 100%;
                height: 600px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 20px;
                display: none;
            }
            @media (max-width: 768px) {
                .endpoints {
                    grid-template-columns: 1fr;
                }
                .tabs {
                    flex-wrap: wrap;
                }
                .tab {
                    width: 50%;
                    text-align: center;
                    box-sizing: border-box;
                }
            }
        </style>
    </head>
    <body>
        <header>
            <h1>Find a Meeting Spot - Debug Dashboard</h1>
        </header>

        <div class="container">
            <div class="note">
                <strong>Note:</strong> These endpoints are for debugging purposes only and should not be exposed in production.
                You can use this dashboard to diagnose issues with the application.
            </div>

            <div class="search-container">
                <input type="text" id="search-input" class="search-input" placeholder="Search endpoints...">
                <button id="search-btn" class="search-btn">Search</button>
            </div>
"""

    return html


def init_app(app):
    """Initialize API and register blueprints with the Flask application.

    Args:
        app: Flask application instance
    """
    # Register API v1 blueprint
    app.register_blueprint(api_v1_bp)

    # Register API v2 blueprint
    app.register_blueprint(api_v2_bp)

    # Register debug blueprint
    app.register_blueprint(debug_bp)

    # Initialize limiter with app if it exists
    if limiter:
        limiter.init_app(app)

    return app


@debug_bp.route("/debug-contacts")
def debug_contacts():
    """Debug endpoint for contacts API issues."""
    log_entry = {}

    try:
        # Import the Contact model
        from app.models import Contact

        log_entry["import_contact_model"] = "success"

        # Check if Contact model is properly defined
        log_entry["contact_model_attributes"] = {
            "has_id": hasattr(Contact, "id"),
            "has_user_id": hasattr(Contact, "user_id"),
            "has_name": hasattr(Contact, "name"),
            "has_tablename": hasattr(Contact, "__tablename__"),
            "tablename": getattr(Contact, "__tablename__", None),
        }

        # Check if table exists
        from sqlalchemy import inspect

        from app import db

        inspector = inspect(db.engine)
        log_entry["contact_table_exists"] = "contacts" in inspector.get_table_names()

        if log_entry["contact_table_exists"]:
            log_entry["contact_table_columns"] = [col["name"] for col in inspector.get_columns("contacts")]

        # Check relationships
        log_entry["relationship_check"] = {
            "has_user_relationship": hasattr(Contact, "user"),
            "has_meeting_requests_relationship": hasattr(Contact, "meeting_requests"),
        }

        # Check auth functionality
        from flask import request

        auth_header = request.headers.get("Authorization")
        log_entry["auth_header_exists"] = auth_header is not None

        if auth_header:
            from app.decorators import decode_token

            try:
                token = auth_header.split(" ")[1]
                decoded = decode_token(token)
                log_entry["token_decode"] = "success"
                log_entry["token_payload"] = {
                    "sub": decoded.get("sub"),
                    "exp": decoded.get("exp"),
                    "iat": decoded.get("iat"),
                }
            except Exception as e:
                log_entry["token_decode"] = "failed"
                log_entry["token_error"] = str(e)

        # Check for existing contacts
        from app.models import User

        contact_counts = db.session.query(db.func.count(Contact.id)).scalar()
        user_counts = db.session.query(db.func.count(User.id)).scalar()
        log_entry["db_counts"] = {
            "contacts": contact_counts,
            "users": user_counts,
        }

        return jsonify({"status": "success", "debug_info": log_entry})

    except Exception as e:
        import traceback

        log_entry["error"] = str(e)
        log_entry["traceback"] = traceback.format_exc()

        return jsonify({"status": "error", "debug_info": log_entry}), 500


@debug_bp.route("/fix-contacts-table")
def fix_contacts_table():
    """Create the contacts table if it doesn't exist."""
    log_entry = {}

    try:
        # Check if contacts table exists
        from sqlalchemy import inspect, text
        from sqlalchemy.dialects import postgresql

        from app import db

        inspector = inspect(db.engine)
        exists = "contacts" in inspector.get_table_names()
        log_entry["contacts_table_exists"] = exists

        # If it already exists, we're done
        if exists:
            return jsonify(
                {"status": "no_action_needed", "message": "Contacts table already exists", "details": log_entry}
            )

        # Create the contacts table directly using SQL
        with db.engine.begin() as conn:
            # Create contacts table
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS contacts (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    company VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
            """
                )
            )

            # Create indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contacts_user_id ON contacts(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_contacts_email ON contacts(email)"))

            # Check if meeting_contacts table should also be created
            if "meeting_contacts" not in inspector.get_table_names():
                conn.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS meeting_contacts (
                        meeting_request_id UUID NOT NULL REFERENCES meeting_requests(request_id) ON DELETE CASCADE,
                        contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (meeting_request_id, contact_id)
                    )
                """
                    )
                )

                conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_meeting_contacts_contact_id ON meeting_contacts(contact_id)")
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_meeting_contacts_meeting_request_id ON meeting_contacts(meeting_request_id)"
                    )
                )

                log_entry["meeting_contacts_table_created"] = True

            # Update alembic_version to reflect our changes if it exists
            if "alembic_version" in inspector.get_table_names():
                # Set to latest migration version (our new contacts table migration)
                conn.execute(text("UPDATE alembic_version SET version_num = 'a4b2c3d5e6f7'"))
                log_entry["alembic_version_updated"] = True

        # Verify tables were created
        inspector = inspect(db.engine)
        contacts_exists = "contacts" in inspector.get_table_names()
        meeting_contacts_exists = "meeting_contacts" in inspector.get_table_names()

        log_entry["contacts_table_created"] = contacts_exists
        log_entry["meeting_contacts_table_exists"] = meeting_contacts_exists

        if contacts_exists:
            log_entry["contacts_columns"] = [col["name"] for col in inspector.get_columns("contacts")]

        return jsonify({"status": "success", "message": "Successfully created missing tables", "details": log_entry})

    except Exception as e:
        import traceback

        log_entry["error"] = str(e)
        log_entry["traceback"] = traceback.format_exc()

        return jsonify({"status": "error", "message": "Error creating tables: " + str(e), "details": log_entry}), 500


@debug_bp.route("/basic-register", methods=["OPTIONS"])
def basic_register_options():
    """Handle OPTIONS requests for the basic-register endpoint."""
    response = current_app.make_default_options_response()
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


@debug_bp.route("/basic-register", methods=["POST"])
def basic_register():
    """Simplified registration endpoint with detailed logging and error handling."""
    try:
        from app.models.user import User

        data = request.get_json()
        current_app.logger.info(
            f"Basic register attempt with data: {json.dumps({k: '***' if k == 'password' else v for k, v in data.items()})}"
        )

        # Validate required fields
        if not data.get("email") or not data.get("password"):
            current_app.logger.error("Missing required fields in basic register")
            return jsonify({"status": "error", "message": "Email and password are required"}), 400

        # Check if user already exists
        existing_user = User.query.filter_by(email=data["email"]).first()
        if existing_user:
            current_app.logger.info(f"User already exists: {data['email']}")
            return jsonify({"status": "error", "message": "User already exists"}), 409

        try:
            # Create new user with detailed logging
            current_app.logger.info(f"Creating new user for email: {data['email']}")

            user = User(email=data["email"])
            user.set_password(data["password"])
            current_app.logger.info(f"User object created with ID: {user.id}")

            # Add to database
            db.session.add(user)
            current_app.logger.info("User added to session, about to commit")
            db.session.commit()
            current_app.logger.info(f"User committed to database successfully with ID: {user.id}")

            # Generate access token
            from flask_jwt_extended import create_access_token

            access_token = create_access_token(identity=str(user.id))
            current_app.logger.info(f"Access token generated for user {user.id}")

            # Return success response
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "User registered successfully",
                        "access_token": access_token,
                        "user": user.to_dict(),
                    }
                ),
                201,
            )

        except Exception as e:
            db.session.rollback()
            tb = traceback.format_exc()
            current_app.logger.error(f"Error in basic registration: {str(e)}")
            current_app.logger.error(f"Traceback: {tb}")
            return jsonify({"status": "error", "message": "Error registering user", "error": str(e)}), 500

    except Exception as e:
        tb = traceback.format_exc()
        current_app.logger.error(f"Critical error in basic registration endpoint: {str(e)}")
        current_app.logger.error(f"Traceback: {tb}")
        return jsonify({"status": "error", "message": "Server error", "error": str(e)}), 500


@debug_bp.route("/google-auth-debug", methods=["GET", "OPTIONS"])
def google_auth_debug():
    """Debug endpoint for checking Google OAuth configuration"""
    if request.method == "OPTIONS":
        response = current_app.make_default_options_response()
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    try:
        # Check Google OAuth configuration
        google_client_id = current_app.config.get("GOOGLE_CLIENT_ID")
        google_client_id_mask = "Not set"

        if google_client_id:
            if len(google_client_id) > 20:
                google_client_id_mask = f"{google_client_id[:10]}...{google_client_id[-5:]}"
            else:
                google_client_id_mask = google_client_id

        result = {
            "status": "success",
            "message": "Google OAuth debug information",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "google_auth": {
                "client_id_configured": bool(google_client_id),
                "client_id_mask": google_client_id_mask,
                "google_auth_module_available": "google.oauth2" in sys.modules,
                "id_token_module_available": hasattr(sys.modules.get("google.oauth2", {}), "id_token"),
            },
            "environment": current_app.config.get("ENV", "unknown"),
            "debug_mode": current_app.config.get("DEBUG", False),
        }

        # Get the Google-related environment variables for debugging
        env_vars = {}
        for key in os.environ:
            if key.startswith("GOOGLE_") and "SECRET" not in key.upper():
                env_vars[key] = os.environ[key]

        result["environment_variables"] = env_vars

        return jsonify(result)
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Error checking Google OAuth configuration: {str(e)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            500,
        )
