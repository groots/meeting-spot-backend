#!/bin/bash
set -e

# Build and deploy the application with our fix
echo "Building and deploying the fixed application..."

# Create a temporary directory for the fix
mkdir -p /tmp/app_fix
cp -r app /tmp/app_fix/
cp requirements.txt /tmp/app_fix/
cp Dockerfile /tmp/app_fix/

# Move to the temporary directory
cd /tmp/app_fix

# Create a minimal Dockerfile
cat > Dockerfile <<EOF
FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:create_app()"]
EOF

# Create the image tag
IMAGE_TAG="gcr.io/find-a-meeting-spot/meeting-spot-backend:fix-$(date +%s)"

# Build the container
echo "Building container image: $IMAGE_TAG"
gcloud builds submit --tag $IMAGE_TAG

# Deploy the service
echo "Updating service with the new image"
gcloud run services update meeting-spot-backend \
  --region=us-east1 \
  --project=find-a-meeting-spot \
  --image=$IMAGE_TAG

echo "Deployment complete!"
