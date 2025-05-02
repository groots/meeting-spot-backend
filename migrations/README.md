# Database Migrations Guide

This directory contains the database migration system for the "Find A Meeting Spot" application, powered by Alembic and Flask-Migrate.

## Migration Architecture

- **Framework**: Alembic (with Flask-Migrate integration)
- **Storage**: Migration scripts are stored in `versions/` directory
- **Configuration**: `alembic.ini` and `env.py` contain the configuration
- **Automation**: `deploy_db_migrations.py` handles safe migration deployment

## Creating New Migrations

When you make changes to your models, create a new migration with:

```bash
flask db migrate -m "Description of the changes"
```

This will:
1. Detect changes between your models and the current database schema
2. Create a new migration file in `versions/` directory
3. The migration file will have an automatically generated revision ID and contain upgrade/downgrade functions

## Review Generated Migrations

Always review the generated migration files before applying them:

1. Check that the correct changes were detected
2. Verify that the upgrade/downgrade functions work as expected
3. Add any custom logic if needed (data transformations, etc.)

## Applying Migrations

### Development Environment

```bash
# Apply all pending migrations
flask db upgrade

# Check current database version
flask db current
```

### Production Environment

For production deployments, use the automated script:

```bash
./deploy_migrations.sh
```

This script:
- Performs safety checks
- Creates a backup if possible
- Applies migrations in a controlled manner
- Verifies the database state after migration

## Common Migration Tasks

### Adding a new column to an existing table

```python
# In your migration file's upgrade() function:
op.add_column('table_name', sa.Column('new_column', sa.String(50), nullable=True))
```

### Creating a new index

```python
op.create_index(op.f('ix_table_name_column_name'), 'table_name', ['column_name'], unique=False)
```

### Safely checking if an object exists before modifying

```python
conn = op.get_bind()
inspector = inspect(conn)
if 'column_name' not in [col['name'] for col in inspector.get_columns('table_name')]:
    # Perform operation only if the column doesn't exist
    op.add_column('table_name', sa.Column('column_name', sa.String(50), nullable=True))
```

## Troubleshooting

### Migration conflicts

If you encounter conflicts between your local migration history and the database:

```bash
# Stamp the database with the current migration without applying changes
flask db stamp head
```

### Database verification

To check if migrations need to be applied:

```bash
flask db check
```

### Manual fixes

For emergency fixes when migrations can't be applied normally:

1. Create a custom migration script
2. Use raw SQL if needed:
   ```python
   op.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(50);")
   ```
3. Make it idempotent (safe to run multiple times)

## Best Practices

1. Never edit migration files after they've been committed/applied
2. Keep migrations small and focused on specific changes
3. Test migrations on a staging environment before production
4. Always back up the database before applying migrations in production
5. Include data migrations along with schema changes when needed
6. Add proper error handling for idempotency in critical migrations
