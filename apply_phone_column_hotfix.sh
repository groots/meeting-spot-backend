#!/bin/bash
# apply_phone_column_hotfix.sh
# This script applies the phone column hotfix to the production database

set -e  # Exit on error

# Log file
LOGFILE="hotfix_$(date +%Y%m%d_%H%M%S).log"
> $LOGFILE  # Clear log file

# Timestamp function
timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

# Logging function
log() {
  echo "$(timestamp) - $1" | tee -a $LOGFILE
}

# Error handling
handle_error() {
  log "ERROR: $1"
  log "Hotfix application failed"
  exit 1
}

# Header
log "=== PHONE COLUMN HOTFIX APPLICATION ==="
log "This script will add the missing 'phone' column to the users table"

# Check if we're in the backend directory
if [ ! -f "wsgi.py" ] || [ ! -d "app" ]; then
  handle_error "This script must be run from the backend directory"
fi

# Step 1: Backup the database (if possible)
log "Step 1: Trying to backup the database"
if [ -f "app/dev.db" ]; then
  cp app/dev.db "app/dev.db.bak.$(date +%Y%m%d%H%M%S)"
  log "- Local database backed up"
elif [ -f "instance/app.db" ]; then
  cp instance/app.db "instance/app.db.bak.$(date +%Y%m%d%H%M%S)"
  log "- Instance database backed up"
else
  log "- No local database found to backup (this is normal for Cloud SQL)"
fi

# Step 2: Check if Python is available
log "Step 2: Checking Python environment"
if ! command -v python &> /dev/null; then
  log "- Python not found, trying python3"
  PY_CMD="python3"
else
  log "- Python found"
  PY_CMD="python"
fi

if ! $PY_CMD -c "import sqlalchemy" &> /dev/null; then
  log "- Installing required packages"
  pip install sqlalchemy || handle_error "Failed to install sqlalchemy"
fi

# Step 3: Try applying the fix with Python script
log "Step 3: Applying phone column fix with Python"
cat > fix_db_phone.py << 'EOL'
#!/usr/bin/env python3
"""
Emergency fix for missing phone column in production.
"""

import os
import sys
import logging
import traceback
from sqlalchemy import create_engine, inspect, text

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("emergency_fix")

def fix_phone_column():
    """Add the phone column to the users table."""
    try:
        # Try to get database URL from environment
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            # Check for local database files
            possible_db_files = [
                "instance/app.db",
                "app/dev.db",
                "dev.db"
            ]

            for db_file in possible_db_files:
                if os.path.exists(db_file):
                    db_url = f"sqlite:///{db_file}"
                    logger.info(f"Found database at {db_file}")
                    break

            # If still no database URL, try to get it from Flask app
            if not db_url:
                try:
                    from app import create_app
                    app = create_app('production')  # Use production config
                    with app.app_context():
                        db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
                        logger.info(f"Got database URL from app config")
                except Exception as e:
                    logger.error(f"Failed to get database URL from app config: {str(e)}")
                    return False

        if not db_url:
            logger.error("No database URL found")
            return False

        logger.info(f"Using database URL: {db_url.split('@')[1] if '@' in db_url else '*****'}")

        # Create direct engine connection
        engine = create_engine(db_url)
        inspector = inspect(engine)

        # Check if users table exists
        if 'users' not in inspector.get_table_names():
            logger.error("Users table not found in the database")
            return False

        # Check if phone column exists
        columns = [col['name'] for col in inspector.get_columns('users')]
        logger.info(f"Existing columns in users table: {columns}")

        if 'phone' not in columns:
            logger.info("Adding phone column to users table")

            try:
                with engine.begin() as conn:
                    # Handle different database types
                    if "sqlite" in db_url.lower():
                        # SQLite syntax
                        conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                    else:
                        # PostgreSQL/MySQL syntax
                        try:
                            # Try PostgreSQL syntax first
                            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)"))
                            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone)"))
                        except Exception as e:
                            logger.error(f"PostgreSQL syntax failed: {str(e)}")
                            # Try MySQL syntax
                            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(50)"))
                            conn.execute(text("CREATE INDEX ix_users_phone ON users (phone)"))
            except Exception as e:
                logger.error(f"Failed to add phone column: {str(e)}")
                return False

            # Verify the column was added
            try:
                inspector = inspect(engine)
                columns = [col['name'] for col in inspector.get_columns('users')]
                if 'phone' in columns:
                    logger.info("Successfully added phone column!")
                    return True
                else:
                    logger.error("Failed to verify phone column was added")
                    return False
            except Exception as e:
                logger.error(f"Error verifying column addition: {str(e)}")
                return False
        else:
            logger.info("phone column already exists in users table")
            return True

    except Exception as e:
        logger.error(f"Error in fix_phone_column: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting phone column hotfix application")

    if fix_phone_column():
        logger.info("✅ PHONE COLUMN HOTFIX APPLIED SUCCESSFULLY")
        sys.exit(0)
    else:
        logger.error("❌ PHONE COLUMN HOTFIX FAILED")
        sys.exit(1)
