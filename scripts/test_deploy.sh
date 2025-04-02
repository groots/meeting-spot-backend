#!/bin/bash

# Exit on error
set -e

echo "Testing deployment setup..."

# 1. Run Python tests
echo "Running Python tests..."
python -m pytest tests/ -v

# 2. Check if all required files exist
echo "Checking required files..."
if [ ! -f "static/index.html" ]; then
    echo "❌ Missing static/index.html"
    ls -la static/
    exit 1
fi

if [ ! -d "static/_next/static" ]; then
    echo "❌ Missing static/_next/static directory"
    ls -la static/
    exit 1
fi

# 3. Check if Next.js static files are present
echo "Checking Next.js static files..."
if [ ! -d "static/_next/static/chunks" ]; then
    echo "❌ Missing Next.js chunks directory"
    ls -la static/_next/static/
    exit 1
fi

if [ ! -d "static/_next/static/css" ]; then
    echo "❌ Missing Next.js css directory"
    ls -la static/_next/static/
    exit 1
fi

# 4. Check if public files are present
echo "Checking public files..."
if [ ! -f "static/globe.svg" ]; then
    echo "❌ Missing public files"
    ls -la static/
    exit 1
fi

# 5. Test Flask app locally
echo "Testing Flask app..."
export FLASK_APP=wsgi.py
export FLASK_ENV=development
export DATABASE_URL="postgresql+pg8000:///findameetingspot?host=/cloudsql/find-a-meeting-spot:us-east1:findameetingspot"

# Start Flask in background with debug output
echo "Starting Flask server..."
flask run --port=5000 --debug &
FLASK_PID=$!

# Wait for Flask to start
echo "Waiting for Flask server to start..."
sleep 2

# Test endpoints with verbose output
echo "Testing endpoints..."
echo "Testing root endpoint..."
response=$(curl -v http://localhost:5000/ 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Root endpoint failed"
    echo "Response:"
    echo "$response"
    kill $FLASK_PID
    exit 1
fi

echo "Testing static files..."
response=$(curl -v http://localhost:5000/_next/static/css/app.css 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Next.js static files not accessible"
    echo "Response:"
    echo "$response"
    kill $FLASK_PID
    exit 1
fi

# 6. Test API endpoints
echo "Testing API endpoints..."
response=$(curl -v http://localhost:5000/hello 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Hello endpoint failed"
    echo "Response:"
    echo "$response"
    kill $FLASK_PID
    exit 1
fi

# Cleanup
kill $FLASK_PID

echo "✅ All tests passed!" 