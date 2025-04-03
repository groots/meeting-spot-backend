#!/bin/bash

# Function to fix unused imports
fix_unused_imports() {
    local file=$1
    echo "Fixing unused imports in $file..."

    # Remove unused typing imports
    sed -i '' '/^from typing import Any, Optional, List, Dict, Union$/d' "$file"
}

# Process each Python file
for file in $(find . -name "*.py"); do
    if [[ ! "$file" =~ "migrations" ]]; then
        fix_unused_imports "$file"
    fi
done

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing imports!"
