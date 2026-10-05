"""
Application factory.

Using the factory pattern (`create_app()`) instead of a single global
`app = Flask(__name__)` keeps configuration explicit and testable, and
avoids circular imports between blueprints and extensions.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template

from app.config import Config
from app.extensions import db, bcrypt, login_manager, csrf, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    _configure_logging(app)

    # --- Init extensions ---
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # --- Register blueprints ---
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.admin.routes import admin_bp
    from app.progress.routes import progress_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(progress_bp)
    


    # --- User loader for Flask-Login ---
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Error handlers ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error: %s", e)
        return render_template("errors/500.html"), 500

    # --- Create tables automatically on first run (in addition to schema.sql) ---
    with app.app_context():
        db.create_all()

    app.logger.info("Application startup complete (env=%s)", app.config.get("FLASK_ENV"))
    return app


def _configure_logging(app):
    """Configure a rotating file logger plus console output, so operational
    events (logins, registrations, errors, plan generations) are recorded
    without ever writing sensitive data like passwords."""

    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)
