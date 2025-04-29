#!/bin/bash
# Script to deploy the places migration endpoint to Cloud Run

# Set project ID
PROJECT_ID="find-a-meeting-spot"
SERVICE_NAME="places-migration-tool"
REGION="us-east1"

# Navigate to the backend directory
cd "$(dirname "$0")"

# Build the Docker image
echo "Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME --project $PROJECT_ID

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars="FLASK_ENV=production,RUN_MIGRATIONS=false,INSTANCE_CONNECTION_NAME=find-a-meeting-spot:us-east1:findameetingspot" \
  --add-cloudsql-instances="find-a-meeting-spot:us-east1:findameetingspot"

echo "Deployment complete!"
echo "You can access the migration tool at the URL provided above."
