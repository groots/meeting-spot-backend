#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Direct Database Schema Fix Utility${NC}"
echo -e "${YELLOW}This script applies schema changes directly to the users table using SQL${NC}"
echo

# Change to the backend directory if script is called from elsewhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${SCRIPT_DIR}/.." || exit 1

# Set variables for Cloud SQL proxy and database
INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"
PROXY_PORT=5432
DB_USER="meetingspot"
DB_PASS="MeetingSpot123!"
DB_NAME="findameetingspot"

echo -e "${YELLOW}Setting up Cloud SQL Proxy to connect to remote database...${NC}"

# Check if cloud_sql_proxy is installed
if ! command -v cloud_sql_proxy &> /dev/null; then
    echo -e "${RED}Cloud SQL Proxy not found. Please install it first:${NC}"
    echo "https://cloud.google.com/sql/docs/postgres/sql-proxy#install"
    exit 1
fi

# Check if the user is logged in to gcloud
gcloud auth print-access-token &>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}You are not logged in to Google Cloud. Please login first:${NC}"
    echo "gcloud auth login"
    exit 1
fi

# Start Cloud SQL proxy
echo -e "${YELLOW}Starting Cloud SQL Proxy...${NC}"
cloud_sql_proxy -instances=${INSTANCE_CONNECTION_NAME}=tcp:${PROXY_PORT} &
PROXY_PID=$!

# Wait for the proxy to start
echo -e "${YELLOW}Waiting for proxy connection...${NC}"
sleep 5

# Trap to kill the proxy on exit
trap 'kill $PROXY_PID; echo -e "${GREEN}Cloud SQL Proxy stopped.${NC}"; exit' EXIT INT TERM

# Test the connection
echo -e "${YELLOW}Testing database connection...${NC}"
PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -c "SELECT current_user, current_database();"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect to the database. Check your credentials and proxy.${NC}"
    exit 1
fi
echo -e "${GREEN}Database connection successful!${NC}"

# Get current users table schema
echo -e "${YELLOW}Current users table schema:${NC}"
PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -c "\d users"

# Check if username column exists
echo -e "${YELLOW}Checking if username column exists...${NC}"
USERNAME_EXISTS=$(PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='username')")
USERNAME_EXISTS=$(echo $USERNAME_EXISTS | tr -d ' ')

# Confirm before proceeding
echo
echo -e "${YELLOW}This will directly modify the users table schema in the PRODUCTION database.${NC}"
echo -e "${RED}WARNING: This is a potentially destructive operation. Make sure you have a backup.${NC}"
read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Operation cancelled.${NC}"
    exit 1
fi

# Create a SQL file with our schema modifications
cat > schema_fix.sql << EOL
-- Add username column if it doesn't exist
DO \$\$
BEGIN
    BEGIN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(50);
        RAISE NOTICE 'Username column added or already exists';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE WARNING 'Insufficient privilege to add username column';
    END;

    BEGIN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(50);
        RAISE NOTICE 'first_name column added or already exists';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE WARNING 'Insufficient privilege to add first_name column';
    END;

    BEGIN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(50);
        RAISE NOTICE 'last_name column added or already exists';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE WARNING 'Insufficient privilege to add last_name column';
    END;

    BEGIN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_oauth_id VARCHAR(255);
        RAISE NOTICE 'facebook_oauth_id column added or already exists';
    EXCEPTION WHEN insufficient_privilege THEN
        RAISE WARNING 'Insufficient privilege to add facebook_oauth_id column';
    END;
END \$\$;

-- Generate usernames from email for users without usernames
UPDATE users
SET username = SPLIT_PART(email, '@', 1)
WHERE username IS NULL AND position('@' in email) > 0;

-- For emails without @ symbol, use the whole email
UPDATE users
SET username = email
WHERE username IS NULL AND position('@' in email) = 0;

-- For any remaining users without usernames, set a default
UPDATE users
SET username = 'user_' || id
WHERE username IS NULL;

-- Output the results
SELECT COUNT(*) AS users_with_username FROM users WHERE username IS NOT NULL;
SELECT COUNT(*) AS users_without_username FROM users WHERE username IS NULL;
EOL

# Run the schema fix SQL
echo -e "${GREEN}Applying schema changes...${NC}"
PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -f schema_fix.sql

# Show the updated schema
echo -e "${YELLOW}Updated users table schema:${NC}"
PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -c "\d users"

# Clean up
rm schema_fix.sql

# Success message
echo -e "${GREEN}Schema changes applied successfully!${NC}"

# Verify username generation
echo -e "${YELLOW}Sample of users with generated usernames:${NC}"
PGPASSWORD=$DB_PASS psql -h localhost -p $PROXY_PORT -U $DB_USER -d $DB_NAME -c "SELECT id, email, username FROM users LIMIT 5;"
