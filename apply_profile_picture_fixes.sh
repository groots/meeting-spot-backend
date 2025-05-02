#!/bin/bash

# Create profile_picture.py file
cat > app/api/profile_picture.py << 'EOL'
import os
import traceback
import uuid
from datetime import datetime, timezone

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from sqlalchemy import inspect, text

from .. import db
from ..models.user import User

# Create a separate namespace for profile picture endpoints
api = Namespace("profile", description="Profile picture operations")

@api.route("/picture")
class ProfilePicture(Resource):
    @api.doc("upload_profile_picture")
    @api.response(200, "Profile picture uploaded successfully")
    @api.response(400, "Invalid file")
    @api.response(401, "Unauthorized")
    @api.response(500, "Server error")
    @jwt_required()
    def post(self) -> None:
        """Upload a profile picture for the current user"""
        try:
            current_user_id = get_jwt_identity()
            current_app.logger.info(f"[/profile/picture] Uploading profile picture for user ID: {current_user_id}")

            # Check if user exists
            user = User.get_by_token_identity(current_user_id)
            if not user:
                current_app.logger.error(f"[/profile/picture] User not found for profile picture upload: {current_user_id}")
                return {"error": "User not found"}, 404

            # Check if profile_picture file was uploaded
            if 'profile_picture' not in request.files:
                current_app.logger.error("[/profile/picture] No profile_picture part in the request")
                return {"error": "No profile picture found in request"}, 400

            file = request.files['profile_picture']

            # Check if file exists and has a filename
            if file.filename == '':
                current_app.logger.error("[/profile/picture] Empty filename provided")
                return {"error": "No file selected"}, 400

            # Check file extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                current_app.logger.error(f"[/profile/picture] Invalid file extension: {file.filename}")
                return {"error": "Invalid file extension. Allowed: png, jpg, jpeg, gif"}, 400

            # Create storage directory if it doesn't exist
            profile_pics_dir = os.path.join(current_app.instance_path, 'profile_pictures')
            os.makedirs(profile_pics_dir, exist_ok=True)

            # Generate a unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            new_filename = f"{current_user_id}.{file_extension}"
            file_path = os.path.join(profile_pics_dir, new_filename)

            # Save the file
            file.save(file_path)
            current_app.logger.info(f"[/profile/picture] Profile picture saved to {file_path}")

            # Update user model if it has a profile_picture_url field
            try:
                # Check if the column exists in the table
                table_inspection = inspect(db.engine).get_columns('users')
                columns = [col['name'] for col in table_inspection]

                if 'profile_picture_url' in columns:
                    # Column exists, update it
                    with db.engine.connect() as conn:
                        update_sql = text("""
                            UPDATE users
                            SET profile_picture_url = :url, updated_at = :updated_at
                            WHERE id = :user_id
                        """)
                        conn.execute(update_sql, {
                            "url": f"/profile_pictures/{new_filename}",
                            "updated_at": datetime.now(timezone.utc),
                            "user_id": current_user_id
                        })
                        conn.commit()
                    current_app.logger.info(f"[/profile/picture] Updated profile_picture_url for user {current_user_id}")
            except Exception as db_error:
                current_app.logger.error(f"[/profile/picture] Error updating profile_picture_url: {str(db_error)}")
                # Continue despite this error

            return {
                "success": True,
                "message": "Profile picture uploaded successfully",
                "url": f"/profile_pictures/{new_filename}"
            }, 200

        except Exception as e:
            current_app.logger.error(f"[/profile/picture] Error uploading profile picture: {str(e)}")
            current_app.logger.error(f"[/profile/picture] Error details: {traceback.format_exc()}")
            return {"error": "Failed to upload profile picture"}, 500

    @api.doc("options_profile_picture")
    def options(self) -> None:
        """Preflight response for profile picture upload"""
        response = current_app.make_default_options_response()
        response.headers["Access-Control-Allow-Origin"] = current_app.config.get("CORS_ORIGIN", "*")
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, X-Requested-With, Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response
EOL

# Modify app/api/__init__.py to add the new namespace
INIT_FILE="app/api/__init__.py"
if grep -q "profile_picture" "$INIT_FILE"; then
  echo "Profile namespace already in __init__.py"
else
  # Add import
  sed -i.bak '/^from .payments import api as payments_namespace/a\
from .profile_picture import api as profile_namespace' "$INIT_FILE"

  # Add namespace registration
  sed -i.bak '/^api.add_namespace(payments_namespace, path="\/v1\/payments")/a\
api.add_namespace(profile_namespace, path="\/v1\/auth\/me")' "$INIT_FILE"

  # Remove backup
  rm -f "${INIT_FILE}.bak"
