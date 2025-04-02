#!/bin/bash

# Function to fix line length in a file
fix_line_length() {
    local file=$1
    echo "Fixing line length issues in $file..."
    # Use more aggressive settings with autopep8
    autopep8 --in-place --max-line-length 100 --aggressive --aggressive "$file"
}

# Fix line length issues in specific files
fix_line_length "app/config.py"
fix_line_length "routes/main.py"

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing line length issues!" 