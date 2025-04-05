# Use Python 3.8 slim image
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Set environment variables
ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production
ENV PORT=8080

# Expose the port the app runs on
EXPOSE 8080

# Use the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
