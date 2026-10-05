"""
Application configuration.

All secrets and environment-specific values are read from environment
variables (loaded from a local .env file via python-dotenv). Nothing
sensitive is hard-coded, so the same code can move between dev/staging/
production just by changing the .env file.
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load variables from a .env file sitting next to the project root, if present.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    FLASK_ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = FLASK_ENV == "development"

    # --- Database (MySQL) ---
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "fitness_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # avoids "MySQL server has gone away" errors
        "pool_recycle": 280,
    }

    # --- Sessions / cookies ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only force HTTPS-only cookies outside local development.
    SESSION_COOKIE_SECURE = FLASK_ENV != "development"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 hours

    # --- WTForms / CSRF ---
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # --- App-specific ---
    APP_PORT = int(os.environ.get("APP_PORT", 5001))
