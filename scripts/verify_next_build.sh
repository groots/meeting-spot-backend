#!/bin/bash

# Exit on error
set -e

echo "Verifying Next.js build..."

# Check if Next.js build exists
if [ ! -d "../frontend/.next" ]; then
    echo "❌ Next.js build directory not found"
    exit 1
fi

# Check for required build files
echo "Checking build files..."
if [ ! -f "../frontend/.next/server/app/index.html" ]; then
    echo "❌ Missing server-side rendered index.html"
    exit 1
fi

if [ ! -d "../frontend/.next/static" ]; then
    echo "❌ Missing Next.js static directory"
    exit 1
fi

# Check for required static directories
if [ ! -d "../frontend/.next/static/chunks" ]; then
    echo "❌ Missing chunks directory"
    exit 1
fi

if [ ! -d "../frontend/.next/static/css" ]; then
    echo "❌ Missing css directory"
    exit 1
fi

# Check public directory
if [ ! -d "../frontend/public" ]; then
    echo "❌ Missing public directory"
    exit 1
fi

echo "✅ Next.js build verification passed!"
