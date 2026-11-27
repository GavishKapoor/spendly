import re
from pathlib import Path

import pytest

from database import db

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "profile.html"
STYLESHEET = ROOT / "static" / "css" / "profile.css"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    # Import only after patching: importing app runs init_db() and seed_db().
    from app import app

    # The import is cached after the first test, so set up each temp DB here.
    db.init_db()
    db.seed_db()
    monkeypatch.setitem(app.config, "TESTING", True)
    return app.test_client()


def _sign_in(client, email="demo@spendly.com", password="demo123"):
    response = client.post("/login", data={"email": email, "password": password})
    assert response.status_code == 302


def _profile_html(client):
    _sign_in(client)
    response = client.get("/profile")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_signed_out_visitor_is_redirected_to_login(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_redirects_to_profile(client):
    response = client.post(
        "/login", data={"email": "demo@spendly.com", "password": "demo123"}
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


@pytest.mark.parametrize("path", ["/login", "/register"])
def test_signed_in_user_is_sent_to_profile(client, path):
    _sign_in(client)

    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


@pytest.mark.parametrize("user_id", [0, None, ""])
def test_empty_session_user_id_does_not_loop(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/profile", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/login"


def test_account_card_shows_user_details(client):
    html = _profile_html(client)

    assert re.search(r'class="profile-avatar"[^>]*>DU<', html)
    assert re.search(r'class="profile-name">Demo User<', html)
    assert re.search(r'class="profile-email">demo@spendly\.com<', html)
    assert "Member since November 2026" in html


def test_summary_shows_three_stats(client):
    html = _profile_html(client)

    values = re.findall(r'class="profile-stat-value">([^<]*)<', html)
    assert values == ["₹6,348.00", "8", "Shopping"]


def test_transactions_are_listed_newest_first(client):
    html = _profile_html(client)

    rows = re.findall(
        r'<tr class="profile-row">\s*'
        r'<td class="profile-date">\s*<time datetime="[^"]+">([^<]*)</time>\s*</td>\s*'
        r"<td>([^<]*)</td>\s*"
        r'<td><span class="category-badge">([^<]*)</span></td>\s*'
        r'<td class="profile-amount">([^<]*)</td>',
        html,
    )

    assert rows == [
        ("2026-11-27", "Stationery", "Other", "₹150.00"),
        ("2026-11-23", "Dinner with friends", "Food", "₹280.00"),
        ("2026-11-19", "New shoes", "Shopping", "₹2,300.00"),
        ("2026-11-15", "Movie tickets", "Entertainment", "₹499.00"),
        ("2026-11-12", "Pharmacy", "Health", "₹650.00"),
        ("2026-11-08", "Electricity bill", "Bills", "₹1,899.00"),
        ("2026-11-04", "Metro card recharge", "Transport", "₹120.00"),
        ("2026-11-01", "Groceries", "Food", "₹450.00"),
    ]


def test_category_breakdown_lists_every_category(client):
    html = _profile_html(client)

    names = re.findall(r'class="profile-category-name">([^<]*)<', html)
    totals = re.findall(r'class="profile-category-total">([^<]*)<', html)
    bars = re.findall(r'<progress class="profile-category-bar" value="(\d+)"', html)

    assert list(zip(names, totals, bars)) == [
        ("Shopping", "₹2,300.00", "36"),
        ("Bills", "₹1,899.00", "30"),
        ("Food", "₹730.00", "11"),
        ("Health", "₹650.00", "10"),
        ("Entertainment", "₹499.00", "8"),
        ("Other", "₹150.00", "2"),
        ("Transport", "₹120.00", "2"),
    ]
    assert sorted(names) == sorted(db.CATEGORIES)


def test_navbar_shows_signed_in_state(client):
    db.create_user("Asha Rao", "asha@example.com", "password123")
    _sign_in(client, "asha@example.com", "password123")

    html = client.get("/profile").get_data(as_text=True)

    assert re.search(r'href="/profile" class="nav-user">Asha Rao<', html)
    assert 'href="/logout"' in html


def test_profile_is_protected_again_after_logout(client):
    _sign_in(client)
    client.get("/logout")

    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize("path", [TEMPLATE, STYLESHEET], ids=lambda p: p.name)
def test_profile_files_have_no_hex_colours(path):
    source = path.read_text(encoding="utf-8")

    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", source)


def test_profile_template_has_no_inline_styles():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "style=" not in source
    assert "<style" not in source
