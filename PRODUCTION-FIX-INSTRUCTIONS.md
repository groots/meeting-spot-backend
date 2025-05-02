# Production Fix Instructions

These instructions will guide you through fixing the two critical issues in the application:

1. Profile Picture Upload (405/500 Error)
2. Meeting Requests (500 Error - Missing Phone Column)

## Prerequisites

Ensure you have SSH access to your production server or access to your deployment environment.

## Step 1: Clone or Update the Repository

If you haven't already cloned the repository on your production server:

```bash
git clone https://github.com/groots/meeting-spot-backend.git
cd meeting-spot-backend
```

If you already have the repository:

```bash
cd meeting-spot-backend
git pull origin main
```

## Step 2: Apply the Database Fixes

The missing phone column is causing the meeting requests to fail. Run the hotfix script to add it:

```bash
cd backend
chmod +x apply_phone_column_hotfix.sh
./apply_phone_column_hotfix.sh
```

This script will:
- Attempt to find your database (local or via DATABASE_URL)
- Back up your database if possible
- Add the missing phone column using Python and SQLAlchemy
- Fall back to direct SQL if needed
- Verify the fix was applied correctly

## Step 3: Create Profile Pictures Directory

The profile picture uploads fail because the storage directory doesn't exist:

```bash
mkdir -p instance/profile_pictures
chmod 755 instance/profile_pictures
```

## Step 4: Verify Middleware Registration

The middleware ensures the encryption key is properly set:

```bash
grep -q "register_middleware(app)" app/__init__.py
```

If the above command doesn't return anything, you need to add the middleware registration:

```bash
# Open the file for editing
nano app/__init__.py

# Add this import near the top:
from .middleware import register_middleware

# Find where setup_cors(app) is called and add after it:
register_middleware(app)
```

## Step 5: Restart the Application

Restart your application to apply the changes:

```bash
# If using systemd
sudo systemctl restart findameetingspot.service

# If using Docker
docker restart <container-id>

# If using Supervisor
supervisorctl restart findameetingspot

# If using Cloud Run or similar, redeploy the application
```

## Step 6: Verify the Fixes

1. Try uploading a profile picture
2. Create a meeting request

Both operations should now work without errors.

## Troubleshooting

If the fixes don't work as expected:

1. Check the application logs:
   ```bash
   # If using systemd
   journalctl -u findameetingspot.service -n 100

   # If using Docker
   docker logs <container-id>
   ```

2. Use the direct fix script if the hotfix didn't work:
   ```bash
   python fix_db_now.py
   ```

3. Manually examine the database:
   ```bash
   # For SQLite
   sqlite3 app/dev.db "PRAGMA table_info(users);"

   # For PostgreSQL
   psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"
   ```

4. Check middleware registration with:
   ```bash
   cat app/__init__.py | grep -n register_middleware
   ```

## Support

If you continue to experience issues, contact the development team for further assistance.
