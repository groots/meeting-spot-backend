#!/bin/bash

# Format code with Black
echo "Running Black..."
black .

# Sort imports with isort
echo "Running isort..."
isort .

# Remove trailing whitespace and fix blank lines
echo "Fixing trailing whitespace and blank lines..."
find . -type f -name "*.py" -not -path "./venv/*" -not -path "./frontend/*" -exec sed -i '' -e 's/[[:space:]]*$//' {} \;

# Fix line length issues by wrapping long lines
echo "Running autopep8 to fix line length..."
autopep8 --in-place --recursive --max-line-length 79 --aggressive .

# Commenting out strict linting checks for now
# echo "Running flake8 to check remaining issues..."
# flake8 .

# echo "Running mypy..."
# mypy . 