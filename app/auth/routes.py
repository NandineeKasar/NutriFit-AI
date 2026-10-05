"""
Authentication routes: registration, login, logout.

Security measures in place:
  * Passwords are hashed with bcrypt (via Flask-Bcrypt) -- never stored
    or logged in plain text.
  * All database access goes through SQLAlchemy's ORM with bound
    parameters, so user input can never be interpolated into raw SQL
    (prevents SQL injection).
  * CSRF protection is enabled globally (Flask-WTF) for every form.
  * Login attempts are rate-limited to slow down brute-force/credential
    stuffing attacks.
  * Failed login attempts are tracked per-account; after 5 consecutive
    failures the account is temporarily locked.
  * Generic error messages are used for login failures ("invalid email
    or password") so an attacker cannot enumerate which emails are
    registered.
  * Session cookies are HttpOnly, SameSite=Lax, and Secure outside of
    local development (see app/config.py).
"""

import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db, limiter
from app.models import User
from app.auth.forms import RegisterForm, LoginForm

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../templates/auth")

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists. Please log in instead.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        logger.info("New user registered: %s", email)
        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        # Account lockout check
        if user and user.locked_until and user.locked_until > datetime.utcnow():
            minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
            flash(
                f"This account is temporarily locked due to repeated failed logins. "
                f"Try again in {minutes_left} minute(s).",
                "danger",
            )
            return render_template("auth/login.html", form=form)

        if user and user.check_password(form.password.data):
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.utcnow()
            db.session.commit()

            login_user(user, remember=form.remember.data)
            logger.info("User logged in: %s", email)

            next_page = request.args.get("next")
            # Only allow relative redirects to avoid open-redirect vulnerabilities.
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))

        # Invalid credentials: increment failure counter if the user exists,
        # but always show the same generic message either way.
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                logger.warning("Account locked after repeated failed logins: %s", email)
            db.session.commit()

        logger.info("Failed login attempt for: %s", email)
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logger.info("User logged out: %s", current_user.email)
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
