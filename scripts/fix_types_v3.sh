#!/bin/bash

# Function to fix double return type annotations
fix_double_return_types() {
    local file=$1
    echo "Fixing double return type annotations in $file..."

    # Fix functions with double return type annotations
    sed -i '' 's/\(def [^(]*([^)]*)\) -> None -> None:/\1 -> None:/g' "$file"
    sed -i '' 's/\(def [^(]*([^)]*)\) -> Any -> None:/\1 -> None:/g' "$file"
    sed -i '' 's/\(def [^(]*([^)]*)\) -> None -> Any:/\1 -> Any:/g' "$file"
    sed -i '' 's/\(def [^(]*([^)]*)\) -> Any -> Any:/\1 -> Any:/g' "$file"
}

# Process each Python file
for file in $(find . -name "*.py"); do
    if [[ ! "$file" =~ "migrations" ]]; then
        fix_double_return_types "$file"
    fi
done

# Run Black to ensure consistent formatting
echo "Running Black for consistent formatting..."
black .

# Run isort to sort imports
echo "Running isort..."
isort .

echo "Done fixing type annotations!"
