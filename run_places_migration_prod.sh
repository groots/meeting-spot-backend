#!/bin/bash
# Script to run the places migration on the production database

# Navigate to the backend directory
cd "$(dirname "$0")"

# Set environment variables for production database
export FLASK_ENV=production

# Check if Cloud SQL proxy is running, if not, start it
if ! pgrep -x "cloud[-_]sql[-_]proxy" > /dev/null; then
    echo "Starting Cloud SQL proxy for production database..."
    INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"

    # Check if the proxy exists
    if [ -f "cloud_sql_proxy" ]; then
        ./cloud_sql_proxy -instances=$INSTANCE_CONNECTION_NAME=tcp:5432 &
        PROXY_PID=$!
        echo "Cloud SQL proxy started with PID: $PROXY_PID"
        # Give the proxy a moment to start
        sleep 3
    elif [ -f "cloud-sql-proxy" ]; then
        ./cloud-sql-proxy -instances=$INSTANCE_CONNECTION_NAME=tcp:5432 &
        PROXY_PID=$!
        echo "Cloud SQL proxy started with PID: $PROXY_PID"
        # Give the proxy a moment to start
        sleep 3
    else
        echo "Cloud SQL proxy not found. Please download it first."
        exit 1
    fi
fi

# Set database connection variables for production
export DB_USER="meetingspot"
export DB_PASS="MeetingSpot123!"
export DB_NAME="findameetingspot"
export DB_HOST="127.0.0.1"
export DB_PORT="5432"
export INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"

# Run the migration script
echo "Running places migration on production database..."
python apply_places_migration.py

# Check if the migration was successful
if [ $? -eq 0 ]; then
    echo "Migration completed successfully!"
else
    echo "Migration failed!"
    exit 1
fi

# If we started the proxy, stop it
if [ -n "$PROXY_PID" ]; then
    echo "Stopping Cloud SQL proxy..."
    kill $PROXY_PID
    echo "Cloud SQL proxy stopped"
fi

echo "Places tables migration process completed!"
