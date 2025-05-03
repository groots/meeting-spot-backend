-- direct_phone_column_fix.sql
-- This script directly adds the phone column to the users table
-- Use this as a fallback if the Python migrations fail

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

-- SQLite version (in a separate file or as a comment)
/*
-- For SQLite databases:
-- Check if the column exists (this needs to be done in application code)
-- SQLite doesn't support IF NOT EXISTS for ADD COLUMN

-- Add the column
ALTER TABLE users ADD COLUMN phone VARCHAR(50);

-- Create an index on the column
CREATE INDEX IF NOT EXISTS ix_users_phone ON users (phone);
*/

-- MySQL version
/*
-- For MySQL databases:
-- Check if the column exists
SET @column_exists = 0;
SELECT COUNT(*) INTO @column_exists
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'phone';

-- Add the column if it doesn't exist
SET @query = IF(@column_exists = 0,
    'ALTER TABLE users ADD COLUMN phone VARCHAR(50)',
    'SELECT "phone column already exists in users table"');
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create an index on the column
CREATE INDEX ix_users_phone ON users (phone);
*/
