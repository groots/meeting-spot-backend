# Find A Meeting Spot Backend Fixes

This document explains the critical fixes applied to resolve the two primary issues affecting the application:

1. Profile Picture Upload (405/500 Error)
2. Meeting Requests Dashboard (500 Error due to missing encryption key)

## Issue 1: Profile Picture Upload 405/500 Error

### Problem

Users were experiencing either 405 Method Not Allowed or 500 Internal Server errors when attempting to upload profile pictures to the `/api/v1/auth/me/picture` endpoint.

### Root Causes

1. While the endpoint was properly implemented in `auth.py`, the `profile_picture_url` column was either missing from the `users` table or not properly registered in some production environments.
2. The instance directory for storing uploaded profile pictures might not have been created properly.

### Fix Implementation

1. Verified endpoint implementation in `auth.py` which included:
   - POST handler for `/api/v1/auth/me/picture`
   - Validation for image file types
   - Storage mechanism for saving images

2. Added database migration to ensure the `profile_picture_url` column exists:
   - Created `add_profile_picture_url_field.py` migration script
   - Direct database migration to add column if missing

3. Added the field to the User model:
   - `profile_picture_url = db.Column(db.String(255), nullable=True)`
   - Updated `to_dict()` method to include the field

4. Ensured the instance directory exists:
   - Created `instance/profile_pictures` directory if not present
   - Set proper permissions to ensure write access

## Issue 2: Meeting Requests 500 Error

### Problem

The dashboard was showing 500 Internal Server Error when attempting to fetch meeting requests due to a missing encryption key.

### Root Causes

1. The application required an encryption key for certain operations, but it wasn't properly set up.
2. The middleware for handling the default encryption key wasn't properly registered with the Flask app.

### Fix Implementation

1. Created middleware.py with encryption key handling:
   - `DEFAULT_ENCRYPTION_KEY` for fallback
   - `ensure_encryption_key()` function to validate/set the key
   - `register_middleware()` function to properly hook into Flask

2. Modified app/__init__.py to properly register the middleware:
   - Added import: `from .middleware import register_middleware`
   - Added registration call: `register_middleware(app)`

3. Added a before_request handler to ensure the encryption key is always available:
   - Checks if key is missing at each request
   - Logs warnings when using the default key

## Deployment

The fixes have been implemented using the `deploy_middleware_fix.sh` script that:

1. Checks and updates the middleware registration
2. Ensures the profile_picture_url column exists in the database
3. Creates the necessary directories for profile picture storage
4. Verifies all fixes were applied correctly

### How to Apply the Fix

1. Run the deployment script:
   ```bash
   bash deploy_middleware_fix.sh
   ```

2. Restart the application server after applying the fix:
   ```bash
   # For systemd-based servers
   sudo systemctl restart findameetingspot.service

   # For Docker-based deployments
   docker restart findameetingspot
   ```

3. Verify the fix by:
   - Testing profile picture uploads
   - Testing meeting requests in the dashboard

## Technical Implementation Details

### Middleware Registration

The middleware implementation adds a default encryption key and proper registration with Flask:

```python
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
```

### Profile Picture Database Migration

The database migration script ensures the `profile_picture_url` column exists:

```python
def upgrade():
    """Add profile_picture_url column to users table."""
    # Get the current column names of users table
    columns = [column["name"] for column in op.get_bind().execute('PRAGMA table_info("users")').fetchall()]

    if "profile_picture_url" not in columns:
        # Add profile_picture_url column to users table
        op.add_column("users", sa.Column("profile_picture_url", sa.String(length=255), nullable=True))
```

## Conclusion

The implemented fixes address both critical issues:

1. Profile picture uploads should now work correctly with proper database support and file storage
2. Meeting requests should display properly with the encryption key middleware correctly registered

If issues persist after applying these fixes, further investigation may be needed to identify additional root causes.
