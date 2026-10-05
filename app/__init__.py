"""
Application factory.

Using the factory pattern (`create_app()`) instead of a single global
`app = Flask(__name__)` keeps configuration explicit and testable, and
avoids circular imports between blueprints and extensions.
"""

import logging
import os


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
    """Configure application logging.

    Vercel uses a read-only deployment filesystem, so logs are
    written to stdout/stderr instead of a local file.
    """
    if app.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    app.logger.setLevel(log_level)

    # Vercel/serverless environments should log to stdout.
    if not app.logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        stream_handler.setFormatter(formatter)

        app.logger.addHandler(stream_handler)
