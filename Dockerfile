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

# Expose port
ENV PORT=8080
EXPOSE 8080

# Start the application
CMD exec gunicorn --bind :$PORT wsgi:app 