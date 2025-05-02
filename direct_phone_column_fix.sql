-- Direct SQL fix for missing phone column in users table
-- Use this script if the migration approach fails

-- First check if the column already exists to avoid errors
DO $$
BEGIN
    -- Check if column already exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'phone'
    ) THEN
        -- Add the column if it doesn't exist
        ALTER TABLE users ADD COLUMN phone VARCHAR(50);

        -- Add an index on the column
        CREATE INDEX ix_users_phone ON users (phone);

        RAISE NOTICE 'Added phone column to users table successfully';
    ELSE
        RAISE NOTICE 'phone column already exists in users table';
    END IF;
END $$;
