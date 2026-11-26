# Spec: Login and Logout

## Overview
Implement session-based authentication so registered users can sign in to Spendly and sign out again. This step upgrades `GET /login` to also accept a POST that checks the submitted credentials against the `users` table and stores the user in Flask's signed session cookie, and it replaces the `GET /logout` stub with a route that clears that session. The navbar changes to reflect whether a visitor is signed in. This establishes the logged-in state that the profile page (Step 4) and the expense features (Steps 7–9) depend on.

## Depends on
- Step 01 — Database setup (`users` table, `get_db()`, demo user)
- Step 02 — Registration (`create_user()`, flash messages, `app.secret_key`)

## Routes
- `GET /login` — render the login form; redirect to `/` if already signed in — public (already exists, upgrade it)
- `POST /login` — validate credentials, start the session, redirect to `/` — public
- `GET /logout` — clear the session, redirect to `/` — public, safe to visit when signed out (replaces the stub)
- `GET /register` and `POST /register` — redirect to `/` if already signed in — public (existing, small change)

## Database changes
No new tables or columns. The existing `users` table (id, name, email, password_hash, created_at) covers all requirements.

A new DB helper must be added to `database/db.py`:
- `get_user_by_email(email)` — returns the matching `users` row (`sqlite3.Row`), or `None` if no user has that email. Closes its connection before returning.

## Templates
- **Create:** none
- **Modify:** `templates/login.html`
  - Change the hardcoded `action="/login"` to `url_for('login')`
  - Repopulate the email input after a failed attempt (never the password)
  - Remove the unused `{% if error %}` block; errors are shown through flash messages
  - Keep all existing visual design
- **Modify:** `templates/base.html`
  - When signed out: show "Sign in" and "Get started" as today
  - When signed in: show the user's name and a "Sign out" link to `url_for('logout')` in their place
  - The "Sign out" link must stay visible at widths of 600px and below, where `style.css` hides every nav link without the `nav-cta` class

## Files to change
- `app.py` — handle `GET` and `POST` in `login()`; implement `logout()`; redirect signed-in users away from `login()` and `register()`; import `session`, `check_password_hash` and `get_user_by_email`
- `database/db.py` — add `get_user_by_email()`
- `templates/login.html` — wire up the form action and email repopulation
- `templates/base.html` — conditional navbar links
- `static/css/style.css` — style for the signed-in user's name in the navbar
- `CLAUDE.md` — update the route table: `POST /login` and `GET /logout` are implemented

## Files to create
None.

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (already installed) and Flask's built-in `session` / `flash` / `redirect` / `url_for`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use f-strings in SQL
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare or store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode URLs
- DB logic lives in `database/db.py` only — no queries in routes
- Routes go in `app.py` only — no blueprints
- Normalise the email with `.strip().lower()`, as `register()` does; do not strip or alter the password
- Login checks only that both fields are non-empty — do not apply the 8-character registration rule (the demo password `demo123` is 7 characters)
- An unknown email and a wrong password must show the same message: "Invalid email or password"
- If either field is empty, show "All fields are required"
- On any failure, flash the message with category `error` and re-render the form — do not redirect
- On success, call `session.clear()`, then store `user_id` and `user_name` in the session
- Never put the password or password hash in the session
- Logout uses `session.clear()`
- Do not flash a message on successful login or logout — the landing page does not render flashes, so it would appear later on an unrelated page. The navbar shows the new state
- Do not implement `/profile` or any expense route — they belong to later steps

## Definition of done
- [ ] `GET /login` renders the form without errors when signed out
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/`, and the navbar shows "Demo User" and "Sign out"
- [ ] Signing in with the email in different case or with surrounding spaces also works
- [ ] A newly registered user can sign in with the password they chose
- [ ] A wrong password re-renders the form with "Invalid email or password" and the email still filled in
- [ ] An unregistered email shows the same "Invalid email or password" message
- [ ] Submitting an empty or whitespace-only email, or an empty password, shows "All fields are required" (send the POST directly, since the browser blocks empty required fields)
- [ ] The signed-in state persists across page loads (`/`, `/terms`, `/privacy`)
- [ ] Visiting `/login` or `/register` while signed in redirects to `/`
- [ ] Clicking "Sign out" redirects to `/`, and the navbar shows "Sign in" and "Get started" again
- [ ] Visiting `/logout` while signed out redirects to `/` without errors
- [ ] "Sign out" is visible and usable in a browser window narrower than 600px
- [ ] No message from login or logout appears later on the login or register page
