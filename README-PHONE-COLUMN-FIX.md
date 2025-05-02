# Missing Phone Column Hotfix

## Issue Description

The application is experiencing 500 errors on meeting requests and profile picture uploads with the following error:

```
Server error: (pg8000.dbapi.ProgrammingError) {'S': 'ERROR', 'V': 'ERROR', 'C': '42703', 'M': 'column users.phone does not exist', 'P': '166', 'F': 'parse_relation.c', 'L': '3676', 'R': 'errorMissingColumn'}
[SQL: SELECT users.id AS users_id, users.email AS users_email, users.username AS users_username, users.first_name AS users_first_name, users.last_name AS users_last_name, users.phone AS users_phone, users.facebook_oauth_id AS users_facebook_oauth_id, users.profile_picture_url AS users_profile_picture_url, users.password_hash AS users_password_hash, users.google_oauth_id AS users_google_oauth_id, users.created_at AS users_created_at, users.updated_at AS users_updated_at FROM users WHERE users.id = %s::UUID LIMIT %s::INTEGER]
```

### Root Cause
The application code is trying to access a `phone` column in the `users` table, but this column does not exist in the production database schema. This indicates that:

1. The `phone` column exists in the User model in code
2. The column has been added to development/testing databases
3. The migration to add this column was never applied to the production database

## Solution

This hotfix includes several approaches to fix the issue:

### 1. Alembic Migration Approach (Recommended)

We've created a dedicated migration file to add the missing column:
- File: `migrations/versions/add_phone_column_hotfix.py`
- This migration checks if the column exists before attempting to add it
- It also adds an index on the phone column for performance

To apply this migration:

```bash
cd backend
chmod +x apply_phone_column_hotfix.sh
./apply_phone_column_hotfix.sh
```

The script will:
1. Verify the migration file exists
2. Try to back up the database if possible
3. Check the existing columns in the users table
4. Apply the migration
5. Verify the migration was successful
6. Restart the application

### 2. Direct SQL Approach (Fallback)

If the migration approach fails, you can directly run SQL to add the column:
- File: `direct_phone_column_fix.sql`

To apply this SQL script directly:

```bash
# For PostgreSQL
psql <DATABASE_URL> -f direct_phone_column_fix.sql

# Or within psql
\i direct_phone_column_fix.sql
```

## Verification

After applying the fix, verify that:

1. The `phone` column exists in the `users` table:
   ```sql
   SELECT column_name FROM information_schema.columns WHERE table_name = 'users';
   ```

2. Meeting requests endpoint (/api/v1/meeting-requests/) works without errors
3. Profile picture upload endpoint (/api/v1/auth/me/picture) works without errors

## Prevention

To prevent similar issues in the future:

1. Ensure that all migrations are tracked and applied to all environments
2. Add pre-deployment checks to verify database schema matches the expected state
3. Consider implementing automated migration testing in CI/CD pipeline
4. Add monitoring to detect and alert on database-related 500 errors

## Additional Notes

This issue highlights the importance of maintaining schema consistency across environments. In some cases, adding a column to a model without properly creating and applying a migration can lead to these types of errors.

The `phone` column is used for contact information and allows users to provide a phone number on their profile, but it's nullable so existing records will continue to work properly after the fix.
