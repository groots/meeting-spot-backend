#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Database Permission Grant Utility${NC}"
echo -e "${YELLOW}This script grants necessary permissions to the meetingspot user${NC}"
echo

# Change to the backend directory if script is called from elsewhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${SCRIPT_DIR}/.." || exit 1

# Set variables for Cloud SQL proxy and database
INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"
PROXY_PORT=5432
ADMIN_USER="postgres"
ADMIN_PASS=""  # You'll need to provide this when prompted
APP_USER="meetingspot"
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

# Get PostgreSQL admin password securely
echo -e "${YELLOW}Please enter the PostgreSQL admin password:${NC}"
read -s ADMIN_PASS
echo

if [ -z "$ADMIN_PASS" ]; then
    echo -e "${RED}Password cannot be empty${NC}"
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

# Test admin connection
echo -e "${YELLOW}Testing database connection with admin user...${NC}"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $PROXY_PORT -U $ADMIN_USER -d $DB_NAME -c "SELECT current_user, current_database();" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect with admin user. Check your credentials and proxy.${NC}"
    exit 1
fi
echo -e "${GREEN}Admin connection successful!${NC}"

# Create a SQL file with our permission grants
cat > grant_permissions.sql << EOL
-- Grant table owner privileges to meetingspot user for users table
ALTER TABLE users OWNER TO ${APP_USER};

-- Grant all privileges on the users table to meetingspot user
GRANT ALL PRIVILEGES ON TABLE users TO ${APP_USER};

-- Grant sequence privileges if any exist for users table
DO \$\$
DECLARE
    seq_name text;
BEGIN
    FOR seq_name IN
        SELECT pg_class.relname
        FROM pg_class
        JOIN pg_depend ON pg_depend.objid = pg_class.oid
        JOIN pg_class AS tablename ON pg_depend.refobjid = tablename.oid
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
        WHERE pg_class.relkind = 'S'
        AND tablename.relname = 'users'
        AND pg_namespace.nspname = 'public'
    LOOP
        EXECUTE format('GRANT ALL PRIVILEGES ON SEQUENCE %I TO ${APP_USER}', seq_name);
        RAISE NOTICE 'Granted privileges on sequence %', seq_name;
    END LOOP;
END \$\$;

-- Grant schema privileges
GRANT USAGE, CREATE ON SCHEMA public TO ${APP_USER};

-- Show the privileges granted to meetingspot user
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = '${APP_USER}' AND table_name = 'users';
EOL

# Run the permission grants
echo -e "${GREEN}Granting permissions to ${APP_USER} user...${NC}"
PGPASSWORD=$ADMIN_PASS psql -h localhost -p $PROXY_PORT -U $ADMIN_USER -d $DB_NAME -f grant_permissions.sql

# Test the permissions by trying to alter the table with the app user
echo -e "${YELLOW}Testing new permissions by attempting to alter table with ${APP_USER} user...${NC}"
PGPASSWORD="MeetingSpot123!" psql -h localhost -p $PROXY_PORT -U $APP_USER -d $DB_NAME -c "DO \$\$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'test_column'
    ) THEN
        ALTER TABLE users ADD COLUMN test_column VARCHAR(50);
        ALTER TABLE users DROP COLUMN test_column;
        RAISE NOTICE 'Successfully added and removed test column';
    END IF;
END \$\$;"

PERMISSION_TEST_RESULT=$?

# Clean up
rm grant_permissions.sql

# Check if permission test was successful
if [ $PERMISSION_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}Permissions granted successfully! The ${APP_USER} user can now alter the users table.${NC}"

    # Show users table schema to verify
    echo -e "${YELLOW}Current users table schema:${NC}"
    PGPASSWORD="MeetingSpot123!" psql -h localhost -p $PROXY_PORT -U $APP_USER -d $DB_NAME -c "\d users"

    echo -e "${GREEN}You can now run the apply_remote_migrations.sh script successfully.${NC}"
else
    echo -e "${RED}Permission test failed. Please check the output above for errors.${NC}"
fi
