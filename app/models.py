"""
Database models.

Using SQLAlchemy's ORM (rather than hand-written SQL strings) means every
query is automatically parameterized, which is the primary defense against
SQL injection. Passwords are never stored in plain text -- only a bcrypt
hash is persisted.
"""

from datetime import datetime
import json

from flask_login import UserMixin

from app.extensions import db, bcrypt


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active_account = db.Column("is_active", db.Boolean, nullable=False, default=True)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    plans = db.relationship(
        "PlanHistory", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    progress_logs = db.relationship(
        "ProgressLog", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    # --- Password helpers -------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(raw_password).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw_password)

    # Flask-Login expects `is_active` -- expose the renamed column under that name.
    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<User {self.email}>"


class PlanHistory(db.Model):
    """Stores every fitness/nutrition plan a logged-in user generates."""

    __tablename__ = "plan_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Inputs the user supplied
    goal = db.Column(db.String(50))
    activity_level = db.Column(db.String(50))
    targeted_muscle = db.Column(db.String(50))
    difficulty = db.Column(db.Integer)
    num_weeks = db.Column(db.Integer)
    diet_type = db.Column(db.String(50))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)

    # Computed results
    daily_calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)

    # Full generated plan, stored as JSON text so it can be redisplayed later.
    plan_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def get_plan(self):
        return json.loads(self.plan_json) if self.plan_json else []

    def set_plan(self, plan_data):
        self.plan_json = json.dumps(plan_data)

class ProgressLog(db.Model):
    """A weekly check-in: body weight plus how many workouts were completed."""

    __tablename__ = "progress_logs"
    __table_args__ = (db.UniqueConstraint("user_id", "log_date", name="uq_progress_user_date"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    workouts_done = db.Column(db.Integer, nullable=False, default=0)  # workouts completed that week
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
