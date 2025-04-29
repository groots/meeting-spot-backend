# Use Python 3.8 slim image
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir alembic retry backoff

# Copy the rest of the application
COPY . .

# Create a migration entrypoint script with GCP support
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Checking database connection..."\n\
# Use retry logic for database connection\n\
max_retries=5\n\
retry_count=0\n\
\n\
# Extract host from connection string or use default if not found\n\
if [ -n "$INSTANCE_CONNECTION_NAME" ]; then\n\
  echo "Using Cloud SQL instance: $INSTANCE_CONNECTION_NAME"\n\
  # Wait for Cloud SQL Proxy to be ready\n\
  sleep 5\n\
else\n\
  echo "Using standard database connection"\n\
fi\n\
\n\
# Run migrations with retry logic\n\
if [ "$RUN_MIGRATIONS" = "true" ]; then\n\
  echo "Running database migrations..."\n\
  # If alembic.ini exists, use it to run migrations\n\
  if [ -f alembic.ini ]; then\n\
    for i in $(seq 1 $max_retries); do\n\
      echo "Migration attempt $i of $max_retries"\n\
      if flask db upgrade; then\n\
        echo "Migrations completed successfully"\n\
        break\n\
      else\n\
        echo "Migration failed. Retrying in 5 seconds..."\n\
        sleep 5\n\
        if [ $i -eq $max_retries ]; then\n\
          echo "Failed to run migrations after $max_retries attempts"\n\
          exit 1\n\
        fi\n\
      fi\n\
    done\n\
  else\n\
    echo "Running custom migration script..."\n\
    python run_migrations.py\n\
  fi\n\
fi\n\
\n\
# Start the application\n\
exec gunicorn --workers 2 --threads 8 --timeout 120 --bind 0.0.0.0:$PORT "$FLASK_APP:create_app()"\n\
' > /app/gcp_entrypoint.sh \
    && chmod +x /app/gcp_entrypoint.sh \
    && chmod +x entrypoint.sh

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production
ENV PORT=8080
ENV RUN_MIGRATIONS=false

# Expose the port the app runs on
EXPOSE 8080

# Use the appropriate entrypoint script
# In GCP environments, use GCP-specific entrypoint
CMD [ "/bin/bash", "-c", "if [ \"$GOOGLE_CLOUD_PROJECT\" != \"\" ] || [ \"$GCP_PROJECT\" != \"\" ]; then /app/gcp_entrypoint.sh; else ./entrypoint.sh; fi" ]