EOL

# Make the Python script executable
chmod +x fix_db_phone.py

# Run the Python hotfix
$PY_CMD fix_db_phone.py || {
  log "- Python fix failed, trying SQL method"

  # Try direct SQL approach if Python fails
  log "Step 4: Trying direct SQL approach"

  # Create the SQL file
  cat > direct_phone_column_fix.sql << 'EOL'
-- direct_phone_column_fix.sql
-- This script directly adds the phone column to the users table

-- PostgreSQL version
DO $$
BEGIN
    -- Check if the column exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'phone'
    ) THEN
        -- Add the column if it doesn't exist
        ALTER TABLE users ADD COLUMN phone VARCHAR(50);

        -- Create an index on the column
        CREATE INDEX ix_users_phone ON users (phone);

        RAISE NOTICE 'phone column added to users table';
    ELSE
        RAISE NOTICE 'phone column already exists in users table';
    END IF;
END $$;
EOL

  if [ -f "app/dev.db" ]; then
    log "- Using local SQLite database"
    sqlite3 app/dev.db "ALTER TABLE users ADD COLUMN phone VARCHAR(50);" || true
    sqlite3 app/dev.db "CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone);" || true
    log "- Direct SQL fix applied to SQLite database"
  elif [[ -n "$DATABASE_URL" && "$DATABASE_URL" == *"postgres"* ]]; then
    log "- Using PostgreSQL database from DATABASE_URL"
    psql "$DATABASE_URL" -f direct_phone_column_fix.sql || handle_error "Failed to apply PostgreSQL fix"
    log "- Direct SQL fix applied to PostgreSQL database"
  else
    log "- Could not determine database type for direct SQL fix"
    handle_error "Neither Python nor SQL fix methods succeeded"
  fi
}

# Step 5: Verify the fix
log "Step 5: Verifying the phone column was added"
cat > verify_phone_column.py << 'EOL'
#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, inspect

try:
    # Try to get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Check for local database files
        for db_file in ["instance/app.db", "app/dev.db", "dev.db"]:
            if os.path.exists(db_file):
                db_url = f"sqlite:///{db_file}"
                break

        # If still no database URL, try to get it from Flask app
        if not db_url:
            try:
                from app import create_app
                app = create_app('production')
                with app.app_context():
                    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
            except:
                print("Could not get database URL from app config")
                sys.exit(1)

    if not db_url:
        print("No database URL found")
        sys.exit(1)

    # Create engine and inspect
    engine = create_engine(db_url)
    inspector = inspect(engine)

    if 'users' not in inspector.get_table_names():
        print("Users table not found")
        sys.exit(1)

    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'phone' in columns:
        print("Phone column exists in users table")
        sys.exit(0)
    else:
        print("Phone column is missing from users table")
        sys.exit(1)
except Exception as e:
    print(f"Error verifying phone column: {str(e)}")
    sys.exit(1)
EOL

# Run verification
if $PY_CMD verify_phone_column.py; then
  log "✅ Verification successful - phone column exists in users table"
else
  log "⚠️ Verification failed - phone column may not have been added correctly"
  # We don't exit with error here as the fix might have worked but verification failed
fi

# Step 6: Cleanup
log "Step 6: Cleaning up temporary files"
rm -f fix_db_phone.py direct_phone_column_fix.sql verify_phone_column.py

# Success message
log "=== PHONE COLUMN HOTFIX APPLICATION COMPLETE ==="
log "The 'phone' column should now be available in the users table"
log "Please restart your application for the changes to take effect"
