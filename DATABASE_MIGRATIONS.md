# Database Migration Strategy

This document explains our approach to database migrations in the Find a Meeting Spot application.

## Overview

Our database migration strategy is designed to:

1. **Ensure CI pipeline stability**: Migrations are skipped in CI to avoid dependency on the production database
2. **Support local development**: Connect to the database locally using Cloud SQL Proxy
3. **Controlled production migrations**: Run migrations in production using a dedicated workflow

## Migration Workflows

### CI/CD Pipeline

The main CI/CD pipeline (`ci-deploy.yaml`) **skips database migrations** by default by setting:

```
SKIP_DB_MIGRATIONS_IN_CI=true
```

This ensures deployments don't depend on database connectivity or attempts to perform potentially risky schema modifications automatically.

### Production Migrations

For running migrations in production, we use a dedicated workflow:

1. Go to GitHub Actions in your repository
2. Select "Production Database Migrations" workflow
3. Click "Run workflow"
4. Type "yes" to confirm running migrations on production
5. Click "Run workflow" button

This will:
- Start a Cloud SQL Proxy to connect to your production database
- Run all pending migrations safely
- Verify the migrations completed successfully
- Record the results in the GitHub Action summary

## Local Development

For local development with the production database:

1. Make sure you have Google Cloud SDK installed
2. Authenticate with `gcloud auth login`
3. Run the helper script:

```bash
cd backend
# Make script executable if needed
chmod +x setup-local-db.sh
# Run the script
./setup-local-db.sh
```

This will:
- Download and start the Cloud SQL Proxy
- Connect to your production database
- Set up the necessary environment variables
- Allow you to run migrations and develop locally with the production database

While the script is running, you can:
- Run migrations: `python deploy_db_migrations.py`
- Run the application: `flask run`
- Run tests: `pytest`

## Creating New Migrations

To create a new migration:

1. Set up local database connection using `setup-local-db.sh`
2. Make your model changes in the code
3. Generate a migration:

```bash
flask db migrate -m "Description of your changes"
```

4. Review the generated migration file in `migrations/versions/`
5. If needed, edit the migration file to ensure it does exactly what you want
6. Test the migration locally:

```bash
flask db upgrade
```

7. Commit your changes and migration file
8. Push to GitHub
9. Deploy your application using the normal CI/CD pipeline
10. Run the "Production Database Migrations" workflow to apply your migrations to production

## Troubleshooting

### Migration Errors in CI

If you see migration errors in CI, check:

1. The CI workflow is configured to skip migrations (it should be)
2. The `env.py` file correctly identifies CI environments
3. The `deploy_db_migrations.py` script respects the CI environment variables

### Failed Migrations in Production

If a migration fails in production:

1. Check the error message in the workflow logs
2. Connect to the database locally using `setup-local-db.sh`
3. Run `flask db current` to see the current migration version
4. Fix any issues with the migration files
5. Run the migrations locally to test: `flask db upgrade`
6. Commit and push your fixes
7. Run the "Production Database Migrations" workflow again

## Best Practices

1. **Always test migrations locally** before running them in production
2. **One change per migration** - keep migrations focused on specific changes
3. **Make migrations reversible** where possible (implement `downgrade()` functions)
4. **Treat migration files as immutable** once they've been applied to any environment
5. **Backup the database** before running major migrations
6. **Plan for rollbacks** in case a migration fails
7. **Run migrations during low-traffic periods** for production systems
