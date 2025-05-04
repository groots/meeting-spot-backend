# Find a Meeting Spot Backend

This is the backend service for the Find a Meeting Spot application, providing API endpoints for user management, meeting coordination, and location-based services.

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
- [Development](#development)
  - [Running Locally](#running-locally)
  - [Testing](#testing)
  - [Code Style](#code-style)
- [Database Management](#database-management)
  - [Migration Strategy](#migration-strategy)
  - [Creating Migrations](#creating-migrations)
  - [Running Migrations Locally](#running-migrations-locally)
  - [Production Migrations](#production-migrations)
- [CI/CD](#cicd)
  - [GitHub Actions Workflows](#github-actions-workflows)
  - [Deployment Process](#deployment-process)
- [Architecture](#architecture)
  - [Project Structure](#project-structure)

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL (for production)
- Google Cloud SDK (for deployment and accessing production database)
- Docker (optional, for containerized development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/find-a-meeting-spot.git
cd find-a-meeting-spot/backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

For development, you may also want to install additional tools:
```bash
pip install -r requirements-dev.txt
```

### Environment Setup

Create a `.env` file with the following variables:

```bash
FLASK_APP=wsgi.py
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL="postgresql+psycopg2://postgres:password@localhost:5432/findameetingspot_dev"
SECRET_KEY="your-secret-key"
```

## Development

### Running Locally

1. Start the application:
```bash
flask run
```

2. The API will be available at http://localhost:5000

### Testing

Run tests with pytest:
```bash
pytest
```

For specific test files:
```bash
pytest tests/test_specific_file.py
```

### Code Style

This project uses Black for code formatting:

```bash
# Check code style
black --check .

# Fix code style issues
black .

# Using helper scripts (recommended)
./check_format.py  # Check formatting
./format_all.py    # Apply formatting
```

#### Excluding Files from Formatting

Some files are excluded from Black formatting due to compatibility issues. These files are listed in the `.noformat` file in the project root.

To exclude a file from Black formatting:
1. Add the file path to the `.noformat` file (one path per line)
2. The CI/CD pipeline and helper scripts will automatically skip these files

Current exclusions:
- `tests/test_notifications.py` - Known issue with Black's internal formatter

## Database Management

### Migration Strategy

Our database migration strategy is designed to:

1. **Ensure CI pipeline stability**: Migrations are skipped in CI to avoid dependency on the production database
2. **Support local development**: Connect to the database locally using Cloud SQL Proxy
3. **Control production migrations**: Run migrations in production using a dedicated workflow

### Creating Migrations

1. Set up local database connection:
```bash
# Make script executable if needed
chmod +x setup-local-db.sh
# Run the script
./setup-local-db.sh
```

2. Make model changes in the code

3. Generate a migration:
```bash
flask db migrate -m "Description of your changes"
```

4. Review the generated migration file in `migrations/versions/`

5. Test the migration locally:
```bash
flask db upgrade
```

### Running Migrations Locally

Connect to the production database locally:

```bash
./setup-local-db.sh
```

This will:
- Download and start the Cloud SQL Proxy
- Connect to your production database
- Set up the necessary environment variables
- Allow you to run migrations and develop locally with the production database

### Production Migrations

For running migrations in production, we use a dedicated GitHub Actions workflow:

1. Go to GitHub Actions in your repository
2. Select "Production Database Migrations" workflow
3. Click "Run workflow"
4. Type "yes" to confirm running migrations on production
5. Click "Run workflow" button

This process:
- Starts a Cloud SQL Proxy to connect to your production database
- Runs all pending migrations safely
- Verifies the migrations completed successfully
- Records the results in the GitHub Action summary

## CI/CD

### GitHub Actions Workflows

This project uses several GitHub Actions workflows:

1. **CI Deploy** (`ci-deploy.yaml`):
   - Runs tests
   - Checks code style
   - Deploys to Cloud Run
   - Skips database migrations (handled separately)

2. **Production Database Migrations** (`production-migrations.yaml`):
   - Manually triggered workflow
   - Requires explicit confirmation
   - Connects to production database
   - Applies pending migrations

3. **Migration Configuration** (`migration-config.yaml`):
   - Reusable workflow for migration settings
   - Controls migration behavior based on environment

### Deployment Process

The standard deployment process:

1. Push changes to the main branch
2. GitHub Actions will automatically run tests and deploy the application
3. Database migrations are skipped by default
4. To apply database changes, manually run the "Production Database Migrations" workflow

## Architecture

### Project Structure

```
backend/
├── app/                  # Application code
│   ├── api/              # API endpoints
│   ├── models/           # Database models
│   ├── services/         # Business logic
│   └── utils/            # Helper functions
├── migrations/           # Database migrations
│   ├── versions/         # Migration scripts
│   └── env.py            # Migration environment
├── tests/                # Test suite
├── .github/workflows/    # CI/CD configuration
├── deploy_db_migrations.py # Migration script
├── setup-local-db.sh     # Local DB connection helper
└── wsgi.py               # Application entry point
```

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
3. Fix any issues with the migration files
4. Run the migrations locally to test
5. Commit and push your fixes
6. Run the "Production Database Migrations" workflow again
