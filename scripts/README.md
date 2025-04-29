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

### Legacy Verification Script

The root directory also contains a legacy verification script:

* `check-db.sh` - Simple script that calls the verification service without detailed output formatting

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

### `apply_remote_migrations_admin.sh`

A specialized version of the migration script that uses admin database credentials for situations where the regular user lacks the necessary privileges.

**Usage:**
```bash
./scripts/apply_remote_migrations_admin.sh
```

**What it does:**
- Similar to `apply_remote_migrations.sh` but uses the postgres admin user
- Provides more detailed schema verification after migration
- Shows sample of updated users
- Displays helpful error messages if the migration fails

### `fix_users_table_directly.sh`

A direct SQL approach to fixing the users table schema that avoids using the migration framework.

**Usage:**
```bash
./scripts/fix_users_table_directly.sh
```

**What it does:**
- Connects to the database using Cloud SQL Proxy
- Displays the current users table schema
- Creates a SQL script that handles possible permission issues
- Adds the missing columns if they don't exist
- Generates usernames from email addresses for users without usernames
- Shows the updated schema and a sample of users with generated usernames

**When to use:**
- When standard migrations fail due to permission issues
- When you need a more targeted approach to fix specific schema issues
- When you want to verify the script before running (it generates a SQL file that you can review)

## Deployment Scripts

The project also includes scripts to deploy the database verification service to Cloud Run:

* `deploy_verification.sh` - Deploys the database schema verification service to Cloud Run
* `deploy_verification_simple.sh` - Simplified version of the deployment script

These scripts:
- Build a Docker container with the verification code
- Deploy it to Cloud Run as an authenticated service
- Configure it to connect to the Cloud SQL instance
- Output the URL and how to authenticate with the service

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

### Common Migration Issues

- **Permission errors**: If you see "insufficient privilege" errors, try using the `fix_users_table_directly.sh` script which handles permissions more gracefully
- **Connection issues**: Make sure the Cloud SQL Proxy is running and connected
- **SQL errors**: Review the generated SQL in the `schema_fix.sql` file before executing

## Security Notes

- The remote migration script contains database credentials. Use with caution.
- Never commit actual production credentials to the repository.
- Consider using secrets management for sensitive information.
