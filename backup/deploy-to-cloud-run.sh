#!/bin/bash

# Exit on error
set -e

# Configuration
PROJECT_ID="find-a-meeting-spot"
SERVICE_NAME="find-a-meeting-spot-backend"
REGION="us-central1"

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME .

# Authenticate with Google Cloud (if needed)
if ! gcloud auth print-access-token &>/dev/null; then
  echo "🔑 Authenticating with Google Cloud..."
  gcloud auth login
fi

# Configure Docker to use gcloud as a credential helper
echo "🔄 Configuring Docker authentication..."
gcloud auth configure-docker

# Push the Docker image to Container Registry
echo "📤 Pushing image to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "NODE_ENV=production"

echo "✅ Deployment completed!"

# Get the deployed service URL
echo "📡 Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)" 