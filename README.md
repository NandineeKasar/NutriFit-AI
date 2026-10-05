# FitFuel — AI-Driven Personalized Fitness & Nutrition Recommendation System

A Flask web app that generates a personalized weekly workout and meal plan
from a user's body stats, goal, and preferences — now with full MySQL-backed
authentication, saved plan history, and an admin panel.

---

## What changed from the original project

The uploaded project was a single `app.py` file plus two loose HTML pages
with no authentication, no database, and a few bugs. It's been rebuilt into
a modular Flask application. Full breakdown below.

### 1. Authentication (new)
- **Registration** — name, email, password, with server-side validation
  (valid email format, strong-password policy, duplicate-email check).
- **Login** — email + password, "remember me" option, session-based via
  Flask-Login.
- **Password hashing** — bcrypt via Flask-Bcrypt; plaintext passwords are
  never stored or logged.
- **Logout** — clears the session.
- **Account lockout** — 5 failed logins locks the account for 15 minutes,
  slowing down brute-force attacks.
- **Rate limiting** — the login endpoint is capped at 10 requests/minute
  per IP (Flask-Limiter).
- **SQL injection prevention** — all queries go through SQLAlchemy's ORM
  with bound parameters; no string-formatted SQL anywhere in the app.
- **CSRF protection** — every form is protected via Flask-WTF's CSRF
  tokens.
- **Generic auth errors** — login failures always say "Invalid email or
  password" (never "no such user") to prevent account enumeration.
- **Secure cookies** — session cookies are `HttpOnly`, `SameSite=Lax`, and
  `Secure` outside local development.

### 2. MySQL database
- `database/schema.sql` — creates the database, a least-privilege app
  user, and the `users` / `plan_history` tables.
- SQLAlchemy models in `app/models.py` mirror that schema and will also
  auto-create the tables on first run if you'd rather skip running the
  SQL file manually.

### 3. Existing functionality preserved
- The original BMR/TDEE calculation (Mifflin-St Jeor formula), macro
  split, workout-plan generator, meal-plan generator, and the
  RandomForestRegressor calorie-accuracy check are all still here,
  refactored into `app/recommender/engine.py` with the same behavior.

### 4. Bugs fixed
- **Missing datasets**: `new_cleaned_exercise_dataset.csv` and
  `neutritionData1.csv` were referenced by `app.py` but not included in
  the project at all — the app could not have run as uploaded. Sample
  datasets with matching columns are now included under `app/data/`.
  **Replace them with your real datasets** by dropping in files with the
  same column names.
- **Missing `templates/` and `static/` folders**: `index.html` and
  `result.html` used `render_template` and `url_for('static', ...)` but
  there was no `templates/` or `static/` directory anywhere in the
  project, so both the page render and every image/background would
  have failed. Templates now live in `app/templates/`, static assets in
  `app/static/`.
- **`result.html` referenced `fog.avif`**, a file that did not exist
  anywhere in the project. Replaced with an existing background image.
- **Meal-plan generator crashed** (`IndexError`) whenever fewer than 4
  meals matched the selected diet type, because it blindly indexed
  `iloc[0]` through `iloc[3]`. It now only builds as many meal lines as
  rows actually available.
- **`bmr` was undefined** for any gender value other than exactly
  `"male"` or `"female"` (e.g. empty/garbled form data), causing an
  `UnboundLocalError`. There's now a safe neutral fallback, plus the form
  field is now a required radio button and validated server-side too.
- **No input validation at all** — the `/predict` route trusted every
  form field blindly (`float(request.form['height'])` etc. with no
  try/except), so a single bad field crashed the whole request with a
  500 error. All inputs are now validated with sensible ranges and clear
  error messages.
- Removed committed IDE cruft (`tempCodeRunnerFile.py`, `tempCodeRunnerFile.python`)
  that had nothing to do with the app.

### 5. Other improvements
- **Modular structure** — app factory pattern, blueprints for `auth`,
  `main`, and `admin`, a dedicated `recommender` package for the ML/plan
  logic.
- **Environment variables** — all secrets (DB credentials, Flask secret
  key) are read from a `.env` file via `python-dotenv`, never hard-coded.
- **Logging** — rotating file logs at `logs/app.log` capture
  registrations, logins/logouts, lockouts, plan generation, and
  unhandled server errors (never passwords).
- **User dashboard** — shows plan count, member-since date, last login,
  and the 5 most recent plans.
- **Plan history** — every plan a logged-in user generates is saved and
  can be revisited later.
