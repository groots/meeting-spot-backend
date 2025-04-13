FROM python:3.8-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app
COPY utils /app/utils

# Create a simple app.py to initialize the app
RUN echo 'from app import create_app\n\napp = create_app()' > app.py

# Command to run the server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"] 