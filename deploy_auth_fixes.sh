#!/bin/bash

# Script to deploy authentication fixes to Google Cloud Run

set -e  # Exit on any error

echo "🚀 Deploying authentication fixes to Cloud Run"

# Deploy to Cloud Run (replace with your actual deployment command)
gcloud run deploy your-service-name --source . --region us-central1 --platform managed
