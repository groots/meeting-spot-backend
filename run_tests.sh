#!/bin/bash
set -e

# Set environment to testing
export FLASK_ENV=testing
export FLASK_DEBUG=1
export FLASK_APP=app
export DATABASE_URL=sqlite:///:memory:
export TESTING=True
export GOOGLE_MAPS_API_KEY=test_key

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
echo "Running unit tests..."
python -m pytest tests/unit -v

echo "Running integration tests..."
python -m pytest tests/integration -v

# Generate coverage report
echo "Generating coverage report..."
python -m pytest --cov=app tests/

echo "All tests completed!"
