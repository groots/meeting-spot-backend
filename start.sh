#!/bin/bash
# Script to set required environment variables and run the application

# Set the encryption key if not already set
if [ -z "$ENCRYPTION_KEY" ]; then
    export ENCRYPTION_KEY="wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA"
    echo "ENCRYPTION_KEY environment variable set from script"
else
    echo "ENCRYPTION_KEY already set in environment"
fi

# Check if the .env file exists and ENCRYPTION_KEY is in it
if [ -f .env ]; then
    if ! grep -q "ENCRYPTION_KEY" .env; then
        echo "Adding ENCRYPTION_KEY to .env file"
        echo "ENCRYPTION_KEY=wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA" >> .env
    else
        echo "ENCRYPTION_KEY already in .env file"
    fi
else
    echo "Creating .env file with ENCRYPTION_KEY"
    echo "ENCRYPTION_KEY=wx3XysUzuC2Um5gRWIiqqxsG1iy62F8T9f_WQoLlquA" > .env
fi

# Run the application with gunicorn
echo "Starting application with encryption key configured"
python development.py
