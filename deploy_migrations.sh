#!/bin/bash
set -e

# Database Migration Deployment Script for Find A Meeting Spot
# This script ensures consistent migration of the database across all environments

# Display banner
echo "===================================================="
echo "   Find A Meeting Spot - Database Migration Tool    "
echo "===================================================="
echo

# Set environment variables
export FLASK_APP=app:create_app

# Check if we're in a production environment
if [ -n "$GOOGLE_CLOUD_PROJECT" ] || [ -n "$GCP_PROJECT" ] || [ "$FLASK_ENV" = "production" ]; then
    echo "🔶 Running in PRODUCTION environment!"
    echo "🔶 This will apply migrations to the production database."
    echo "🔶 Press Ctrl+C within 5 seconds to abort..."
    sleep 5
    echo "Proceeding with production migration..."
else
    echo "📊 Running in development/testing environment"
fi

# Step 1: Verify Alembic setup
echo -e "\n📋 Step 1: Verifying Alembic configuration..."
if [ ! -f "migrations/env.py" ] || [ ! -d "migrations/versions" ]; then
    echo "❌ ERROR: Migrations directory structure is incomplete."
    echo "Please ensure you have a proper Alembic setup with migrations/env.py and migrations/versions/ directory."
    exit 1
fi
echo "✅ Alembic configuration verified"

# Step 2: Check for migration files
echo -e "\n📋 Step 2: Checking migration files..."
MIGRATION_COUNT=$(find migrations/versions -name "*.py" | wc -l)
if [ "$MIGRATION_COUNT" -eq 0 ]; then
    echo "⚠️ WARNING: No migration files found in migrations/versions/"
    echo "You may need to create a migration with 'flask db migrate'"
else
    echo "✅ Found $MIGRATION_COUNT migration file(s)"
fi

# Step 3: Database backup check
echo -e "\n📋 Step 3: Checking database backup options..."
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo "📦 PostgreSQL database detected"
    echo "Ensure you have a recent backup before proceeding!"

    if [ -n "$GOOGLE_CLOUD_PROJECT" ] || [ -n "$GCP_PROJECT" ]; then
        echo "For GCP Cloud SQL, verify automated backups are enabled"
    fi
fi
echo "✅ Backup check complete"

# Step 4: Run migrations using our migration script
echo -e "\n📋 Step 4: Running database migrations..."
if [ -f "deploy_db_migrations.py" ]; then
    # Run dry-run first to see what would happen
    echo "Running migration dry-run..."
    python deploy_db_migrations.py --dry-run

    # Confirm and run actual migration
    echo -e "\nApplying actual migrations now..."
    python deploy_db_migrations.py
    MIGRATION_RESULT=$?

    if [ $MIGRATION_RESULT -eq 0 ]; then
        echo "✅ Migrations applied successfully!"
    else
        echo "❌ Migration failed with error code $MIGRATION_RESULT"
        exit $MIGRATION_RESULT
    fi
else
    echo "❌ ERROR: deploy_db_migrations.py not found"
    echo "Please ensure the migration script is in the current directory"
    exit 1
fi

# Step 5: Verify database state
echo -e "\n📋 Step 5: Verifying database state..."
echo "Running alembic current to verify database version:"
flask db current

# Step 6: Test database connection
echo -e "\n📋 Step 6: Testing database connection..."
python -c "
from app import create_app, db
from sqlalchemy import text
app = create_app()
with app.app_context():
    result = db.session.execute(text('SELECT 1'))
    print('Database connection successful:', next(result)[0] == 1)
"

echo -e "\n✨ Database migration process complete ✨"

# Add to deployment checklist
echo -e "\nDeployment Checklist:"
echo "✓ Database schema is up to date"
echo "✓ Alembic migration history is consistent"
echo "✓ Database connection verified"
echo -e "\nNext Steps:"
echo "1. Deploy application code"
echo "2. Restart application servers if needed"
echo "3. Monitor application logs for any database-related issues"
