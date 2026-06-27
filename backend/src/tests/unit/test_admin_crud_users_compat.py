from __future__ import annotations

from pathlib import Path

from db import connect
from tables import ensure_admin_tables


def test_admin_crud_user_compat_delegates_to_domain_service(monkeypatch):
    from admin import crud

    calls: list[tuple[str, tuple[object, ...]]] = []

    def fake_list_users(*args, **kwargs):
        calls.append(("list", args + (kwargs,)))
        return [{"id": 1, "username": "admin"}]

    def fake_save_user(*args, **kwargs):
        calls.append(("save", args + (kwargs,)))
        return {"id": 2, "username": "operator"}

    def fake_delete_user(*args, **kwargs):
        calls.append(("delete", args + (kwargs,)))
        return None

    monkeypatch.setattr("domains.users.service.list_users", fake_list_users)
    monkeypatch.setattr("domains.users.service.save_user", fake_save_user)
    monkeypatch.setattr("domains.users.service.delete_user", fake_delete_user)

    db_path = Path("delegation-only.sqlite3")
    assert crud.list_users(db_path) == [{"id": 1, "username": "admin"}]
    assert crud.save_user(db_path, {"username": "operator"}, user_id=2) == {"id": 2, "username": "operator"}
    assert crud.delete_user(db_path, 2) is None

    assert calls == [
        ("list", (db_path, {})),
        ("save", (db_path, {"username": "operator"}, {"user_id": 2})),
        ("delete", (db_path, 2, {})),
    ]


def test_users_service_create_update_list_and_password_behavior(tmp_path):
    from domains.users import service

    db_path = tmp_path / "users.sqlite3"
    ensure_admin_tables(db_path)

    created = service.save_user(
        db_path,
        {
            "username": "operator",
            "display_name": "Operator",
            "role": "editor",
            "status": True,
            "password": "first-secret",
        },
    )

    assert created["username"] == "operator"
    assert created["display_name"] == "Operator"
    assert created["role"] == "editor"
    assert created["status"] is True
    assert "password_hash" not in created

    with connect(db_path) as conn:
        first_hash = conn.execute(
            "SELECT password_hash FROM admin_users WHERE id = ?",
            (created["id"],),
        ).fetchone()["password_hash"]

    updated_without_password = service.save_user(
        db_path,
        {
            "username": "operator2",
            "display_name": "Operator Two",
            "role": "admin",
            "status": False,
            "password": "",
        },
        user_id=created["id"],
    )

    assert updated_without_password["id"] == created["id"]
    assert updated_without_password["username"] == "operator2"
    assert updated_without_password["display_name"] == "Operator Two"
    assert updated_without_password["role"] == "admin"
    assert updated_without_password["status"] is False
    assert "password_hash" not in updated_without_password

    with connect(db_path) as conn:
        unchanged_hash = conn.execute(
            "SELECT password_hash FROM admin_users WHERE id = ?",
            (created["id"],),
        ).fetchone()["password_hash"]
    assert unchanged_hash == first_hash

    updated_with_password = service.save_user(
        db_path,
        {
            "username": "operator2",
            "display_name": "Operator Two",
            "role": "admin",
            "status": True,
            "password": "second-secret",
        },
        user_id=created["id"],
    )
    assert updated_with_password["status"] is True

    with connect(db_path) as conn:
        changed_hash = conn.execute(
            "SELECT password_hash FROM admin_users WHERE id = ?",
            (created["id"],),
        ).fetchone()["password_hash"]
    assert changed_hash != first_hash

    rows = service.list_users(db_path)
    row_by_id = {row["id"]: row for row in rows}
    assert row_by_id[created["id"]]["username"] == "operator2"
    assert "password_hash" not in row_by_id[created["id"]]


def test_users_service_validates_create_update_and_delete_safety(tmp_path):
    from domains.users import service

    db_path = tmp_path / "user_errors.sqlite3"
    ensure_admin_tables(db_path)

    try:
        service.save_user(db_path, {"username": "", "password": "x"})
    except ValueError as exc:
        assert str(exc)
    else:
        raise AssertionError("empty username should fail")

    try:
        service.save_user(db_path, {"username": "missing-password"})
    except ValueError as exc:
        assert str(exc)
    else:
        raise AssertionError("create without password should fail")

    try:
        service.save_user(db_path, {"username": "missing", "password": "x"}, user_id=99999)
    except KeyError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("missing user update should fail")

    with connect(db_path) as conn:
        conn.execute("UPDATE admin_users SET status = 0")

    active = service.save_user(
        db_path,
        {"username": "sole-active", "password": "secret", "status": True},
    )
    try:
        service.delete_user(db_path, active["id"])
    except ValueError as exc:
        assert str(exc)
    else:
        raise AssertionError("deleting the only active admin should fail")

    disabled = service.save_user(
        db_path,
        {"username": "disabled", "password": "secret", "status": False},
    )
    service.delete_user(db_path, disabled["id"])
    with connect(db_path) as conn:
        deleted = conn.execute("SELECT id FROM admin_users WHERE id = ?", (disabled["id"],)).fetchone()
    assert deleted is None
