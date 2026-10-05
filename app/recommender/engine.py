"""
Recommendation engine: workout plan generation, meal plan generation,
and the calorie-prediction regression model.

This is a refactor of the original single-file app.py logic. Bug fixes
made here (see README for full list):
  * Meal plan generation no longer crashes when fewer than 4 matching
    meals exist for a diet type (previously `.iloc[1]`/`.iloc[3]` would
    raise IndexError).
  * BMR calculation now has a safe fallback for genders other than
    'male'/'female' instead of leaving `bmr` undefined (UnboundLocalError).
  * Datasets and the trained model are loaded/trained exactly once at
    import time and cached, instead of implicitly relying on module-level
    globals scattered through app.py.
"""

import logging
import random
from pathlib import Path

import pandas as pd
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_absolute_percentage_error
# from sklearn.model_selection import train_test_split
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_percentage_error
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except Exception:  # blocked DLL / not installed
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EXERCISE_CSV = DATA_DIR / "new_cleaned_exercise_dataset.csv"
NUTRITION_CSV = DATA_DIR / "neutritionData1.csv"

ACTIVITY_LEVEL_MAPPING = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very active": 1.9,
}

VALID_GOALS = {"bulking", "cutting", "maintaining"}
VALID_GENDERS = {"male", "female"}
VALID_DIET_TYPES = {"veg", "non-veg"}
VALID_MUSCLES = {"chest", "back", "legs", "shoulder", "biceps", "triceps", "core"}


class RecommendationEngine:
    """Loads the datasets once and exposes plan-generation helpers."""

    def __init__(self):
        if not EXERCISE_CSV.exists() or not NUTRITION_CSV.exists():
            raise FileNotFoundError(
                "Required dataset CSV files are missing from app/data/. "
                "Expected: new_cleaned_exercise_dataset.csv and neutritionData1.csv"
            )

        self.exercise_df = pd.read_csv(EXERCISE_CSV)
        self.nutrition_df = pd.read_csv(NUTRITION_CSV)

        self.exercise_df["Targeted Muscle"] = (
            self.exercise_df["Targeted Muscle"].str.lower().str.strip()
        )
        self.nutrition_df["Veg / Non-veg"] = (
            self.nutrition_df["Veg / Non-veg"].str.lower().str.strip()
        )

        self.model, self.accuracy = self._train_model()
        logger.info("Calorie regression model trained. Accuracy=%.2f%%", self.accuracy)

    # def _train_model(self):
    #     X = self.nutrition_df[["Protein (g)", "Carbs (g)", "Fat (g)"]]
    #     y = self.nutrition_df["Total Calories"]
    #     X_train, X_test, y_train, y_test = train_test_split(
    #         X, y, test_size=0.2, random_state=42
    #     )
    #     model = RandomForestRegressor(n_estimators=100, random_state=42)
    #     model.fit(X_train, y_train)

    #     y_pred = model.predict(X_test)
    #     mape = mean_absolute_percentage_error(y_test, y_pred)
    #     accuracy = 100 - (mape * 100)
    #     return model, accuracy

    def _train_model(self):
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn unavailable; skipping calorie model.")
            return None, 0.0
        X = self.nutrition_df[["Protein (g)", "Carbs (g)", "Fat (g)"]]
        y = self.nutrition_df["Total Calories"]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mape = mean_absolute_percentage_error(y_test, y_pred)
        accuracy = 100 - (mape * 100)
        return model, accuracy

    # -- Workout plan ------------------------------------------------------
    def generate_workout_plan(self, targeted_muscle: str, difficulty: int, num_weeks: int):
        plan = []
        filtered = self.exercise_df[
            (self.exercise_df["Targeted Muscle"] == targeted_muscle)
            & (self.exercise_df["Difficulty Level"] <= difficulty)
        ]
        available_exercises = list(filtered["Exercise Name"].unique())

        for week in range(1, num_weeks + 1):
            for day in range(1, 8):
                if not available_exercises:
                    daily_exercises = ["No available exercises for this selection."]
                else:
                    sample_size = min(3, len(available_exercises))
                    daily_exercises = random.sample(available_exercises, sample_size)
                plan.append(
                    {
                        "week": week,
                        "day": day,
                        "workout": [f"{ex} - 3 sets x 8 reps" for ex in daily_exercises],
                    }
                )
        return plan

    # -- Meal plan -----------------------------------------------------------
    def generate_meal_plan(self, diet_type: str, num_weeks: int):
        plan = []
        filtered = self.nutrition_df[self.nutrition_df["Veg / Non-veg"] == diet_type]

        meal_labels = ["Breakfast", "Lunch", "Dinner", "Snack"]

        for week in range(1, num_weeks + 1):
            for day in range(1, 8):
                if filtered.empty:
                    plan.append(
                        {
                            "week": week,
                            "day": day,
                            "diet": ["No available meals for this selection."],
                        }
                    )
                    continue

                # Fix: sample only as many rows as actually exist, and only
                # label as many meals as we actually got back, instead of
                # blindly indexing iloc[0..3] (which crashed on small datasets).
                sample_n = min(len(meal_labels), len(filtered))
                daily_meals = filtered.sample(sample_n)
                diet_lines = [
                    f"{meal_labels[i]}: {row['Recipe Name']} - {row['Total Calories']} kcal"
                    for i, (_, row) in enumerate(daily_meals.iterrows())
                ]
                plan.append({"week": week, "day": day, "diet": diet_lines})
        return plan

    # -- Combined plan ------------------------------------------------------
    def build_full_plan(self, *, targeted_muscle, difficulty, num_weeks, diet_type):
        workout_plan = self.generate_workout_plan(targeted_muscle, difficulty, num_weeks)
        meal_plan = self.generate_meal_plan(diet_type, num_weeks)

        full_plan = []
        for i in range(len(workout_plan)):
            full_plan.append(
                {
                    "week": workout_plan[i]["week"],
                    "day": workout_plan[i]["day"],
                    "workout": workout_plan[i]["workout"],
                    "diet": meal_plan[i]["diet"] if i < len(meal_plan) else [],
                }
            )
        return full_plan


def calculate_bmr(*, weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor formula. Falls back safely for unrecognized genders
    instead of leaving `bmr` undefined (a bug in the original code)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == "male":
        return base + 5
    if gender == "female":
        return base - 161
    # Neutral fallback: average of the male/female offsets.
    return base - 78


def calculate_daily_calories(bmr: float, activity_level_str: str, goal: str):
    activity_level = ACTIVITY_LEVEL_MAPPING.get(activity_level_str, 1.2)
    tdee = bmr * activity_level

    if goal == "bulking":
        daily_calories = tdee * 1.2
    elif goal == "cutting":
        daily_calories = tdee * 0.8
    else:
        daily_calories = tdee
    return daily_calories


def calculate_macros(daily_calories: float):
    protein = round((daily_calories * 0.3) / 4, 1)
    carbs = round((daily_calories * 0.4) / 4, 1)
    fats = round((daily_calories * 0.3) / 9, 1)
    return protein, carbs, fats


# Singleton, created once when the module is first imported by the app factory.
_engine_instance = None


def get_engine() -> "RecommendationEngine":
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RecommendationEngine()
    return _engine_instance
