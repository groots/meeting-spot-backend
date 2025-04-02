#!/bin/bash

# Function to fix class definitions
fix_class_definitions() {
    local file=$1
    echo "Fixing class definitions in $file..."
    
    # Remove return type annotations from class definitions
    sed -i '' 's/class \([^(]*\)(\([^)]*\)) -> None:/class \1(\2):/g' "$file"
}

# Function to fix if statements
fix_if_statements() {
    local file=$1
    echo "Fixing if statements in $file..."
    
    # Remove return type annotations from if statements
    sed -i '' 's/if \([^:]*\) -> None:/if \1:/g' "$file"
}

# Function to add return type annotations
add_return_types() {
    local file=$1
    echo "Adding return type annotations to $file..."
    
    # Add return type annotations to functions that don't have them
    sed -i '' '/^def [^:]*:$/s/:/ -> None:/' "$file"
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
        fix_class_definitions "$file"
        fix_if_statements "$file"
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