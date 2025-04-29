#!/bin/bash
set -e

echo "Building and deploying DB verification endpoint to Cloud Run"

# Set variables
PROJECT_ID="find-a-meeting-spot"
SERVICE_NAME="db-schema-verifier"
REGION="us-east1"
INSTANCE_CONNECTION_NAME="find-a-meeting-spot:us-east1:findameetingspot"

# Generate a unique build ID
BUILD_ID=$(date +%Y%m%d%H%M%S)

# Create a temporary Dockerfile for the verification service
cat > Dockerfile.verify << EOL
FROM python:3.8-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only what we need
COPY requirements.txt .
COPY verify_db_schema.py .
COPY verify_db_endpoint.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir sqlalchemy flask

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the verification endpoint
CMD ["python", "verify_db_endpoint.py"]
EOL

# Create a temporary cloudbuild.yaml
cat > cloudbuild.verify.yaml << EOL
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/$SERVICE_NAME:$BUILD_ID', '-f', 'Dockerfile.verify', '.']
images:
- 'gcr.io/$PROJECT_ID/$SERVICE_NAME:$BUILD_ID'
EOL

# Build the container
echo "Submitting build to Cloud Build..."
gcloud builds submit --config cloudbuild.verify.yaml

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$BUILD_ID \
  --platform managed \
  --region $REGION \
  --project=$PROJECT_ID \
  --no-allow-unauthenticated \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars="INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME"

# Generate a token and test the endpoint
echo "Getting URL and testing the endpoint..."
URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

echo "Service URL: $URL"
echo "Testing the endpoint..."
curl -H "Authorization: Bearer $TOKEN" $URL

# Cleanup
rm Dockerfile.verify
rm cloudbuild.verify.yaml

echo "Deployment completed successfully!"
echo "You can check the endpoint at: $URL"
echo "Use the following command to get results:"
echo "curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $URL"
