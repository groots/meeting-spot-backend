#!/bin/bash

# Install autoflake if not already installed
pip install autoflake

# Remove unused imports
echo "Removing unused imports..."
autoflake --in-place --remove-all-unused-imports --recursive .

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing imports!"
