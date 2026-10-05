"""
Core application routes: the landing/form page, plan generation, the
user dashboard, and plan history.
"""

import logging

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import PlanHistory
from app.recommender.guide import get_exercise_guide
from app.recommender.engine import (
    get_engine,
    calculate_bmr,
    calculate_daily_calories,
    calculate_macros,
    VALID_GOALS,
    VALID_GENDERS,
    VALID_DIET_TYPES,
    VALID_MUSCLES,
    ACTIVITY_LEVEL_MAPPING,
)

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


@main_bp.app_context_processor
def inject_exercise_guide():
    """Make the exercise demo data (video link, steps, photos) available to
    every template as `exercise_guide`."""
    return {"exercise_guide": get_exercise_guide()}


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/predict", methods=["POST"])
def predict():
    """Validate the submitted form, generate a plan, and (if the user is
    logged in) persist it to their history."""

    errors = []

    def get_str(field):
        return (request.form.get(field) or "").strip()

    name = get_str("name")
    goal = get_str("goal").lower()
    activity_level_str = get_str("activity_level").lower()
    targeted_muscle = get_str("targeted_muscle").lower()
    diet_type = get_str("diet_type").lower()
    gender = get_str("gender").lower()

    if not name:
        errors.append("Name is required.")

    try:
        height_cm = float(request.form.get("height", ""))
        if not (50 <= height_cm <= 272):
            errors.append("Height must be between 50 and 272 cm.")
    except ValueError:
        errors.append("Height must be a valid number.")
        height_cm = None

    try:
        weight_kg = float(request.form.get("weight", ""))
        if not (20 <= weight_kg <= 400):
            errors.append("Weight must be between 20 and 400 kg.")
    except ValueError:
        errors.append("Weight must be a valid number.")
        weight_kg = None

    try:
        age = int(request.form.get("age", ""))
        if not (10 <= age <= 100):
            errors.append("Age must be between 10 and 100.")
    except ValueError:
        errors.append("Age must be a valid whole number.")
        age = None

    try:
        difficulty = int(request.form.get("difficulty", ""))
        if not (1 <= difficulty <= 5):
            errors.append("Difficulty must be between 1 and 5.")
    except ValueError:
        errors.append("Difficulty must be a valid whole number.")
        difficulty = None

    try:
        num_weeks = int(request.form.get("num_weeks", ""))
        if not (1 <= num_weeks <= 12):
            errors.append("Number of weeks must be between 1 and 12.")
    except ValueError:
        errors.append("Number of weeks must be a valid whole number.")
        num_weeks = None

    if gender not in VALID_GENDERS:
        errors.append("Please select a valid gender.")
    if goal not in VALID_GOALS:
        errors.append("Please select a valid goal.")
    if targeted_muscle not in VALID_MUSCLES:
        errors.append("Please select a valid targeted muscle group.")
    if diet_type not in VALID_DIET_TYPES:
        errors.append("Please select a valid diet type.")
    if activity_level_str not in ACTIVITY_LEVEL_MAPPING:
        errors.append("Please select a valid activity level.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("main.index"))

    engine = get_engine()

    bmr = calculate_bmr(weight_kg=weight_kg, height_cm=height_cm, age=age, gender=gender)
    daily_calories = calculate_daily_calories(bmr, activity_level_str, goal)
    protein, carbs, fats = calculate_macros(daily_calories)

    full_plan = engine.build_full_plan(
        targeted_muscle=targeted_muscle,
        difficulty=difficulty,
        num_weeks=num_weeks,
        diet_type=diet_type,
    )

    # Save to history only for logged-in users.
    if current_user.is_authenticated:
        record = PlanHistory(
            user_id=current_user.id,
            goal=goal,
            activity_level=activity_level_str,
            targeted_muscle=targeted_muscle,
            difficulty=difficulty,
            num_weeks=num_weeks,
            diet_type=diet_type,
            age=age,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            daily_calories=round(daily_calories, 2),
            protein=protein,
            carbs=carbs,
            fats=fats,
        )
        record.set_plan(full_plan)
        db.session.add(record)
        db.session.commit()
        logger.info("Saved plan history id=%s for user=%s", record.id, current_user.email)

    return render_template(
        "result.html",
        name=name,
        daily_calories=round(daily_calories, 2),
        protein=protein,
        carbs=carbs,
        fats=fats,
        plan=full_plan,
        saved=current_user.is_authenticated,
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    recent_plans = (
        PlanHistory.query.filter_by(user_id=current_user.id)
        .order_by(PlanHistory.created_at.desc())
        .limit(5)
        .all()
    )
    total_plans = PlanHistory.query.filter_by(user_id=current_user.id).count()
    return render_template("dashboard.html", recent_plans=recent_plans, total_plans=total_plans)


@main_bp.route("/history")
@login_required
def history():
    plans = (
        PlanHistory.query.filter_by(user_id=current_user.id)
        .order_by(PlanHistory.created_at.desc())
        .all()
    )
    return render_template("history.html", plans=plans)


@main_bp.route("/history/<int:plan_id>")
@login_required
def history_detail(plan_id):
    record = PlanHistory.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    return render_template(
        "result.html",
        name=current_user.name,
        daily_calories=record.daily_calories,
        protein=record.protein,
        carbs=record.carbs,
        fats=record.fats,
        plan=record.get_plan(),
        saved=True,
        viewing_history=True,
    )
