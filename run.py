"""
Entry point for local development.

For production, use a WSGI server instead, e.g.:
    gunicorn -w 4 -b 0.0.0.0:5001 "run:app"
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["APP_PORT"], debug=app.config["DEBUG"])
