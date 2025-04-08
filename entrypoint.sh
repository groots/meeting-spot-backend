#!/bin/bash
set -e

echo "Starting application..."

# Check if INSTANCE_CONNECTION_NAME is provided (for Cloud Run with Cloud SQL)
if [ -n "$INSTANCE_CONNECTION_NAME" ]; then
  echo "Using Cloud SQL Proxy..."
  # The Cloud SQL Proxy is automatically used by Cloud Run when properly configured
  # We don't need to run it manually anymore
fi

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  flask db upgrade
fi

# Start the application with gunicorn
echo "Starting gunicorn server..."
exec gunicorn --bind 0.0.0.0:$PORT wsgi:app --workers 2 --threads 8 --timeout 60
