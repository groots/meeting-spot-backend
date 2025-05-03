#!/bin/bash
set -e

# This script sets up and fixes pre-commit hooks

echo "Setting up pre-commit hooks..."

# Make sure pre-commit is installed
pip install pre-commit

# Create a .pre-commit-config.yaml file if it doesn't exist
if [ ! -f .pre-commit-config.yaml ]; then
  cat << EOF > .pre-commit-config.yaml
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files

-   repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
    -   id: isort
        args: ["--profile", "black"]

-   repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
    -   id: black
        exclude: >
            (?x)(
                tests/integration/test_meeting_request_api_flow.py|
                tests/test_notifications.py|
                migrations/.*
            )

-   repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
    -   id: flake8
        additional_dependencies: [flake8-docstrings]
        exclude: ^migrations/
        args: ["--max-line-length=88", "--extend-ignore=E203"]
EOF
  echo "Created .pre-commit-config.yaml"
fi

# Install the pre-commit hooks
pre-commit install

# Add fmt:off directives to problematic files if not already present
for file in "tests/integration/test_meeting_request_api_flow.py" "tests/test_notifications.py"; do
  if [ -f "$file" ] && ! grep -q "# fmt: off" "$file"; then
    sed -i '1s/^/# fmt: off\n/' "$file"
    echo "Added fmt:off directive to $file"
  fi
done

echo "Pre-commit hooks setup complete!"
echo "Run 'pre-commit run --all-files' to fix all existing files"
