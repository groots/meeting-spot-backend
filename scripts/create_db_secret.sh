#!/bin/bash

# This script adds the database URL to Google Cloud Secret Manager
# Make sure you're authenticated with gcloud before running this script

# Replace these values with your actual database credentials
DB_USER="postgres"
DB_PASS="your-database-password"  # Replace with the actual password
INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"
DB_NAME="findameetingspot"

# Build the connection string
DB_CONNECTION_STRING="postgresql+pg8000://${DB_USER}:${DB_PASS}@/findameetingspot?unix_sock=/cloudsql/${INSTANCE_CONNECTION_NAME}/.s.PGSQL.5432"

# Echo masked connection string (for verification)
MASKED_CONNECTION_STRING="postgresql+pg8000://${DB_USER}:***@/findameetingspot?unix_sock=/cloudsql/${INSTANCE_CONNECTION_NAME}/.s.PGSQL.5432"
echo "Creating secret with connection string: $MASKED_CONNECTION_STRING"

# Create the secret
echo "Creating/updating database-url secret..."
echo -n "$DB_CONNECTION_STRING" | gcloud secrets create database-url --data-file=- --replication-policy="automatic" || \
echo -n "$DB_CONNECTION_STRING" | gcloud secrets versions add database-url --data-file=-

# Grant the Cloud Run service account access to the secret
echo "Granting service account access to the secret..."
SERVICE_ACCOUNT="$(gcloud run services describe meeting-spot-backend --region us-east1 --format='value(serviceAccountEmail)')"

gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

echo "Done! The database-url secret is now available to the Cloud Run service."
