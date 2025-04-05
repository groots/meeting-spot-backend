#!/bin/bash

# Run database migrations
flask db upgrade

# Start the application
exec gunicorn --bind 0.0.0.0:8080 wsgi:app 