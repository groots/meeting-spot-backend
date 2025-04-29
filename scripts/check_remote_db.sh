#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Checking remote database schema...${NC}"

# Get authentication token from gcloud
echo -e "${YELLOW}Authenticating with Google Cloud...${NC}"
TOKEN=$(gcloud auth print-identity-token)

if [ -z "$TOKEN" ]; then
  echo -e "${RED}Failed to get authentication token. Please make sure you're logged in with gcloud.${NC}"
  echo "Try running: gcloud auth login"
  exit 1
fi

# Call the verification service with proper headers
echo -e "${YELLOW}Calling remote database verification service...${NC}"
RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" https://db-schema-verifier-vn5dwnwlzq-ue.a.run.app/)

# Check if curl command succeeded
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to connect to the database verification service.${NC}"
  exit 1
fi

# Print the response in a formatted way
echo -e "${GREEN}Remote Database Verification Results:${NC}"
echo "$RESPONSE" | python3 -m json.tool

# Extract verification status
COLUMN_VERIFICATION=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('column_verification', 'unknown'))")

# Check if there are users without usernames
USERS_WITHOUT_USERNAME=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('user_data', {}).get('users_without_username', 'unknown'))")

# Print a summary
echo ""
echo -e "${GREEN}Summary:${NC}"
echo -e "Column verification: $([ "$COLUMN_VERIFICATION" == "success" ] && echo "${GREEN}PASSED${NC}" || echo "${RED}FAILED${NC}")"

if [ "$USERS_WITHOUT_USERNAME" != "unknown" ]; then
  if [ "$USERS_WITHOUT_USERNAME" -gt 0 ]; then
    echo -e "Users without username: ${YELLOW}$USERS_WITHOUT_USERNAME users need to be fixed${NC}"
  else
    echo -e "Users without username: ${GREEN}All users have usernames${NC}"
  fi
fi

# Final status
if [ "$COLUMN_VERIFICATION" == "success" ] && [ "$USERS_WITHOUT_USERNAME" == "0" ]; then
  echo -e "\n${GREEN}✓ Database schema looks good!${NC}"
  exit 0
else
  echo -e "\n${YELLOW}⚠ Database schema needs attention. Please review the results above.${NC}"
  exit 1
fi
