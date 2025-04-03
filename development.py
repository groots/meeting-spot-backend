import os
from app import create_app

if __name__ == "__main__":
    # Set environment variables for development
    os.environ["FLASK_ENV"] = "development"
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg2://postgres:ggSO12ro9u5N1VxANoQOlyGDuOzsHyv3Su7t9LO9IiQ@"
        "localhost:5433/findameetingspot_dev"
    )

    app = create_app("development")
    app.run(host="0.0.0.0", port=8000, debug=True)
