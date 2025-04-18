#!/bin/bash
# deploy_cors_fix.sh - Script to deploy CORS fixes to GCP App Engine

set -e  # Exit immediately if a command exits with a non-zero status

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CORS fix deployment process${NC}"

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

# Format and lint the code
echo -e "${YELLOW}Formatting Python code...${NC}"
cd /Users/georgeroots/biz/find_a_meeting_spot/backend
python -m black app/
python -m isort app/

# Run a quick test to ensure things are working
echo -e "${YELLOW}Running a quick test of the CORS handler...${NC}"
python -c "from app import create_app; app = create_app(); print('CORS handlers registered:', [rule.rule for rule in app.url_map.iter_rules() if 'OPTIONS' in rule.methods and 'basic-register' in rule.rule])"

# Verify app.yaml exists
if [ ! -f "app.yaml" ]; then
    echo -e "${RED}Error: app.yaml not found in the current directory.${NC}"
    exit 1
fi

# Deploy to App Engine
echo -e "${YELLOW}Deploying CORS fixes to App Engine...${NC}"
gcloud app deploy app.yaml --project=find-a-meeting-spot --quiet

echo -e "${GREEN}Deployment complete. Testing the CORS configuration...${NC}"

# Test the CORS configuration
echo -e "${YELLOW}Testing OPTIONS request to the basic-register endpoint...${NC}"
curl -i -X OPTIONS -H "Origin: http://localhost:3000" https://api.findameetingspot.com/debug/basic-register

echo -e "\n${GREEN}Deployment process completed successfully.${NC}"
echo -e "${YELLOW}If you need to rollback, use: 'gcloud app versions list' to find previous versions and then 'gcloud app services set-traffic default --splits=<version_id>=1' to revert.${NC}"
