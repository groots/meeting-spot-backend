#!/bin/bash
# Script to reorganize the project structure

set -e

# Color codes for better visibility
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting project reorganization...${NC}"

# Create necessary directories
mkdir -p backend/app
mkdir -p backend/migrations
mkdir -p backend/scripts
mkdir -p backend/utils
mkdir -p backend/tests
mkdir -p backend/docs
mkdir -p backend/config

# Display current state
echo -e "${YELLOW}Current files at the root level:${NC}"
find . -maxdepth 1 -type f -not -path './\.*' | sort
echo -e "${YELLOW}Current directories at the root level:${NC}"
find . -maxdepth 1 -type d -not -path './\.*' -not -path '.' | sort

# Move app directory to backend
echo -e "${GREEN}Moving app directory to backend...${NC}"
cp -R app/* backend/app/
echo -e "${GREEN}✓ Moved app to backend/app${NC}"

# Move migrations to backend
echo -e "${GREEN}Moving migrations to backend...${NC}"
cp -R migrations/* backend/migrations/
echo -e "${GREEN}✓ Moved migrations to backend/migrations${NC}"

# Move important configuration and deployment files
echo -e "${GREEN}Moving configuration and deployment files...${NC}"
cp app.yaml backend/
cp -f deploy_to_cloud_run.sh backend/
cp wsgi.py backend/ 2>/dev/null || :
cp config.py backend/config/ 2>/dev/null || :
cp requirements*.txt backend/ 2>/dev/null || :
cp Dockerfile* backend/ 2>/dev/null || :
cp cloud*proxy backend/ 2>/dev/null || :
cp *.sql backend/ 2>/dev/null || :
cp *.py backend/ 2>/dev/null || :
cp *.sh backend/ 2>/dev/null || :
cp *.yaml backend/ 2>/dev/null || :
echo -e "${GREEN}✓ Moved configuration and deployment files${NC}"

# Update import paths in backend Python files if needed
echo -e "${YELLOW}Note: You may need to update import paths in Python files${NC}"
echo -e "${YELLOW}For example, change 'from app import db' to 'from backend.app import db'${NC}"

echo -e "${GREEN}Reorganization completed!${NC}"
echo -e "${YELLOW}Please review the backend directory to ensure everything was copied correctly.${NC}"
echo -e "${YELLOW}Once verified, you can remove the duplicated files from the root directory.${NC}"
