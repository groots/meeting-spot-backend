#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Remote Migration Utility (ADMIN MODE)${NC}"
echo -e "${YELLOW}This script applies database migrations to the remote Cloud SQL database using the postgres admin user${NC}"
echo

# Change to the backend directory if script is called from elsewhere
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "${SCRIPT_DIR}/.." || exit 1

# Set variables for Cloud SQL proxy and database
INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"
PROXY_PORT=5432
DB_USER="postgres"  # Using postgres admin user
DB_PASS="ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ"  # Admin password
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

# Set up environment variables for Flask-Migrate
export DB_HOST=localhost
export DB_PORT=$PROXY_PORT
export DB_USER=$DB_USER
export DB_PASS=$DB_PASS
export DB_NAME=$DB_NAME
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Print the masked database URL
MASKED_URL="postgresql://${DB_USER}:***@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo -e "${YELLOW}Using database URL: ${MASKED_URL}${NC}"

# Test the connection
echo -e "${YELLOW}Testing database connection with admin privileges...${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT current_user, current_database();"
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to connect to the database. Check your credentials and proxy.${NC}"
    exit 1
fi
echo -e "${GREEN}Database connection successful!${NC}"

# Show current migration version
echo -e "${YELLOW}Current migration version:${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version_num FROM alembic_version;"

# Confirm before proceeding
echo
echo -e "${RED}!!! ADMIN MODE !!!${NC}"
echo -e "${YELLOW}This will apply all pending database migrations to the PRODUCTION database using ADMIN privileges.${NC}"
echo -e "${RED}WARNING: This is a potentially destructive operation. Make sure you have a backup.${NC}"
read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Migration cancelled.${NC}"
    exit 1
fi

# Run the migrations
echo -e "${GREEN}Running database migrations with admin privileges...${NC}"
python run_migrations_directly.py
MIGRATION_RESULT=$?

# Check if the migration was successful
if [ $MIGRATION_RESULT -ne 0 ]; then
    echo -e "${RED}Migration failed with exit code: ${MIGRATION_RESULT}${NC}"
    echo -e "${RED}Please check the logs above for the specific error.${NC}"
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "  - Database credentials may be incorrect"
    echo -e "  - Network connectivity issues with the Cloud SQL Proxy"
    echo -e "  - Database may already be migrated or schema conflicts"
    exit 1
fi

# Show new migration version
echo -e "${YELLOW}New migration version:${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT version_num FROM alembic_version;"

# List the columns in the users table to verify the migration
echo -e "${YELLOW}Verifying users table schema:${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\d users"

# Get count of users without usernames
echo -e "${YELLOW}Checking users without usernames:${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM users WHERE username IS NULL;"

# Success message
echo -e "${GREEN}Migration completed successfully!${NC}"
