# Find a Meeting Spot Backend

This is the backend service for the Find a Meeting Spot application.

## Development

To run the application locally:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export FLASK_APP=wsgi.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export DATABASE_URL="postgresql+psycopg2://postgres:password@localhost:5433/findameetingspot_dev"
```

3. Run the application:
```bash
flask run
```

## Deployment

The application is deployed using GitHub Actions and Google Cloud Run.

# Test deployment change - can be removed after verification 