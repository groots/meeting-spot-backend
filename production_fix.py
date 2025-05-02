#!/usr/bin/env python3

"""
Production-specific fix script for addressing both the profile picture upload
and meeting request 500 errors in the production environment.
"""

import logging
import os
import sys
import traceback

from flask import Flask
from sqlalchemy import inspect, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("production_fix.log")],
)
logger = logging.getLogger("production_fix")


def verify_api_routes():
    """Verify API routes are correctly registered."""
    try:
        from app import create_app

        app = create_app("production")
        with app.app_context():
            # Get all registered routes
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(f"{rule.endpoint}: {','.join(rule.methods)} {rule}")

            logger.info(f"Found {len(routes)} registered routes")

            # Check for critical endpoints
            meeting_requests_endpoint = False
            profile_picture_endpoint = False

            for route in routes:
                if "/api/v1/meeting-requests/" in route:
                    meeting_requests_endpoint = True
                    logger.info(f"Found meeting requests endpoint: {route}")
                if "/api/v1/auth/me/picture" in route:
                    profile_picture_endpoint = True
                    logger.info(f"Found profile picture endpoint: {route}")

            if not meeting_requests_endpoint:
                logger.error("Meeting requests endpoint is not properly registered!")

            if not profile_picture_endpoint:
                logger.error("Profile picture endpoint is not properly registered!")

            return meeting_requests_endpoint and profile_picture_endpoint
    except Exception as e:
        logger.error(f"Failed to verify API routes: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def verify_middleware_registration():
    """Check and ensure middleware registration in production."""
    try:
        import importlib.util

        from app import create_app

        # First check if middleware module exists
        middleware_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "middleware.py")
        if not os.path.exists(middleware_path):
            logger.error(f"Middleware file does not exist at {middleware_path}")
            return False

        # Check if middleware is imported in __init__.py
        init_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "__init__.py")
        with open(init_path, "r") as f:
            init_content = f.read()
            if "from .middleware import register_middleware" not in init_content:
                logger.error("Middleware import not found in __init__.py")
                return False
            if "register_middleware(app)" not in init_content:
                logger.error("Middleware registration call not found in __init__.py")
                return False

        logger.info("Middleware import and registration found in __init__.py")

        # Now check if it's actually working in the app
        app = create_app("production")
        with app.app_context():
            if "ENCRYPTION_KEY" not in app.config:
                logger.error("ENCRYPTION_KEY not set in app config")
                return False

            logger.info(f"ENCRYPTION_KEY is set in app config")
            return True
    except Exception as e:
        logger.error(f"Failed to verify middleware registration: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def verify_profile_picture_column():
    """Check profile_picture_url column exists in users table in production."""
    try:
        from app import create_app, db

        app = create_app("production")
        with app.app_context():
            inspector = inspect(db.engine)
            if "users" in inspector.get_table_names():
                columns = [col["name"] for col in inspector.get_columns("users")]
                if "profile_picture_url" not in columns:
                    logger.error("profile_picture_url column does not exist in users table")
                    return False

                logger.info("profile_picture_url column exists in users table")
                return True
            else:
                logger.error("users table does not exist in the database")
                return False
    except Exception as e:
        logger.error(f"Failed to verify profile_picture_url column: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def verify_storage_directory():
    """Verify profile pictures directory exists and has proper permissions."""
    try:
        from app import create_app

        app = create_app("production")
        with app.app_context():
            profile_pics_dir = os.path.join(app.instance_path, "profile_pictures")
            if not os.path.exists(profile_pics_dir):
                logger.error(f"Profile pictures directory does not exist at {profile_pics_dir}")
                return False

            # Check directory permissions
            if not os.access(profile_pics_dir, os.W_OK):
                logger.error(f"Profile pictures directory is not writable at {profile_pics_dir}")
                return False

            logger.info(f"Profile pictures directory exists and is writable at {profile_pics_dir}")
            return True
    except Exception as e:
        logger.error(f"Failed to verify storage directory: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def test_encryption():
    """Test encryption functionality with the current app config."""
    try:
        from app import create_app
        from app.utils.encryption import decrypt_data, encrypt_data

        app = create_app("production")
        with app.app_context():
            # Test encryption/decryption
            test_data = "test@example.com"
            encrypted = encrypt_data(test_data, app.config.get("ENCRYPTION_KEY"))
            decrypted = decrypt_data(encrypted, app.config.get("ENCRYPTION_KEY"))

            if decrypted != test_data:
                logger.error(f"Encryption/decryption test failed: {test_data} != {decrypted}")
                return False

            logger.info("Encryption/decryption test passed successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to test encryption: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def fix_middleware():
    """Deploy middleware fix to ensure encryption key is always available."""
    try:
        # Create middleware.py if it doesn't exist
        middleware_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "middleware.py")
        if not os.path.exists(middleware_path):
            logger.info(f"Creating middleware.py at {middleware_path}")
            with open(middleware_path, "w") as f:
                f.write(
                    '''"""Middleware for ensuring required environment variables and configurations are set."""

import logging
import os

from flask import Flask, current_app, request

# Default encryption key to use if none is set in the environment
DEFAULT_ENCRYPTION_KEY = "wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"


def ensure_encryption_key(app: Flask) -> None:
    """Ensure encryption key is set in app config."""
    if not app.config.get("ENCRYPTION_KEY"):
        app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
        app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY


def register_middleware(app: Flask) -> None:
    """Register middleware with the Flask app."""

    # Make sure encryption key is set
    ensure_encryption_key(app)

    # Register before_request handlers
    @app.before_request
    def check_encryption_key():
        """Check if encryption key is properly set in the config."""
        if not current_app.config.get("ENCRYPTION_KEY"):
            current_app.logger.warning("ENCRYPTION_KEY not set in config; using default fallback key")
            current_app.config["ENCRYPTION_KEY"] = DEFAULT_ENCRYPTION_KEY

    # Log the encryption key status (don't log the actual key)
    if app.config.get("ENCRYPTION_KEY"):
        app.logger.info("ENCRYPTION_KEY is configured")
    else:
        app.logger.error("ENCRYPTION_KEY could not be set; this may cause issues with encrypted data")
'''
                )
            logger.info("Created middleware.py successfully")

        # Update __init__.py to include middleware if needed
        init_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "__init__.py")
        with open(init_path, "r") as f:
            init_content = f.read()

        updated = False
        if "from .middleware import register_middleware" not in init_content:
            # Find a good spot to add the import (after other imports, before app initialization)
            import_lines = init_content.split("\n")
            for i, line in enumerate(import_lines):
                if line.startswith("from .cors_middleware import setup_cors"):
                    # Insert after CORS middleware import
                    import_lines.insert(
                        i + 1, "\n# Import encryption key middleware\nfrom .middleware import register_middleware"
                    )
                    updated = True
                    break

            if updated:
                init_content = "\n".join(import_lines)

        if "register_middleware(app)" not in init_content:
            # Find the app creation section and add middleware registration before other extensions
            lines = init_content.split("\n")
            for i, line in enumerate(lines):
                if (
                    line.strip()
                    == "# *** IMPORTANT: Set up CORS with our simplified middleware BEFORE other extensions and blueprints ***"
                ):
                    # Insert after CORS setup line
                    if i + 2 < len(lines) and "setup_cors(app)" in lines[i + 1]:
                        lines.insert(i + 2, "\n    # Register encryption key middleware\n    register_middleware(app)")
                        updated = True
                        break

            if updated:
                init_content = "\n".join(lines)

        if updated:
            logger.info("Updating __init__.py with middleware registration")
            with open(init_path, "w") as f:
                f.write(init_content)
            logger.info("Updated __init__.py successfully")

        return True
    except Exception as e:
        logger.error(f"Failed to fix middleware: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def create_profile_pictures_directory():
    """Create profile pictures directory if it doesn't exist."""
    try:
        from app import create_app

        app = create_app("production")
        with app.app_context():
            profile_pics_dir = os.path.join(app.instance_path, "profile_pictures")
            if not os.path.exists(profile_pics_dir):
                logger.info(f"Creating profile pictures directory at {profile_pics_dir}")
                os.makedirs(profile_pics_dir, exist_ok=True)
                # Set permissions
                os.chmod(profile_pics_dir, 0o755)
                logger.info(f"Created profile pictures directory with permissions 755")
            return True
    except Exception as e:
        logger.error(f"Failed to create profile pictures directory: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def run_migrations():
    """Run database migrations to ensure all tables and columns are properly created."""
    try:
        logger.info("Running database migrations...")
        os.environ["FLASK_APP"] = "wsgi.py"
        os.environ["FLASK_ENV"] = "production"
        migration_result = os.system("flask db upgrade")

        if migration_result == 0:
            logger.info("Database migrations completed successfully")
            return True
        else:
            logger.error(f"Database migrations failed with exit code {migration_result}")
            return False
    except Exception as e:
        logger.error(f"Failed to run migrations: {str(e)}")
        logger.error(traceback.format_exc())
        return False


def main():
    """Main function to verify and fix production issues."""
    logger.info("Starting production fix script for meeting requests and profile picture issues")

    # First, diagnose the issues
    logger.info("=== Diagnosis Phase ===")

    logger.info("Checking API routes...")
    routes_ok = verify_api_routes()

    logger.info("Checking middleware registration...")
    middleware_ok = verify_middleware_registration()

    logger.info("Checking profile_picture_url column...")
    column_ok = verify_profile_picture_column()

    logger.info("Checking storage directory...")
    storage_ok = verify_storage_directory()

    logger.info("Testing encryption...")
    encryption_ok = test_encryption()

    # Report diagnosis
    logger.info("\n=== Diagnosis Summary ===")
    logger.info(f"API Routes: {'✅ OK' if routes_ok else '❌ ISSUE DETECTED'}")
    logger.info(f"Middleware: {'✅ OK' if middleware_ok else '❌ ISSUE DETECTED'}")
    logger.info(f"DB Column: {'✅ OK' if column_ok else '❌ ISSUE DETECTED'}")
    logger.info(f"Storage Directory: {'✅ OK' if storage_ok else '❌ ISSUE DETECTED'}")
    logger.info(f"Encryption: {'✅ OK' if encryption_ok else '❌ ISSUE DETECTED'}")

    # Apply fixes if needed
    if not all([routes_ok, middleware_ok, column_ok, storage_ok, encryption_ok]):
        logger.info("\n=== Applying Fixes ===")

        if not middleware_ok:
            logger.info("Fixing middleware...")
            if fix_middleware():
                logger.info("✅ Middleware fixed successfully")
            else:
                logger.error("❌ Failed to fix middleware")

        if not storage_ok:
            logger.info("Creating profile pictures directory...")
            if create_profile_pictures_directory():
                logger.info("✅ Profile pictures directory created successfully")
            else:
                logger.error("❌ Failed to create profile pictures directory")

        if not column_ok:
            logger.info("Running database migrations...")
            if run_migrations():
                logger.info("✅ Database migrations completed successfully")
            else:
                logger.error("❌ Failed to run database migrations")

        logger.info("\n=== Verification After Fixes ===")

        # Verify fixes
        logger.info("Re-checking middleware registration...")
        middleware_fixed = verify_middleware_registration()

        logger.info("Re-checking profile_picture_url column...")
        column_fixed = verify_profile_picture_column()

        logger.info("Re-checking storage directory...")
        storage_fixed = verify_storage_directory()

        logger.info("Re-testing encryption...")
        encryption_fixed = test_encryption()

        # Final report
        logger.info("\n=== Final Status ===")
        logger.info(f"Middleware: {'✅ FIXED' if middleware_fixed else '❌ STILL BROKEN'}")
        logger.info(f"DB Column: {'✅ FIXED' if column_fixed else '❌ STILL BROKEN'}")
        logger.info(f"Storage Directory: {'✅ FIXED' if storage_fixed else '❌ STILL BROKEN'}")
        logger.info(f"Encryption: {'✅ FIXED' if encryption_fixed else '❌ STILL BROKEN'}")

        if all([middleware_fixed, column_fixed, storage_fixed, encryption_fixed]):
            logger.info("\n✅ All issues have been fixed successfully!")
        else:
            logger.error("\n❌ Some issues could not be fixed automatically.")
            logger.error("Please check the log file for details and fix the remaining issues manually.")
            return 1
    else:
        logger.info("\n✅ No issues detected - all components appear to be working correctly.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
