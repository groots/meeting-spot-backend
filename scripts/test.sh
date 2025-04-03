#!/bin/bash

# Exit on error
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# Change to the backend directory
cd "$BACKEND_DIR"

# Add the current directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

echo "🧪 Running tests from $(pwd)..."
echo "PYTHONPATH: $PYTHONPATH"

# Run pytest with coverage
pytest --cov=app --cov-report=term-missing tests/

echo "✅ Tests completed!"
