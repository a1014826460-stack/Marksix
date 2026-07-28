from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from auth import auth_user_from_token, hash_session_token, login_user
from app_http.response import ResponseWriter
from routes import auth_routes
from tables import ensure_admin_tables
from tests.helpers.api_contract import make_ctx, response_json


def test_new_session_persists_only_a_hash_and_authenticates_with_the_bearer_value(tmp_path):
    from db import connect

    db_path = str(tmp_path / "hashed-admin-session.sqlite3")
    ensure_admin_tables(db_path)

    login = login_user(db_path, "admin", "admin123")
    token = login["token"]
    with connect(db_path) as conn:
        stored = conn.execute("SELECT token, token_hash FROM admin_sessions").fetchone()

    assert stored["token"] != token
    assert stored["token_hash"] == hash_session_token(token)
    assert auth_user_from_token(db_path, token)["username"] == "admin"
    assert auth_user_from_token(db_path, stored["token"]) is None


def test_new_admin_session_defaults_to_forty_eight_hours(tmp_path):
    from db import connect

    db_path = str(tmp_path / "forty-eight-hour-session.sqlite3")
    ensure_admin_tables(db_path)
    login = login_user(db_path, "admin", "admin123")

    expires_at = datetime.fromisoformat(login["expires_at"])
    remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
    assert 47 * 60 * 60 + 55 * 60 <= remaining <= 48 * 60 * 60


def test_legacy_plaintext_session_rows_are_invalidated_during_schema_upgrade(tmp_path):
    from db import connect

    db_path = str(tmp_path / "legacy-plaintext-session.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE admin_sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL, expires_at TEXT)"
        )
        conn.execute(
            "INSERT INTO admin_sessions (token, user_id, created_at) VALUES ('legacy-plaintext-token', 1, '2026-01-01')"
        )

    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute("SELECT token, token_hash FROM admin_sessions").fetchone()

    assert row["token"] == "legacy-plaintext-token"
    assert row["token_hash"] == "legacy-plaintext-token"
    assert auth_user_from_token(db_path, "legacy-plaintext-token") is None


def test_request_context_uses_http_only_session_cookie_when_bearer_is_absent():
    ctx = make_ctx("/api/auth/me")
    ctx.handler.headers["Cookie"] = "liuhecai_admin_session=cookie-token; theme=dark"

    assert ctx.bearer_token() == "cookie-token"


def test_session_cookie_header_is_sent_after_the_http_status_line():
    events: list[tuple[str, str]] = []

    class _Handler:
        headers = {}
        wfile = type("W", (), {"write": lambda _self, _data: None})()

        def send_response(self, _status):
            events.append(("response", str(_status)))

        def send_header(self, key, value):
            events.append((key, value))

        def end_headers(self):
            events.append(("end", ""))

    response = ResponseWriter(_Handler())
    response.set_session_cookie("cookie-token", max_age_seconds=60, secure=True)
    response.send_json({"ok": True})

    assert events[0][0] == "response"
    assert next(index for index, item in enumerate(events) if item[0] == "Set-Cookie") > 0


def test_login_sets_a_secure_strict_http_only_cookie_without_changing_json_contract():
    ctx = make_ctx(
        "/api/auth/login",
        method="POST",
        payload={"username": "admin", "password": "secret", "captcha": "1234"},
    )
    ctx.handler.headers["X-Forwarded-Proto"] = "https"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    with patch("routes.auth_routes.check_login_locked", return_value=(False, "")), \
         patch("routes.auth_routes.verify_captcha", return_value=True), \
         patch("routes.auth_routes.login_user", return_value={"token": "bearer-token", "expires_at": expires_at, "user": {"id": 1}}), \
         patch("routes.auth_routes.reset_login_attempts"):
        auth_routes.login(ctx)

    assert response_json(ctx) == {"token": "bearer-token", "expires_at": expires_at, "user": {"id": 1}}
    cookies = [value for key, value in ctx.handler.response_headers if key.lower() == "set-cookie"]
    assert len(cookies) == 1
    assert "liuhecai_admin_session=bearer-token" in cookies[0]
    assert "HttpOnly" in cookies[0]
    assert "Secure" in cookies[0]
    assert "SameSite=Strict" in cookies[0]


def test_logout_clears_the_session_cookie_while_preserving_response_payload():
    ctx = make_ctx("/api/auth/logout", method="POST")
    ctx.handler.headers["Cookie"] = "liuhecai_admin_session=cookie-token"

    with patch("routes.auth_routes.logout_user") as logout_user:
        auth_routes.logout(ctx)

    assert response_json(ctx) == {"ok": True}
    logout_user.assert_called_once_with(ctx.db_path, "cookie-token")
    cookies = [value for key, value in ctx.handler.response_headers if key.lower() == "set-cookie"]
    assert len(cookies) == 1
    assert "Max-Age=0" in cookies[0]
    assert "HttpOnly" in cookies[0]
