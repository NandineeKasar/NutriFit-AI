"""
One-off helper to promote an existing user to admin status.

Usage:
    python scripts/make_admin.py user@example.com
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import User


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"No user found with email: {email}")
            sys.exit(1)
        user.is_admin = True
        db.session.commit()
        print(f"{email} is now an admin.")


if __name__ == "__main__":
    main()
