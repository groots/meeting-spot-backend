#!/bin/bash
# Script to fix the facebook_oauth_id column in the users table

set -e

# Default settings
API_BASE=${API_BASE:-"https://api.findameetingspot.com"}
ENVIRONMENT=${ENVIRONMENT:-"production"} # Options: local, production

# Check if we want to run locally
if [ "$1" == "local" ]; then
  API_BASE="http://localhost:5000"
  ENVIRONMENT="local"
fi

echo "Starting fix for facebook_oauth_id column..."
echo "Using API base URL: $API_BASE (${ENVIRONMENT})"

# Call the fix-facebook-column-simple endpoint
echo "Calling endpoint to add column..."
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/v1/debug/fix-facebook-column-simple")

# Extract the status code
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$ d')

echo "HTTP Status Code: $HTTP_CODE"
echo "Response body:"
echo "$BODY"

# Attempt to parse JSON response, fall back to treating it as plain text
if [[ "$BODY" == {* ]]; then
  # Looks like JSON
  echo "Received JSON response"
else
  echo "Received non-JSON response"
fi

if [ $HTTP_CODE -eq 200 ]; then
  echo -e "\n✅ Fix operation complete! The endpoint returned status 200."
  echo "The subscription API calls should now work correctly."

  # Direct SQL solution for GCP Cloud SQL
  if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "\n⚠️ If the above fix didn't work, you might need to add the column directly in Cloud SQL:"
    echo "1. Connect to your Cloud SQL instance"
    echo "2. Run these SQL commands:"
    echo "   ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_oauth_id VARCHAR(255) UNIQUE;"
    echo "   CREATE INDEX IF NOT EXISTS ix_users_facebook_oauth_id ON users (facebook_oauth_id);"
  fi
else
  echo -e "\n❌ Fix failed with HTTP status $HTTP_CODE."
  echo "This could mean the debug endpoint isn't available in this environment."

  if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "\nAlternative solution for GCP Cloud SQL:"
    echo "1. Connect to your Cloud SQL instance"
    echo "2. Run these SQL commands:"
    echo "   ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_oauth_id VARCHAR(255) UNIQUE;"
    echo "   CREATE INDEX IF NOT EXISTS ix_users_facebook_oauth_id ON users (facebook_oauth_id);"

    echo -e "\nCommand for connecting to Cloud SQL (adjust instance name):"
    echo "   gcloud sql connect your-instance-name --user=postgres"
  fi
fi

echo -e "\nFor local testing, try: ./fix_facebook_column.sh local"
echo "To deploy changes after fixing, run: gcloud app deploy"

# Verify the subscriptions endpoint works after the fix
if [ "$HTTP_CODE" -eq 200 ]; then
  echo -e "\nVerifying subscriptions endpoint..."
  echo "GET $API_BASE/api/v1/payments/subscriptions"
  TEST_RESPONSE=$(curl -s -w "\n%{http_code}" "$API_BASE/api/v1/payments/subscriptions" -H "Authorization: Bearer YOUR_TEST_TOKEN")
  TEST_CODE=$(echo "$TEST_RESPONSE" | tail -n1)
  echo "Subscriptions endpoint returned HTTP $TEST_CODE"
fi
