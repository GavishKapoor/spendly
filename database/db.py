"""SQLite helpers for Spendly: connection, schema creation and dev seed data."""

import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")

# Keep in sync with the CHECK constraint on expenses.category below.
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount      REAL    NOT NULL CHECK (amount > 0),
    category    TEXT    NOT NULL CHECK (category IN
                  ('Food', 'Transport', 'Bills', 'Health',
                   'Entertainment', 'Shopping', 'Other')),
    date        TEXT    NOT NULL CHECK (date IS date(date)),
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);
"""


def get_db():
    """Return a new SQLite connection with Row access and foreign keys on.

    The caller is responsible for closing it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and indexes if they do not already exist."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a user with a hashed password and return the new id.

    Expects validated input. Raises sqlite3.IntegrityError if the email is
    already registered or a table constraint is violated.
    """
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _current_month_dates(count):
    """Return `count` ISO dates spread evenly from the 1st of this month to today."""
    today = date.today()
    span = today.day - 1
    return [
        date(today.year, today.month, 1 + i * span // (count - 1)).isoformat()
        for i in range(count)
    ]


def seed_db():
    """Insert a demo user and sample expenses. No-op if any user exists."""
    conn = get_db()
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        sample_expenses = [
            (450.00, "Food", "Groceries"),
            (120.00, "Transport", "Metro card recharge"),
            (1899.00, "Bills", "Electricity bill"),
            (650.00, "Health", "Pharmacy"),
            (499.00, "Entertainment", "Movie tickets"),
            (2300.00, "Shopping", "New shoes"),
            (280.00, "Food", "Dinner with friends"),
            (150.00, "Other", "Stationery"),
        ]
        dates = _current_month_dates(len(sample_expenses))
        rows = [
            (user_id, amount, category, expense_date, description)
            for (amount, category, description), expense_date in zip(
                sample_expenses, dates
            )
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
