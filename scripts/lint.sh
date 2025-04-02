#!/bin/bash

echo "Running Black..."
black --check .

echo "Running isort..."
isort --check-only .

echo "Running Flake8..."
flake8 .

echo "Running mypy..."
mypy .

echo "Running pytest..."
pytest

# If any of the above commands fail, the script will exit with a non-zero status 