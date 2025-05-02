#!/bin/bash
# setup-local-db.sh - Script to set up local database connection via Cloud SQL Proxy
#
# Usage:
#   ./setup-local-db.sh
#
# This script will:
# 1. Download Cloud SQL Proxy if needed
# 2. Start the proxy to connect to your production database
# 3. Set up environment variables for local development
# 4. Keep running until you press Ctrl+C
#
# After running this script, you can run database migrations and
# work with your application locally while connected to the real database.

set -e  # Exit on error

echo "=== Cloud SQL Proxy Setup for Local Development ==="

# Download Cloud SQL Proxy if needed
if [ ! -f cloud_sql_proxy ]; then
  echo "Downloading Cloud SQL Proxy..."

  # Detect OS
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy_darwin_amd64
  else
    # Linux
    curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy_x64.linux
  fi

  chmod +x cloud_sql_proxy
  echo "✅ Cloud SQL Proxy downloaded"
else
  echo "✅ Using existing Cloud SQL Proxy"
fi

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
  echo "⚠️ gcloud command not found. Please install Google Cloud SDK."
  echo "Visit: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# Ensure authenticated to Google Cloud
echo "Checking Google Cloud authentication..."
if ! gcloud auth list 2>&1 | grep -q "ACTIVE"; then
  echo "⚠️ Not authenticated to Google Cloud. Please run 'gcloud auth login'"
  exit 1
fi

# Get project information
PROJECT=$(gcloud config get-value project)
REGION="us-east1"  # Set your region here or make this configurable

if [ -z "$PROJECT" ]; then
  echo "⚠️ No Google Cloud project configured. Please run 'gcloud config set project PROJECT_ID'"
  exit 1
fi

echo "Using Google Cloud Project: $PROJECT"

# Start the proxy
echo "Starting Cloud SQL Proxy..."
INSTANCE_NAME="findameetingspot"  # Change to your instance name
INSTANCE_CONNECTION="${PROJECT}:${REGION}:${INSTANCE_NAME}"

echo "Connecting to Cloud SQL instance: $INSTANCE_CONNECTION"
./cloud_sql_proxy -instances=${INSTANCE_CONNECTION}=tcp:5432 &
PROXY_PID=$!

# Wait for it to start
echo "Waiting for connection..."
sleep 5

# Function to clean up proxy on exit
cleanup() {
  echo -e "\nStopping Cloud SQL Proxy..."
  kill $PROXY_PID
  echo "✅ Connection closed"
}

# Set trap for cleanup
trap cleanup EXIT

# Prompt for database password (avoid storing in scripts)
if [ -z "$DB_PASSWORD" ]; then
  read -s -p "Enter database password: " DB_PASSWORD
  echo
fi

# Export database URL for local development
export DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@localhost:5432/${INSTANCE_NAME}"
export FLASK_APP=app:create_app
export FLASK_ENV=development

echo -e "\n=== Database Connection Ready ==="
echo "DATABASE_URL is set to: postgresql://postgres:****@localhost:5432/${INSTANCE_NAME}"
echo -e "\nYou can now run migrations:"
echo "  python deploy_db_migrations.py"
echo -e "\nOr start your application:"
echo "  flask run"
echo -e "\nPress Ctrl+C to stop the database connection"

# Keep script running until canceled
while true; do sleep 1; done
