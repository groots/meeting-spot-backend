# Database Utilities

This directory contains utility scripts for managing, verifying, and maintaining the database for the FindAMeetingSpot application.

## Database Verification Scripts

### `check_local_db.sh`

This script verifies the local database schema to ensure all required columns exist and user data is properly formatted.

**Usage:**
```bash
./scripts/check_local_db.sh
```

**What it does:**
- Connects to the local PostgreSQL database using configuration from environment variables
- Verifies that all required columns exist in the database schema
- Checks if all users have username values properly set
- Reports detailed results and exits with appropriate exit code

### `check_remote_db.sh`

This script verifies the remote (production) database schema by connecting to the schema verification Cloud Run service.

**Usage:**
```bash
./scripts/check_remote_db.sh
```

**What it does:**
- Authenticates with Google Cloud using gcloud
- Calls the remote database verification service deployed on Cloud Run
- Parses and displays the verification results in a user-friendly format
- Exits with non-zero code if issues are found

## Database Migration Scripts

### `apply_remote_migrations.sh`

This script applies database migrations to the remote (production) database via Cloud SQL Proxy.

**Usage:**
```bash
./scripts/apply_remote_migrations.sh
```

**What it does:**
- Sets up a Cloud SQL Proxy connection to the production database
- Shows the current migration version
- Confirms with the user before proceeding
- Applies all pending migrations using `run_migrations_directly.py`
- Verifies the schema after migrations are applied
- Provides detailed output of the operation

**Prerequisites:**
- [Cloud SQL Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy#install) must be installed
- User must be authenticated with Google Cloud (`gcloud auth login`)
- PostgreSQL client (`psql`) must be installed

## Other Database Related Scripts

- `fix_imports.sh` - Fixes Python imports in database-related files
- `fix_types.sh` - Fixes type annotations in database models
- `deploy.sh` - Deploys the application with database migrations

## Database Schema Verification

The database schema verification checks for the following required columns in the users table:
- `username`
- `first_name`
- `last_name`
- `facebook_oauth_id`

These columns were added in the migration `fix_missing_username_fields.py` and are critical for proper application function.

## Troubleshooting

If you encounter issues with database verification or migrations:

1. Check that your database connection settings are correct in `.env` or environment variables
2. Ensure you have the necessary permissions to access the database
3. For remote database operations, verify your Google Cloud credentials
4. Check the logs for detailed error messages

## Security Notes

- The remote migration script contains database credentials. Use with caution.
- Never commit actual production credentials to the repository.
- Consider using secrets management for sensitive information.
