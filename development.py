import os

from dotenv import load_dotenv

from app import create_app

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Set environment variables for development
    os.environ["FLASK_ENV"] = "development"

    app = create_app("development")
    app.run(host="0.0.0.0", port=8000, debug=True)
