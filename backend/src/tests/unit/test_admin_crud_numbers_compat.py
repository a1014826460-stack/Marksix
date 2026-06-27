from __future__ import annotations

from pathlib import Path

from db import connect
from tables import ensure_admin_tables


def _ensure_fixed_data_table(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE fixed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                code TEXT,
                sign TEXT,
                year TEXT,
                status INTEGER,
                type TEXT,
                xu INTEGER
            )
            """
        )


def test_admin_crud_number_compat_delegates_to_domain_service(monkeypatch):
    from admin import crud

    calls: list[tuple[str, tuple[object, ...]]] = []

    def fake_list_numbers(*args, **kwargs):
        calls.append(("list", args + (kwargs,)))
        return [{"id": 1, "status": True}]

    def fake_update_number(*args, **kwargs):
        calls.append(("update", args + (kwargs,)))
        return {"id": 2, "status": False}

    def fake_create_number(*args, **kwargs):
        calls.append(("create", args + (kwargs,)))
        return {"id": 3, "status": True}

    def fake_delete_number(*args, **kwargs):
        calls.append(("delete", args + (kwargs,)))
        return None

    monkeypatch.setattr("domains.numbers.service.list_numbers", fake_list_numbers)
    monkeypatch.setattr("domains.numbers.service.update_number", fake_update_number)
    monkeypatch.setattr("domains.numbers.service.create_number", fake_create_number)
    monkeypatch.setattr("domains.numbers.service.delete_number", fake_delete_number)

    db_path = Path("delegation-only.sqlite3")
    assert crud.list_numbers(db_path, limit=20, keyword="01", sign="red") == [{"id": 1, "status": True}]
    assert crud.update_number(db_path, 2, {"status": False}) == {"id": 2, "status": False}
    assert crud.create_number(db_path, {"name": "one"}) == {"id": 3, "status": True}
    assert crud.delete_number(db_path, 3) is None

    assert calls == [
        ("list", (db_path, {"limit": 20, "keyword": "01", "sign": "red"})),
        ("update", (db_path, 2, {"status": False}, {})),
        ("create", (db_path, {"name": "one"}, {})),
        ("delete", (db_path, 3, {})),
    ]


def test_numbers_service_crud_preserves_admin_payload_shape(tmp_path):
    from domains.numbers import service

    db_path = tmp_path / "numbers.sqlite3"
    ensure_admin_tables(db_path)
    _ensure_fixed_data_table(db_path)

    created = service.create_number(
        db_path,
        {
            "name": "Alpha",
            "code": "01",
            "category_key": "red",
            "year": "2026",
            "status": True,
            "type": "manual",
            "xu": 9,
        },
    )

    assert list(created.keys()) == ["id", "name", "code", "category_key", "year", "status", "type", "xu"]
    assert created["name"] == "Alpha"
    assert created["code"] == "01"
    assert created["category_key"] == "red"
    assert created["year"] == "2026"
    assert created["status"] is True
    assert created["type"] == "manual"
    assert created["xu"] == 9

    rows = service.list_numbers(db_path, limit=10, keyword="alp", sign="red")
    assert rows == [created]

    updated = service.update_number(
        db_path,
        created["id"],
        {
            "name": "Beta",
            "code": "02",
            "sign": "blue",
            "year": "2027",
            "status": False,
        },
    )
    assert updated == {
        "id": created["id"],
        "name": "Beta",
        "code": "02",
        "category_key": "blue",
        "year": "2027",
        "status": False,
        "type": "manual",
        "xu": 9,
    }

    service.delete_number(db_path, created["id"])
    with connect(db_path) as conn:
        deleted = conn.execute("SELECT id FROM fixed_data WHERE id = ?", (created["id"],)).fetchone()
    assert deleted is None


def test_numbers_service_missing_update_and_delete_raise_key_error(tmp_path):
    from domains.numbers import service

    db_path = tmp_path / "numbers_errors.sqlite3"
    ensure_admin_tables(db_path)
    _ensure_fixed_data_table(db_path)

    try:
        service.update_number(db_path, 99999, {"name": "missing"})
    except KeyError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("missing number update should fail")

    try:
        service.delete_number(db_path, 99999)
    except KeyError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("missing number delete should fail")