- **Admin panel** (optional, gated by `is_admin`) — lists all users, plan
  counts, and lets an admin promote/demote or activate/deactivate
  accounts.
- **Responsive, redesigned UI** — a consistent dark theme with a single
  accent color across the landing page, plan form, results page,
  dashboard, history, and auth pages; works down to mobile widths.
- **Loading indicator** — a full-screen overlay appears while a plan is
  being generated, and client-side + server-side validation both give
  clear feedback instead of silent failures.
- **Custom error pages** for 403 / 404 / 500.

---

## Project structure

```
build/
├── app/
│   ├── __init__.py            # app factory, logging, error handlers
│   ├── config.py              # env-based configuration
│   ├── extensions.py          # db, bcrypt, login_manager, csrf, limiter
│   ├── models.py               # User, PlanHistory
│   ├── auth/                   # registration/login/logout blueprint
│   ├── main/                   # plan builder, dashboard, history blueprint
│   ├── admin/                  # admin panel blueprint
│   ├── recommender/
│   │   └── engine.py           # workout/meal plan generation + BMR/TDEE/macros
│   ├── data/                   # exercise & nutrition CSV datasets
│   ├── templates/              # Jinja2 templates
│   └── static/                 # css/js/images
├── database/
│   └── schema.sql              # MySQL schema (tables + app user)
├── scripts/
│   └── make_admin.py           # promote a user to admin from the CLI
├── logs/                        # rotating app.log written here at runtime
├── .env.example
├── requirements.txt
└── run.py                       # local dev entry point
```

---

## Setup instructions

### 1. Prerequisites
- Python 3.10+
- A running MySQL server (8.0+ recommended)

### 2. Clone/copy the project and create a virtual environment
```bash
cd build
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure MySQL
Create the database, app user, and tables:
```bash
mysql -u root -p < database/schema.sql
```
This creates a `fitness_db` database and a `fitness_user` MySQL account.
**Edit `database/schema.sql` and change `'change-this-password'` to a real
password before running it.**

If you'd rather let the app create the tables itself, you can skip
running `schema.sql` — `db.create_all()` runs automatically on startup —
but you'll still need to create the `fitness_db` database and a MySQL
user manually first.

### 4. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in:
```
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DB_HOST=localhost
DB_PORT=3306
DB_USER=fitness_user
DB_PASSWORD=<the password you set in schema.sql>
DB_NAME=fitness_db
```

### 5. Run the app
```bash
python run.py
```
The app starts on `http://localhost:5001` by default (change `APP_PORT`
in `.env` if needed).

### 6. (Optional) Promote a user to admin
Register a normal account through the UI first, then run:
```bash
python scripts/make_admin.py you@example.com
```
Log out and back in, and you'll see an **Admin** link in the navbar.

### 7. Using your own datasets
The included CSVs in `app/data/` are synthetic placeholders (the
originals referenced by the uploaded code were missing from the project
entirely). Replace them with your real data, keeping the same column
names:

- `new_cleaned_exercise_dataset.csv`: `Exercise Name`, `Targeted Muscle`,
  `Difficulty Level`
- `neutritionData1.csv`: `Recipe Name`, `Veg / Non-veg`, `Protein (g)`,
  `Carbs (g)`, `Fat (g)`, `Total Calories`

---

## Running in production

Use a WSGI server instead of the Flask dev server:
```bash
gunicorn -w 4 -b 0.0.0.0:5001 "run:app"
```
Also set `FLASK_ENV=production` in `.env` so debug mode is off and
session cookies require HTTPS. Put the app behind a reverse proxy
(nginx) that terminates TLS.

For rate limiting in a multi-process/multi-server production deployment,
configure Flask-Limiter with a shared backend (e.g. Redis) instead of the
default in-memory store — see the
[Flask-Limiter docs](https://flask-limiter.readthedocs.io) for
`storage_uri`.

---

## Security notes

- Never commit your real `.env` file.
- Rotate `SECRET_KEY` and database credentials if they're ever exposed.
- The account-lockout and rate-limit values (5 attempts / 15 min,
  10 requests/min) can be tuned in `app/auth/routes.py`.
- All templates use Jinja2's automatic HTML escaping, which is Flask's
  default and protects against basic XSS from user-entered data (e.g.
  the `name` field on the plan form).


## 🚀 Live Demo

🔗 **Live Application:** https://nutri-fit-ai-taupe.vercel.app/

The application is deployed using Vercel with MySQL database hosted on Railway.
