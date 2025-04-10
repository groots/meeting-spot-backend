from setuptools import find_packages, setup

setup(
    name="find_a_meeting_spot",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Flask==2.0.1",
        "Flask-SQLAlchemy==2.5.1",
        "Flask-Migrate==3.1.0",
        "Flask-Cors==3.0.10",
        "Flask-RESTX==1.3.0",
        "Werkzeug==2.0.3",
        "psycopg2-binary==2.9.1",
        "python-dotenv==0.19.0",
        "gunicorn==20.1.0",
        "pytest==6.2.5",
        "black==22.3.0",
        "flake8==5.0.4",
        "mypy==1.7.1",
        "isort==5.12.0",
        "types-requests==2.31.0.20240125",
        "types-Flask==1.1.6",
        "types-Jinja2==2.11.9",
        "types-Werkzeug==1.0.9",
        "types-PyYAML==6.0.12.12",
        "types-PyMySQL==1.0.19.7",
        "types-cryptography==3.3.23.2",
    ],
)
