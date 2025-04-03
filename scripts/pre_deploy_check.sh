#!/bin/bash

# Exit on error
set -e

echo "Running pre-deploy checks..."

# 1. Check Python version
echo "Checking Python version..."
python --version

# 2. Check if all required packages are installed
echo "Checking required packages..."
pip install -r requirements.txt

# 3. Check if app.yaml exists and is valid
echo "Checking app.yaml..."
if [ ! -f "app.yaml" ]; then
    echo "❌ Missing app.yaml"
    exit 1
fi

# 4. Check if secret_settings.yaml exists and has required variables
echo "Checking secret_settings.yaml..."
if [ ! -f "secret_settings.yaml" ]; then
    echo "❌ Missing secret_settings.yaml"
    exit 1
fi

# Check if secret_settings.yaml has all required variables
required_vars=(
    "GOOGLE_MAPS_API_KEY"
    "ENCRYPTION_KEY"
    "JWT_SECRET_KEY"
    "MAILGUN_API_KEY"
    "MAILGUN_DOMAIN"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "$var:" secret_settings.yaml; then
        echo "❌ Missing required variable in secret_settings.yaml: $var"
        exit 1
    fi
done

# 5. Run the test script
echo "Running test script..."
./scripts/test_deploy.sh

echo "✅ All pre-deploy checks passed!"
