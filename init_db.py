import os

from app import create_app, db

# Set the environment to development
env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

# Create an application context
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created.")
