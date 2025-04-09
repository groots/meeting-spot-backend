import os

from dotenv import load_dotenv
from flask import Flask

from app import create_app
from development_config import DevelopmentConfig

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Set environment variables for development
    os.environ["FLASK_ENV"] = "development"
    os.environ["FLASK_DEBUG"] = "True"

    # Set encryption key if not already set
    if "ENCRYPTION_KEY" not in os.environ:
        os.environ["ENCRYPTION_KEY"] = "lpCxwLkoWlix-nm4VtLRkbtuy_Yx9pb5mhZjYvJuRGA="

    # Use port from environment or default to 8000
    port = int(os.environ.get("PORT", 8000))

    # Create the app with development config
    app = create_app("development")

    # Run the app
    app.run(host="0.0.0.0", port=port, debug=True)