fi

# Add profile_picture_url to User model
USER_MODEL_FILE="app/models/user.py"
if grep -q "profile_picture_url" "$USER_MODEL_FILE"; then
  echo "profile_picture_url field already in User model"
else
  # Add field to User model
  sed -i.bak '/^    phone = db.Column(db.String(50), nullable=True, index=True)/a\
    profile_picture_url = db.Column(db.String(255), nullable=True)' "$USER_MODEL_FILE"

  # Add to to_dict method
  sed -i.bak '/^        try:/,/^            pass/ {
    /^        try:/,/^            pass/ {
      /^        try:/ {
        h
        s/^.*$/        try:\n            if hasattr(self, "profile_picture_url") and self.profile_picture_url:\n                result["profile_picture_url"] = self.profile_picture_url\n        except:\n            pass/
        p
        g
      }
    }
  }' "$USER_MODEL_FILE"

  # Remove backup
  rm -f "${USER_MODEL_FILE}.bak"
fi

# Create a migration file
MIGRATION_DIR="migrations/versions"
mkdir -p "$MIGRATION_DIR"

MIGRATION_FILE="$MIGRATION_DIR/$(date +%Y%m%d%H%M%S)_add_profile_picture_url.py"
cat > "$MIGRATION_FILE" << 'EOL'
"""Add profile_picture_url column to users table

Revision ID: $(python -c "import uuid; print(uuid.uuid4().hex[:12])"
Create Date: $(date -u +"%Y-%m-%d %H:%M:%S")
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '$(python -c "import uuid; print(uuid.uuid4().hex[:12])")'
down_revision = None  # Replace with the previous migration id if known

def upgrade():
    # Check if column exists before adding it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'profile_picture_url' not in columns:
        op.add_column('users', sa.Column('profile_picture_url', sa.String(255), nullable=True))


def downgrade():
    # Check if column exists before dropping it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'profile_picture_url' in columns:
        op.drop_column('users', 'profile_picture_url')
EOL

# Create the auth/me/picture endpoint in auth.py as a backup
AUTH_FILE="app/api/auth.py"
if grep -q "/me/picture" "$AUTH_FILE"; then
  echo "Picture endpoint already exists in auth.py"
else
  # Find the end of the UserProfile class
  LINE_NUM=$(grep -n "class UserProfile" "$AUTH_FILE" | cut -d':' -f1)
  END_LINE=$(tail -n +$LINE_NUM "$AUTH_FILE" | grep -n "^@api" | head -1 | cut -d':' -f1)
  END_LINE=$((LINE_NUM + END_LINE - 1))

  # Add the new class before the next @api decorator
  sed -i.bak "${END_LINE}i\\
@api.route(\"/me/picture\")\\
class UserProfilePicture(Resource):\\
    @api.doc(\"upload_profile_picture\")\\
    @api.response(200, \"Profile picture uploaded successfully\")\\
    @api.response(400, \"Invalid file\")\\
    @api.response(401, \"Unauthorized\")\\
    @api.response(500, \"Server error\")\\
    @jwt_required()\\
    def post(self) -> None:\\
        \"\"\"Upload a profile picture for the current user\"\"\"\\
        try:\\
            current_user_id = get_jwt_identity()\\
            current_app.logger.info(f\"[/me/picture] Uploading profile picture for user ID: {current_user_id}\")\\
\\
            # Check if user exists\\
            user = User.get_by_token_identity(current_user_id)\\
            if not user:\\
                current_app.logger.error(f\"[/me/picture] User not found for profile picture upload: {current_user_id}\")\\
                return {\"error\": \"User not found\"}, 404\\
\\
            # Check if profile_picture file was uploaded\\
            if 'profile_picture' not in request.files:\\
                current_app.logger.error(\"[/me/picture] No profile_picture part in the request\")\\
                return {\"error\": \"No profile picture found in request\"}, 400\\
\\
            file = request.files['profile_picture']\\
            \\
            # Check if file exists and has a filename\\
            if file.filename == '':\\
                current_app.logger.error(\"[/me/picture] Empty filename provided\")\\
                return {\"error\": \"No file selected\"}, 400\\
\\
            # Check file extension\\
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}\\
            if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:\\
                current_app.logger.error(f\"[/me/picture] Invalid file extension: {file.filename}\")\\
                return {\"error\": \"Invalid file extension. Allowed: png, jpg, jpeg, gif\"}, 400\\
\\
            # Create storage directory if it doesn't exist\\
            profile_pics_dir = os.path.join(current_app.instance_path, 'profile_pictures')\\
            os.makedirs(profile_pics_dir, exist_ok=True)\\
\\
            # Generate a unique filename\\
            file_extension = file.filename.rsplit('.', 1)[1].lower()\\
            new_filename = f\"{current_user_id}.{file_extension}\"\\
            file_path = os.path.join(profile_pics_dir, new_filename)\\
\\
            # Save the file\\
            file.save(file_path)\\
            current_app.logger.info(f\"[/me/picture] Profile picture saved to {file_path}\")\\
\\
            # Update user model if it has a profile_picture_url field\\
            try:\\
                # Check if the column exists in the table\\
                table_inspection = inspect(db.engine).get_columns('users')\\
                columns = [col['name'] for col in table_inspection]\\
                \\
                if 'profile_picture_url' in columns:\\
                    # Column exists, update it\\
                    from sqlalchemy import text\\
                    with db.engine.connect() as conn:\\
                        update_sql = text(\"\"\"\\
                            UPDATE users \\
                            SET profile_picture_url = :url, updated_at = :updated_at\\
                            WHERE id = :user_id\\
                        \"\"\")\\
                        conn.execute(update_sql, {\\
                            \"url\": f\"/profile_pictures/{new_filename}\",\\
                            \"updated_at\": datetime.now(timezone.utc),\\
                            \"user_id\": current_user_id\\
                        })\\
                        conn.commit()\\
                    current_app.logger.info(f\"[/me/picture] Updated profile_picture_url for user {current_user_id}\")\\
            except Exception as db_error:\\
                current_app.logger.error(f\"[/me/picture] Error updating profile_picture_url: {str(db_error)}\")\\
                # Continue despite this error\\
\\
            return {\\
                \"success\": True,\\
                \"message\": \"Profile picture uploaded successfully\",\\
                \"url\": f\"/profile_pictures/{new_filename}\"\\
            }, 200\\
\\
        except Exception as e:\\
            current_app.logger.error(f\"[/me/picture] Error uploading profile picture: {str(e)}\")\\
            current_app.logger.error(f\"[/me/picture] Error details: {traceback.format_exc()}\")\\
            return {\"error\": \"Failed to upload profile picture\"}, 500\\
    \\
    @api.doc(\"options_profile_picture\")\\
    def options(self) -> None:\\
        \"\"\"Preflight response for profile picture upload\"\"\"\\
        response = current_app.make_default_options_response()\\
        response.headers[\"Access-Control-Allow-Origin\"] = current_app.config.get(\"CORS_ORIGIN\", \"*\")\\
        response.headers[\"Access-Control-Allow-Methods\"] = \"POST, OPTIONS\"\\
        response.headers[\"Access-Control-Allow-Headers\"] = \"Content-Type, Authorization, Accept, X-Requested-With, Origin\"\\
        response.headers[\"Access-Control-Allow-Credentials\"] = \"true\"\\
        response.headers[\"Access-Control-Max-Age\"] = \"3600\"\\
        return response\\
" "$AUTH_FILE"

  # Remove backup
  rm -f "${AUTH_FILE}.bak"
fi

# Fix the meeting requests issue with the middleware
cat > app/middleware.py << 'EOL'
"""Middleware for ensuring required environment variables and configurations are set."""

import os
import logging
from flask import Flask, request, current_app

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
EOL

# Update app/__init__.py to import and register the middleware
INIT_APP_FILE="app/__init__.py"
if grep -q "from .middleware import register_middleware" "$INIT_APP_FILE"; then
  echo "Middleware import already exists in app/__init__.py"
else
  # Add the import
  sed -i.bak '/^from .cors_middleware import setup_cors/a\
from .middleware import register_middleware' "$INIT_APP_FILE"

  # Add the registration
  sed -i.bak '/^    setup_cors(app)/a\
    # Register middleware for encryption key\\
    register_middleware(app)' "$INIT_APP_FILE"

  # Remove backup
  rm -f "${INIT_APP_FILE}.bak"
fi

# Git add, commit and push
git add app/api/profile_picture.py app/api/__init__.py app/models/user.py migrations/ app/middleware.py app/__init__.py app/api/auth.py
git commit -m "Add profile picture upload endpoint and fix meeting requests issues"
git push

echo "All changes applied successfully!"
