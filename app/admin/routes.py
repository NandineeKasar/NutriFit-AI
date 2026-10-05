"""
Optional admin panel: lets an admin user view all registered users and
promote/demote/deactivate accounts. Every route requires both a logged-in
session AND `is_admin=True` on the account.
"""

import logging
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, PlanHistory

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    plan_counts = dict(
        db.session.query(PlanHistory.user_id, db.func.count(PlanHistory.id))
        .group_by(PlanHistory.user_id)
        .all()
    )
    return render_template("admin/users.html", users=all_users, plan_counts=plan_counts)


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        flash("You cannot change your own admin status.", "warning")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    logger.info("Admin %s toggled admin flag for user %s -> %s", current_user.email, user.email, user.is_admin)
    flash(f"Updated admin status for {user.email}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.users"))

    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    db.session.commit()
    logger.info(
        "Admin %s toggled active flag for user %s -> %s",
        current_user.email, user.email, user.is_active_account,
    )
    flash(f"Updated active status for {user.email}.", "success")
    return redirect(url_for("admin.users"))
