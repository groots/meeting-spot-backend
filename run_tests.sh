#!/bin/bash
# Script to run tests with proper environment variables

# Set test environment variables
export FLASK_ENV=testing
export FLASK_APP=run.py
export SQLALCHEMY_DATABASE_URI=sqlite:///:memory:
export ENCRYPTION_KEY=test-encryption-key-for-testing-only
export JWT_SECRET_KEY=test-jwt-secret-key-for-testing-only
export GOOGLE_MAPS_API_KEY=test-maps-api-key

# Run the tests
if [ $# -eq 0 ]; then
  # If no arguments provided, run all tests
  pytest
else
  # Run with provided arguments
  pytest "$@"
fi
