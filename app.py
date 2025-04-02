from app import create_app
from config import Config

if __name__ == "__main__":
    app = create_app()
    # Consider using 'waitress' or 'gunicorn' for production
    # Also, consider creating tables via a Flask CLI command instead of automatically
    # with app.app_context():
    #     db.create_all() # Be careful with this in production!
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
