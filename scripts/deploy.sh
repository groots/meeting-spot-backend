#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting deployment process..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud is not installed. Please install the Google Cloud SDK."
    exit 1
fi

# Check if we're authenticated
if ! gcloud auth print-identity-token &> /dev/null; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Run linting checks
echo "🔍 Running linting checks..."
./scripts/lint.sh

# Set the project
echo "📦 Setting Google Cloud project..."
gcloud config set project find-a-meeting-spot

# Set up secrets if needed
echo "🔑 Setting up secrets..."
python scripts/setup_secrets.py

# Deploy to App Engine
echo "🚀 Deploying to App Engine..."
gcloud app deploy app.yaml

echo "✅ Deployment complete!"
echo "🌐 Your app is now live at: https://find-a-meeting-spot.appspot.com"
