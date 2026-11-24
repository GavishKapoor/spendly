import sqlite3
from contextlib import closing
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db


def _insert_user(conn, email="user@example.com", name="Test User"):
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, "hash"),
    )
    conn.commit()
    return cursor.lastrowid


def _insert_expense(conn, user_id, amount=10.0, category="Food", day="2026-01-15"):
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, day, "test"),
    )
    conn.commit()


def test_tables_exist(temp_db):
    with closing(temp_db.get_db()) as conn:
        names = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = ?", ("table",))
        }
    assert {"users", "expenses"} <= names


def test_foreign_keys_enabled(temp_db):
    with closing(temp_db.get_db()) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_row_factory(temp_db):
    with closing(temp_db.get_db()) as conn:
        _insert_user(conn, email="row@example.com")
        row = conn.execute("SELECT email FROM users").fetchone()
    assert row["email"] == "row@example.com"


def test_init_db_idempotent(temp_db):
    temp_db.init_db()
    temp_db.init_db()


def test_seed_idempotent(temp_db):
    temp_db.seed_db()
    temp_db.seed_db()
    with closing(temp_db.get_db()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 8
        user = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("demo@spendly.com",)
        ).fetchone()
    assert check_password_hash(user["password_hash"], "demo123")


def test_seed_covers_all_categories(temp_db):
    temp_db.seed_db()
    with closing(temp_db.get_db()) as conn:
        categories = {row["category"] for row in conn.execute("SELECT category FROM expenses")}
    assert categories == set(db.CATEGORIES)


def test_seed_dates_in_current_month(temp_db):
    temp_db.seed_db()
    today = date.today()
    with closing(temp_db.get_db()) as conn:
        dates = [row["date"] for row in conn.execute("SELECT date FROM expenses")]
    assert len(dates) == 8
    for value in dates:
        assert value.startswith(today.strftime("%Y-%m"))
        assert value <= today.isoformat()


def test_category_transport_allowed_travel_rejected(temp_db):
    with closing(temp_db.get_db()) as conn:
        user_id = _insert_user(conn)
        _insert_expense(conn, user_id, category="Transport")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_expense(conn, user_id, category="Travel")


def test_cascade_delete(temp_db):
    temp_db.seed_db()
    with closing(temp_db.get_db()) as conn:
        conn.execute("DELETE FROM users WHERE email = ?", ("demo@spendly.com",))
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0


def test_email_unique(temp_db):
    with closing(temp_db.get_db()) as conn:
        _insert_user(conn, email="dup@example.com")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_user(conn, email="dup@example.com")
        with pytest.raises(sqlite3.IntegrityError):
            _insert_user(conn, email="DUP@Example.com")


def test_fk_rejects_orphan(temp_db):
    with closing(temp_db.get_db()) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_expense(conn, user_id=999)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": -5},
        {"category": "Bogus"},
        {"day": "24/11/2026"},
    ],
)
def test_check_constraints(temp_db, overrides):
    with closing(temp_db.get_db()) as conn:
        user_id = _insert_user(conn)
        with pytest.raises(sqlite3.IntegrityError):
            _insert_expense(conn, user_id, **overrides)
