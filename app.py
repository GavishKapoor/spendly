import sqlite3

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
# Development-only key, signs the session cookie. Replace before deploying.
app.secret_key = "spendly-dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Sample profile data — Step 5 replaces it with database/db.py calls  #
# ------------------------------------------------------------------ #

SAMPLE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "initials": "DU",
    "member_since": "November 2026",
}

SAMPLE_STATS = {
    "total_spent": 6348.00,
    "transaction_count": 8,
    "top_category": "Shopping",
}

# Newest first.
SAMPLE_TRANSACTIONS = [
    {"date": "2026-11-27", "description": "Stationery",
     "category": "Other", "amount": 150.00},
    {"date": "2026-11-23", "description": "Dinner with friends",
     "category": "Food", "amount": 280.00},
    {"date": "2026-11-19", "description": "New shoes",
     "category": "Shopping", "amount": 2300.00},
    {"date": "2026-11-15", "description": "Movie tickets",
     "category": "Entertainment", "amount": 499.00},
    {"date": "2026-11-12", "description": "Pharmacy",
     "category": "Health", "amount": 650.00},
    {"date": "2026-11-08", "description": "Electricity bill",
     "category": "Bills", "amount": 1899.00},
    {"date": "2026-11-04", "description": "Metro card recharge",
     "category": "Transport", "amount": 120.00},
    {"date": "2026-11-01", "description": "Groceries",
     "category": "Food", "amount": 450.00},
]

# Largest first. `percent` is the whole-number share of total_spent.
SAMPLE_CATEGORIES = [
    {"name": "Shopping", "total": 2300.00, "percent": 36},
    {"name": "Bills", "total": 1899.00, "percent": 30},
    {"name": "Food", "total": 730.00, "percent": 11},
    {"name": "Health", "total": 650.00, "percent": 10},
    {"name": "Entertainment", "total": 499.00, "percent": 8},
    {"name": "Other", "total": 150.00, "percent": 2},
    {"name": "Transport", "total": 120.00, "percent": 2},
]


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method in ("GET", "HEAD"):
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not all((name, email, password, confirm_password)):
        error = "All fields are required"
    elif password != confirm_password:
        error = "Passwords do not match"
    elif len(password) < 8:
        error = "Password must be at least 8 characters"
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "Email already registered"
        else:
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("login"))

    flash(error, "error")
    return render_template("register.html", name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    if request.method in ("GET", "HEAD"):
        return render_template("login.html")
    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        error = "All fields are required"
    else:
        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("profile"))
        error = "Invalid email or password"

    flash(error, "error")
    return render_template("login.html", email=email)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template(
        "profile.html",
        user=SAMPLE_USER,
        stats=SAMPLE_STATS,
        transactions=SAMPLE_TRANSACTIONS,
        categories=SAMPLE_CATEGORIES,
    )


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
