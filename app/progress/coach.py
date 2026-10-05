"""
Adaptive tuning rules for FitFuel (pure Python: no Flask, no database).

Given a user's goal, their calorie target, and their recent weekly check-ins,
decide whether the plan should change:

  * CALORIES   - compare the real weight trend (kg/week) with a healthy range
                 for the goal, then nudge the daily target by half the gap
                 (capped, never below a safe floor).
  * DIFFICULTY - if the last two check-ins both hit the workout goal, step the
                 plan up one level; if both were very low, step it down.

Keeping this logic separate from the web layer makes it easy to read, to test
(see tests/test_coach.py) and to tweak the numbers below.
"""

from datetime import date

# ---------------------------------------------------------------- settings
WORKOUT_DAYS_TARGET = 5       # workouts per week we ask for (rest days are healthy)
LOW_WORKOUTS = 2              # <= this many workouts = "struggling"
KCAL_PER_KG = 7700            # rough energy content of 1 kg of body weight
MAX_STEP_KCAL = 250           # never change the target by more than this at once
MIN_STEP_KCAL = 50            # ...and ignore changes smaller than this
WINDOW_DAYS = 28              # only look at the last 4 weeks of weights
MIN_SPAN_DAYS = 7             # need weights at least a week apart to see a trend
MIN_DIFFICULTY, MAX_DIFFICULTY = 1, 5

# Healthy weekly weight change in kg: (too_slow_or_low, ideal, too_fast_or_high)
RATE_RANGES = {
    "cutting":     (-0.75, -0.50, -0.25),   # losing 0.25-0.75 kg/week is on track
    "bulking":     (0.15, 0.30, 0.50),      # gaining 0.15-0.50 kg/week is on track
    "maintaining": (-0.20, 0.00, 0.20),     # staying within +/-0.2 kg/week
}

# Never recommend eating below these (kcal/day).
CALORIE_FLOOR = {"male": 1500, "female": 1200}
DEFAULT_FLOOR = 1350


def calorie_floor(gender):
    return CALORIE_FLOOR.get((gender or "").lower(), DEFAULT_FLOOR)


# ------------------------------------------------------------------ trends
def weekly_rate(points, today=None):
    """Weight trend in kg/week using a least-squares line through the points.

    points: iterable of (date, weight_kg). Returns None when there isn't
    enough data (fewer than 2 points, or all within a week of each other)."""
    today = today or date.today()
    pts = sorted(p for p in points if 0 <= (today - p[0]).days <= WINDOW_DAYS)
    if len(pts) < 2 or (pts[-1][0] - pts[0][0]).days < MIN_SPAN_DAYS:
        return None
    start = pts[0][0]
    xs = [(d - start).days for d, _ in pts]
    ys = [w for _, w in pts]
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None
    slope_per_day = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    return slope_per_day * 7


def streak(workout_counts, target=WORKOUT_DAYS_TARGET):
    """Consecutive most-recent check-ins that met the workout goal.
    workout_counts: list of ints ordered oldest -> newest."""
    count = 0
    for done in reversed(workout_counts):
        if done >= target:
            count += 1
        else:
            break
    return count


# --------------------------------------------------------- recommendation
def _round25(value):
    return int(round(value / 25.0) * 25)


def recommend(*, goal, gender, current_calories, difficulty, weight_points,
              workout_counts, today=None):
    """Return a dict describing what (if anything) should change.

    weight_points: [(date, kg), ...]      workout_counts: [int, ...] oldest -> newest
    status is one of: "need_data", "on_track", "adjust".
    """
    goal = goal if goal in RATE_RANGES else "maintaining"
    low, ideal, high = RATE_RANGES[goal]
    rate = weekly_rate(weight_points, today)
    reasons = []

    # ---- calories -------------------------------------------------------
    new_calories = int(round(current_calories))
    calorie_change = 0
    if rate is None:
        reasons.append("Log weight check-ins at least a week apart to unlock calorie tuning.")
    elif low <= rate <= high:
        reasons.append(f"Your weight is moving {rate:+.2f} kg/week, which is right on track for {goal}.")
    else:
        gap = ideal - rate                       # kg/week we want to move
        change = 0.5 * gap * KCAL_PER_KG / 7     # fix half the gap per adjustment
        change = max(-MAX_STEP_KCAL, min(MAX_STEP_KCAL, change))
        if abs(change) < MIN_STEP_KCAL:
            change = MIN_STEP_KCAL if change >= 0 else -MIN_STEP_KCAL
        proposed = _round25(current_calories + change)
        floor = calorie_floor(gender)
        if proposed < floor:
            proposed = max(floor, int(round(current_calories)))
            reasons.append(
                f"Your target is already near the safe minimum ({floor} kcal), so it won't be "
                "lowered further. Try adding activity instead."
            )
        new_calories = proposed
        calorie_change = new_calories - int(round(current_calories))
        if calorie_change:
            direction = "above" if rate > high else "below"
            reasons.append(
                f"Your weight is moving {rate:+.2f} kg/week, {direction} the healthy range for {goal} "
                f"({low:+.2f} to {high:+.2f}), so the target changes by {calorie_change:+d} kcal/day."
            )
        if goal == "cutting" and rate < -1.0:
            reasons.append("You're losing weight quickly. Losing more than about 1 kg/week isn't recommended.")

    # ---- difficulty -----------------------------------------------------
    new_difficulty = difficulty
    if len(workout_counts) >= 2:
        last_two = workout_counts[-2:]
        if all(w >= WORKOUT_DAYS_TARGET for w in last_two) and difficulty < MAX_DIFFICULTY:
            new_difficulty = difficulty + 1
            reasons.append(f"You hit {WORKOUT_DAYS_TARGET}+ workouts two check-ins in a row, so difficulty goes up one level.")
        elif all(w <= LOW_WORKOUTS for w in last_two) and difficulty > MIN_DIFFICULTY:
            new_difficulty = difficulty - 1
            reasons.append("Your last two weeks were light on workouts, so difficulty comes down a level to keep it doable.")
    else:
        reasons.append("Log two weekly check-ins to unlock difficulty tuning.")

    difficulty_change = new_difficulty - difficulty
    if rate is None and difficulty_change == 0:
        status = "need_data"
    elif calorie_change == 0 and difficulty_change == 0:
        status = "on_track"
    else:
        status = "adjust"

    return {
        "status": status,
        "rate": rate,
        "goal": goal,
        "range": (low, high),
        "current_calories": int(round(current_calories)),
        "new_calories": new_calories,
        "calorie_change": calorie_change,
        "difficulty": difficulty,
        "new_difficulty": new_difficulty,
        "difficulty_change": difficulty_change,
        "reasons": reasons,
    }
