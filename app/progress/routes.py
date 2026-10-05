"""
Progress tracking: weekly check-ins (weight + workouts), charts, and an
adaptive recommendation that can be applied as a fresh plan.
"""

import logging
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import PlanHistory, ProgressLog
from app.progress import coach
from app.recommender.engine import get_engine, calculate_macros

logger = logging.getLogger(__name__)
progress_bp = Blueprint("progress", __name__, url_prefix="/progress")


# ---------------------------------------------------------------- helpers
def _latest_plan():
    return (
        PlanHistory.query.filter_by(user_id=current_user.id)
        .order_by(PlanHistory.created_at.desc())
        .first()
    )


def _user_entries():
    """All of the user's check-ins, oldest first."""
    return (
        ProgressLog.query.filter_by(user_id=current_user.id)
        .order_by(ProgressLog.log_date.asc())
        .all()
    )


def _recommendation(plan, entries):
    """Build the adaptive recommendation from the latest plan + check-ins made
    since that plan was created (so a freshly applied plan starts clean)."""
    if not plan or not plan.daily_calories:
        return None
    plan_day = plan.created_at.date()
    since = [e for e in entries if e.log_date >= plan_day]

    points = {}
    if plan.weight_kg:
        points[plan_day] = float(plan.weight_kg)      # weight when the plan was made
    for e in since:
        points[e.log_date] = float(e.weight_kg)       # check-ins override same-day plan weight

    return coach.recommend(
        goal=plan.goal,
        gender=plan.gender,
        current_calories=float(plan.daily_calories),
        difficulty=int(plan.difficulty or 3),
        weight_points=sorted(points.items()),
        workout_counts=[e.workouts_done for e in since],
    )


# ----------------------------------------------------------------- routes
@progress_bp.route("/")
@login_required
def index():
    entries = _user_entries()
    plan = _latest_plan()
    reco = _recommendation(plan, entries)
    today = date.today()

    start_weight = entries[0].weight_kg if entries else (plan.weight_kg if plan else None)
    current_weight = entries[-1].weight_kg if entries else (plan.weight_kg if plan else None)
    change = (current_weight - start_weight) if (start_weight and current_weight and entries) else None

    recent_week = [e for e in entries if (today - e.log_date).days < 7]
    this_week = recent_week[-1].workouts_done if recent_week else None

    chart = {
        "weight_labels": [e.log_date.strftime("%d %b") for e in entries],
        "weight_values": [round(e.weight_kg, 1) for e in entries],
        "workout_values": [e.workouts_done for e in entries],
        "workout_target": coach.WORKOUT_DAYS_TARGET,
    }

    new_macros = None
    if reco and reco["status"] == "adjust":
        p, c, f = calculate_macros(reco["new_calories"])
        new_macros = {"protein": p, "carbs": c, "fats": f}

    return render_template(
        "progress.html",
        entries=list(reversed(entries)),
        has_entries=bool(entries),
        plan=plan,
        reco=reco,
        new_macros=new_macros,
        current_weight=current_weight,
        change=change,
        streak=coach.streak([e.workouts_done for e in entries]),
        this_week=this_week,
        workout_target=coach.WORKOUT_DAYS_TARGET,
        chart=chart,
        today=today.isoformat(),
    )


@progress_bp.route("/log", methods=["POST"])
@login_required
def log():
    errors = []
    try:
        log_date = datetime.strptime(request.form.get("log_date", ""), "%Y-%m-%d").date()
        if log_date > date.today():
            errors.append("The check-in date can't be in the future.")
        elif log_date < date.today() - timedelta(days=730):
            errors.append("The check-in date is too far in the past.")
    except ValueError:
        errors.append("Please enter a valid date.")
        log_date = None

    try:
        weight = float(request.form.get("weight", ""))
        if not (20 <= weight <= 400):
            errors.append("Weight must be between 20 and 400 kg.")
    except ValueError:
        errors.append("Weight must be a valid number.")
        weight = None

    try:
        workouts = int(request.form.get("workouts", ""))
        if not (0 <= workouts <= 7):
            errors.append("Workouts must be between 0 and 7.")
    except ValueError:
        errors.append("Workouts must be a whole number.")
        workouts = None

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("progress.index"))

    existing = ProgressLog.query.filter_by(user_id=current_user.id, log_date=log_date).first()
    if existing:                      # one check-in per day: update it
        existing.weight_kg = round(weight, 1)
        existing.workouts_done = workouts
        flash("Check-in updated.", "success")
    else:
        db.session.add(ProgressLog(
            user_id=current_user.id, log_date=log_date,
            weight_kg=round(weight, 1), workouts_done=workouts,
        ))
        flash("Check-in saved.", "success")
    db.session.commit()
    logger.info("Progress check-in saved for user=%s date=%s", current_user.email, log_date)
    return redirect(url_for("progress.index"))


@progress_bp.route("/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    entry = ProgressLog.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Check-in removed.", "success")
    return redirect(url_for("progress.index"))


@progress_bp.route("/apply", methods=["POST"])
@login_required
def apply():
    """Turn the current recommendation into a brand-new saved plan.

    The numbers are recomputed here on the server (never taken from the
    browser), and the old plan stays in History."""
    plan = _latest_plan()
    entries = _user_entries()
    reco = _recommendation(plan, entries)
    if not plan or not reco or reco["status"] != "adjust":
        flash("There's nothing to apply right now.", "warning")
        return redirect(url_for("progress.index"))

    protein, carbs, fats = calculate_macros(reco["new_calories"])
    latest_weight = entries[-1].weight_kg if entries else plan.weight_kg

    full_plan = get_engine().build_full_plan(
        targeted_muscle=plan.targeted_muscle,
        difficulty=reco["new_difficulty"],
        num_weeks=plan.num_weeks,
        diet_type=plan.diet_type,
    )
    record = PlanHistory(
        user_id=current_user.id,
        goal=plan.goal,
        activity_level=plan.activity_level,
        targeted_muscle=plan.targeted_muscle,
        difficulty=reco["new_difficulty"],
        num_weeks=plan.num_weeks,
        diet_type=plan.diet_type,
        age=plan.age,
        gender=plan.gender,
        height_cm=plan.height_cm,
        weight_kg=latest_weight,
        daily_calories=float(reco["new_calories"]),
        protein=protein,
        carbs=carbs,
        fats=fats,
    )
    record.set_plan(full_plan)
    db.session.add(record)
    db.session.commit()
    logger.info("Adaptive plan applied id=%s user=%s kcal=%s diff=%s",
                record.id, current_user.email, reco["new_calories"], reco["new_difficulty"])
    flash("Your plan was updated. The previous plan is still in your History.", "success")
    return redirect(url_for("main.history_detail", plan_id=record.id))
