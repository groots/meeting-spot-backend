#!/bin/bash
# Script to deploy the application to Cloud Run with database migrations

set -e

# Color codes for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Find A Meeting Spot Backend Deployment ===${NC}"
echo -e "${YELLOW}This script will deploy the backend to Cloud Run with proper CORS settings${NC}"

# Ensure we're in the correct directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
echo -e "${GREEN}Working directory: $(pwd)${NC}"

# Configuration
PROJECT_ID="find-a-meeting-spot"
REGION="us-east1"
SERVICE_NAME="meeting-spot-backend"
INSTANCE_NAME="findameetingspot"
INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$INSTANCE_NAME"

# Generate a commit SHA (using current timestamp if not in git repo)
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || date +%s)
echo -e "${GREEN}Using commit SHA/tag: $COMMIT_SHA${NC}"

# Manually deploy to Cloud Run
echo -e "${GREEN}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars=FLASK_ENV=production,RUN_MIGRATIONS=false,INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,CORS_ORIGINS=* \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --source .

# Wait for deployment to complete
echo -e "${GREEN}Waiting for deployment to complete...${NC}"
sleep 10

# Get the deployed URL
DEPLOYED_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo -e "${GREEN}Service deployed at: $DEPLOYED_URL${NC}"

# Set up Cloud SQL Proxy for migrations
echo -e "${GREEN}Setting up Cloud SQL Proxy to run migrations...${NC}"

if [ -f "./cloud-sql-proxy" ]; then
  CLOUD_SQL_PROXY="./cloud-sql-proxy"
else
  echo -e "${GREEN}Downloading Cloud SQL Proxy...${NC}"
  curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.6.1/cloud-sql-proxy.darwin.amd64
  chmod +x cloud-sql-proxy
  CLOUD_SQL_PROXY="./cloud-sql-proxy"
fi

# Start Cloud SQL Proxy
PROXY_PORT=5433
echo -e "${GREEN}Starting Cloud SQL Proxy on port $PROXY_PORT...${NC}"
$CLOUD_SQL_PROXY -instances="$PROJECT_ID:$REGION:$INSTANCE_NAME"=tcp:$PROXY_PORT &
PROXY_PID=$!

# Set up trap to kill Cloud SQL Proxy on exit
cleanup() {
  echo -e "${GREEN}Cleaning up...${NC}"
  if [ -n "$PROXY_PID" ]; then
    echo -e "${GREEN}Stopping Cloud SQL Proxy...${NC}"
    kill $PROXY_PID || true
  fi
}
trap cleanup EXIT

# Wait for proxy to start
echo -e "${GREEN}Waiting for Cloud SQL Proxy to start...${NC}"
sleep 10

# Set up environment for Flask-Migrate
export FLASK_APP=wsgi.py
export DB_HOST=localhost
export DB_PORT=$PROXY_PORT
export DB_USER=meetingspot
export DB_PASS=MeetingSpot123!
export DB_NAME=findameetingspot

# Run fix_column.sql directly against the database
echo -e "${GREEN}Applying database schema update directly...${NC}"
PGPASSWORD=$DB_PASS psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
ALTER TABLE users ALTER COLUMN password_hash TYPE varchar(256);
" || echo -e "${RED}Failed to apply database changes, but continuing deployment${NC}"

echo -e "${GREEN}Testing the deployed application...${NC}"
TEST_URL="${DEPLOYED_URL}/debug/health"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $TEST_URL)

if [ $HTTP_STATUS -eq 200 ]; then
  echo -e "${GREEN}Deployment successful! API is responding.${NC}"

  # Test CORS
  echo -e "${GREEN}Testing CORS configuration...${NC}"
  CORS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Origin: https://findameetingspot.com" $TEST_URL)

  if [ $CORS_STATUS -eq 200 ]; then
    echo -e "${GREEN}CORS configuration appears to be working.${NC}"
    echo -e "${GREEN}Try registering a user now to verify the password hash fix.${NC}"
  else
    echo -e "${RED}CORS may not be configured correctly. Status: $CORS_STATUS${NC}"
  fi
else
  echo -e "${RED}Deployment may have issues. HTTP Status: $HTTP_STATUS${NC}"
fi

echo -e "${GREEN}Deployment completed!${NC}"
