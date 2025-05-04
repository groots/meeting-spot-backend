#!/bin/bash
set -e

# Script to format code while handling special cases
echo "Running code formatting..."

# Create .noformat file to mark test_notifications.py as skipped for black
if [ ! -f "tests/.noformat_test_notifications" ]; then
    echo "Creating marker file for skipping formatting on tests/test_notifications.py"
    echo "# This file marks tests/test_notifications.py to be excluded from Black formatting" > tests/.noformat_test_notifications
    echo "# Created because Black has an internal error when formatting this file" >> tests/.noformat_test_notifications
    echo "# See the docstring in tests/test_notifications.py for more information" >> tests/.noformat_test_notifications
fi

# Format all Python files using black, excluding test_notifications.py
echo "Running black formatter..."
black --exclude "tests/test_notifications.py" .

# Format imports using isort
echo "Running isort formatter..."
isort .

echo "Code formatting complete!"
