#!/bin/bash

# Exit on error
set -e

# Set variables
PROJECT_ID="find-a-meeting-spot"
SERVICE_NAME="find-a-meeting-spot-backend"
REGION="us-central1"
MAX_INSTANCES=5
MIN_INSTANCES=1
MEMORY="512Mi"
CPU="1"
CONCURRENCY=80
TIMEOUT="300s"

# Build the Docker image
echo "Building Docker image..."
docker build -t "gcr.io/$PROJECT_ID/$SERVICE_NAME" .

# Push the image to Google Container Registry
echo "Pushing image to Container Registry..."
docker push "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances "$MAX_INSTANCES" \
  --min-instances "$MIN_INSTANCES" \
  --memory "$MEMORY" \
  --cpu "$CPU" \
  --concurrency "$CONCURRENCY" \
  --timeout "$TIMEOUT" \
  --set-env-vars "NODE_ENV=production"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$REGION" --format 'value(status.url)')

echo "Deployment successful! Service URL: $SERVICE_URL" 