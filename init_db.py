"""Initialize the database for development."""
from app import create_app, db


def init_db():
    """Initialize the database tables."""
    app = create_app("development")
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
