#!/bin/bash

# Function to fix line length issues
fix_line_length() {
    local file=$1
    echo "Fixing line length issues in $file..."
    
    # Use autopep8 to fix line length issues
    autopep8 --in-place --max-line-length 100 --aggressive "$file"
}

# Process specific files with line length issues
fix_line_length "app/config.py"
fix_line_length "routes/main.py"

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing line length issues!" 