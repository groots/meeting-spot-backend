-- Check current column definition
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'password_hash';

-- Alter the column to 256 characters
ALTER TABLE users
ALTER COLUMN password_hash TYPE varchar(256);

-- Verify the change
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'password_hash';
