# GitHub Actions Database Migrations Guide

This guide explains the approach for running database migrations in GitHub Actions CI environment for the Find A Meeting Spot application.

## Problem

When running database migrations in GitHub Actions, we encountered several issues:

1. **Unix socket connection errors**: The pg8000 adapter attempts to use Unix sockets when connecting to localhost, which don't exist in the GitHub Actions environment.
2. **SSL configuration issues**: The SQLAlchemy `immutabledict` couldn't be modified to add SSL parameters.
3. **Connection parameter handling**: Different versions of pg8000/SQLAlchemy handle connection parameters differently.

## Solution

We created a custom GitHub Actions migration script (`github_migrations.py`) that:

1. Properly detects if running in GitHub Actions environment
2. Configures database connection parameters that work in CI
3. Disables SSL for test environments
4. Uses TCP/IP connections instead of Unix sockets
5. Has proper error handling specific to CI environments
6. Provides comprehensive logging

## Using the Script

The script can be run directly from the command line:

```bash
# Check if migrations are needed
python github_migrations.py --check

# Apply migrations
python github_migrations.py --upgrade

# Skip errors (useful for CI)
python github_migrations.py --upgrade --skip-errors
```

### Command Line Options

- `--check`: Check if migrations are needed
- `--upgrade`: Apply all available migrations
- `--downgrade <revision>`: Downgrade to a specific revision
- `--skip-errors`: Skip errors and continue (for CI environments)
- `--force`: Force migrations even in CI environments

## GitHub Actions Workflow

The `.github/workflows/db-migrations.yml` file configures a workflow that:

1. Runs on pushes to `main` that affect migrations or models
2. Sets up a PostgreSQL database service for testing
3. Runs the migration script with appropriate flags
4. Creates a summary of the migration attempt

This workflow is a safe way to validate migrations without affecting production. It doesn't make any changes to the production database, but confirms that migrations will run correctly.

## Local Testing

You can test the GitHub Actions migration flow locally by:

1. Setting up a local PostgreSQL database
2. Running the script with appropriate parameters:

```bash
# Set up environment variables similar to GitHub Actions
export PGUSER=postgres
export PGPASSWORD=postgres
export PGHOST=localhost
export PGDATABASE=test_db

# Run migrations
python github_migrations.py --upgrade
```

## Troubleshooting

If you encounter issues with the migrations in GitHub Actions:

1. Check the workflow logs for detailed error messages
2. Make sure your database models and migrations are compatible
3. Verify the pg8000 version in requirements.txt
4. Check if you're using Unix socket paths in your connection strings
5. Look for SSL configuration issues

## Implementation Details

The custom script works by:

1. Creating the connection URL appropriate for GitHub Actions
2. Bypassing the SQLAlchemy URL immutability by modifying environment variables
3. Testing the connection before attempting migrations
4. Using direct Flask-Migrate commands rather than Alembic CLI
5. Providing detailed logging for debugging

This approach avoids the complexities of the standard Alembic environment when running in CI environments.
