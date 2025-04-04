#!/bin/bash

# Exit on error
set -e

echo "Testing dependencies..."

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install black==22.3.0 isort flake8==5.0.4 flake8-docstrings==1.7.0 pytest pytest-cov cryptography sqlalchemy flask-sqlalchemy psycopg2-binary flask-cors

# Try importing all required modules
echo "Testing imports..."
python -c "
import black
import isort
import flake8
import pytest
import cryptography
import sqlalchemy
import flask_sqlalchemy
import psycopg2
import flask_cors
print('All imports successful!')
"

# Run tests
echo "Running tests..."
pytest --cov=app tests/ -v

echo "All tests passed!" 