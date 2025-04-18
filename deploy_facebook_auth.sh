#!/bin/bash
# deploy_facebook_auth.sh - Script to deploy Facebook OAuth changes to GCP App Engine

set -e  # Exit immediately if a command exits with a non-zero status

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Facebook OAuth implementation deployment process${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install the Google Cloud SDK.${NC}"
    exit 1
fi

# Verify authentication
echo -e "${YELLOW}Verifying gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "@"; then
    echo -e "${RED}Not logged in to gcloud. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Display current configuration
echo -e "${YELLOW}Current gcloud configuration:${NC}"
gcloud config list --format='value(core.project, core.account)'

# First run the migration locally to test
echo -e "${YELLOW}Running migration locally to test...${NC}"
cd /Users/georgeroots/biz/find_a_meeting_spot/backend
python run_migrations.py

# Format and lint the code
echo -e "${YELLOW}Formatting Python code...${NC}"
python -m black app/
python -m isort app/

# Verify app.yaml exists
if [ ! -f "app.yaml" ]; then
    echo -e "${RED}Error: app.yaml not found in the current directory.${NC}"
    exit 1
fi

# Check for FACEBOOK_APP_ID in environment variables
if [ -z "${FACEBOOK_APP_ID}" ]; then
    echo -e "${YELLOW}Warning: FACEBOOK_APP_ID environment variable is not set.${NC}"
    echo -e "${YELLOW}Using the default value from frontend/src/config.ts: 1484265795195128${NC}"
    export FACEBOOK_APP_ID=1484265795195128
fi

# Update the app.yaml file to include FACEBOOK_APP_ID
echo -e "${YELLOW}Updating app.yaml with FACEBOOK_APP_ID...${NC}"
if ! grep -q "FACEBOOK_APP_ID" app.yaml; then
    # Find the env_variables section and add the FACEBOOK_APP_ID
    sed -i '' '/env_variables:/a\\
  FACEBOOK_APP_ID: "'${FACEBOOK_APP_ID}'"' app.yaml
    echo -e "${GREEN}Added FACEBOOK_APP_ID to app.yaml${NC}"
else
    echo -e "${YELLOW}FACEBOOK_APP_ID already exists in app.yaml${NC}"
fi

# Deploy to App Engine
echo -e "${YELLOW}Deploying Facebook OAuth implementation to App Engine...${NC}"
gcloud app deploy app.yaml --project=find-a-meeting-spot --quiet

echo -e "${GREEN}Deployment complete. Testing the Facebook authentication...${NC}"

# Test the Facebook authentication endpoint OPTIONS
echo -e "${YELLOW}Testing OPTIONS request to the Facebook callback endpoint...${NC}"
curl -i -X OPTIONS -H "Origin: http://localhost:3000" https://api.findameetingspot.com/api/v1/auth/facebook/callback

echo -e "\n${GREEN}Deployment process completed successfully.${NC}"
echo -e "${YELLOW}If you need to rollback, use: 'gcloud app versions list' to find previous versions and then 'gcloud app services set-traffic default --splits=<version_id>=1' to revert.${NC}"
