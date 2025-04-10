#!/bin/bash

# Function to add return type annotations
add_return_types() {
    local file=$1
    echo "Adding return type annotations to $file..."

    # Add return type annotations to functions
    sed -i '' 's/def \([^(]*\)(\([^)]*\)):/def \1(\2) -> None:/g' "$file"
    sed -i '' 's/def \([^(]*\)(\([^)]*\)):/def \1(\2) -> Any:/g' "$file"

    # Add type annotations to function parameters
    sed -i '' 's/(\([^)]*\)):/(\1) -> None:/g' "$file"
    sed -i '' 's/(\([^)]*\)):/(\1) -> Any:/g' "$file"
}

# Add imports for typing
add_typing_imports() {
    local file=$1
    echo "Adding typing imports to $file..."

    # Add typing imports if they don't exist
    if ! grep -q "from typing import" "$file"; then
        sed -i '' '1i\
from typing import Any, Optional, List, Dict, Union\
' "$file"
    fi
}

# Process each Python file
for file in $(find . -name "*.py"); do
    if [[ ! "$file" =~ "migrations" ]]; then
        add_typing_imports "$file"
        add_return_types "$file"
    fi
done

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing type annotations!"
