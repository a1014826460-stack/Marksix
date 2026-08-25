from __future__ import annotations

from random import Random

import pytest


def test_taiwan_future_autofill_settings_defaults_and_validation(tmp_path):
    from domains.lottery.service import (
        get_taiwan_future_autofill_settings,
        parse_taiwan_future_autofill_settings,
        save_taiwan_future_autofill_settings,
    )

    db_path = tmp_path / "taiwan-autofill-settings.sqlite3"
    settings = get_taiwan_future_autofill_settings(db_path)
    assert settings == {"enabled": False, "count": 12, "time": "00:00", "timezone": "Asia/Shanghai"}

    saved = save_taiwan_future_autofill_settings(
        db_path,
        {"enabled": True, "count": 18, "time": "07:45"},
        changed_by="admin",
    )
    assert saved == {"enabled": True, "count": 18, "time": "07:45", "timezone": "Asia/Shanghai"}
    assert get_taiwan_future_autofill_settings(db_path) == saved

    for payload in (
        {"enabled": "yes", "count": 12, "time": "07:45"},
        {"enabled": True, "count": 0, "time": "07:45"},
        {"enabled": True, "count": 61, "time": "07:45"},
        {"enabled": True, "count": 12, "time": "24:00"},
        {"enabled": True, "count": 12, "time": "7:45"},
    ):
        with pytest.raises(ValueError):
            parse_taiwan_future_autofill_settings(payload)
from pathlib import Path

from db import connect
from tables import ensure_admin_tables


def test_taiwan_future_draw_candidate_enforces_recent_positional_constraints():
    from domains.lottery.service import _is_valid_taiwan_future_candidate

    recent = [
        [1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14],
    ]

    assert _is_valid_taiwan_future_candidate([15, 16, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([1, 16, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 2, 17, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 16, 3, 18, 19, 20, 21], recent)
    assert not _is_valid_taiwan_future_candidate([15, 16, 17, 18, 19, 20, 7], recent)
    assert not _is_valid_taiwan_future_candidate([1, 2, 3, 4, 5, 6, 7], recent)
    assert not _is_valid_taiwan_future_candidate([15, 15, 17, 18, 19, 20, 21], recent)


def _insert_taiwan_draw(
    conn,
    *,
    year: int,
    term: int,
    numbers: str,
    draw_time: str,
    is_opened: int,
) -> int:
    row = conn.execute(
        """
        INSERT INTO lottery_draws (
            lottery_type_id, year, term, numbers, draw_time, next_time, status,
            is_opened, next_term, created_at, updated_at
        )
        VALUES (3, ?, ?, ?, ?, '', 1, ?, ?, ?, ?)
        RETURNING id
        """,
        (
            year,
            term,
            numbers,
            draw_time,
            is_opened,
            term + 1,
            "2026-06-27T00:00:00+00:00",
            "2026-06-27T00:00:00+00:00",
        ),
    ).fetchone()
    return int(row["id"])


def test_autofill_taiwan_future_draws_preserves_existing_future_rows(tmp_path):
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-future.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_types SET draw_time = '22:30:00' WHERE id = 3")
        _insert_taiwan_draw(
            conn,
            year=2026,
            term=100,
            numbers="01,02,03,04,05,06,07",
            draw_time="2026-04-10 22:30:00",
            is_opened=1,
        )
        existing_id = _insert_taiwan_draw(
            conn,
            year=2026,
            term=102,
            numbers="08,09,10,11,12,13,14",
            draw_time="2026-04-12 22:30:00",
            is_opened=0,
        )

    result = autofill_taiwan_future_draws(db_path, count=12, rng=Random(7))

    assert result["requested_count"] == 12
    assert result["created_count"] == 12
    assert result["preserved_existing_count"] == 1
    assert len(result["created"]) == 12
    assert all(len(row["numbers"].split(",")) == 7 for row in result["created"])
    assert all(row["term"] != 102 for row in result["created"])

    with connect(db_path) as conn:
        existing_after = conn.execute(
            "SELECT id, numbers, is_opened FROM lottery_draws WHERE id = ?", (existing_id,)
        ).fetchone()
        rows = conn.execute(
            """
            SELECT numbers FROM lottery_draws
            WHERE lottery_type_id = 3
            ORDER BY year, term, id
            """
        ).fetchall()

    assert dict(existing_after) == {
        "id": existing_id,
        "numbers": "08,09,10,11,12,13,14",
        "is_opened": 0,
    }
    parsed_rows = [[int(number) for number in row["numbers"].split(",")] for row in rows]
    for index, numbers in enumerate(parsed_rows):
        assert len(numbers) == 7
        assert len(set(numbers)) == 7
        for previous in parsed_rows[max(0, index - 10):index]:
            assert numbers != previous
            assert all(numbers[position] != previous[position] for position in (0, 1, 2, 6))


def test_autofill_taiwan_future_draws_skips_first_existing_future_issue(tmp_path):
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-first-existing.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _insert_taiwan_draw(
            conn,
            year=2026,
            term=100,
            numbers="01,02,03,04,05,06,07",
            draw_time="2026-04-10 22:30:00",
            is_opened=1,
        )
        existing_id = _insert_taiwan_draw(
            conn,
            year=2026,
            term=101,
            numbers="08,09,10,11,12,13,14",
            draw_time="2026-04-11 22:30:00",
            is_opened=0,
        )

    result = autofill_taiwan_future_draws(db_path, count=2, rng=Random(11))

    assert result["created_count"] == 2
    assert result["preserved_existing_count"] == 1
    assert all(row["term"] != 101 for row in result["created"])
    with connect(db_path) as conn:
        existing_after = conn.execute(
            "SELECT numbers FROM lottery_draws WHERE id = ?", (existing_id,)
        ).fetchone()
    assert existing_after["numbers"] == "08,09,10,11,12,13,14"


def test_autofill_taiwan_future_draws_treats_count_as_total_future_target(tmp_path):
    """A scheduled target includes preserved future rows rather than adding to them."""
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-total-target.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _insert_taiwan_draw(
            conn,
            year=2026,
            term=100,
            numbers="01,02,03,04,05,06,07",
            draw_time="2026-04-10 22:30:00",
            is_opened=1,
        )
        existing_id = _insert_taiwan_draw(
            conn,
            year=2026,
            term=101,
            numbers="08,09,10,11,12,13,14",
            draw_time="2026-04-11 22:30:00",
            is_opened=0,
        )

    result = autofill_taiwan_future_draws(db_path, count=1, rng=Random(11), target_total=True)

    assert result["created_count"] == 0
    assert result["preserved_existing_count"] == 1
    with connect(db_path) as conn:
        future_rows = conn.execute(
            "SELECT id, numbers, is_opened FROM lottery_draws WHERE lottery_type_id = 3 AND is_opened = 0"
        ).fetchall()
    assert [dict(row) for row in future_rows] == [
        {"id": existing_id, "numbers": "08,09,10,11,12,13,14", "is_opened": 0}
    ]


def test_autofill_taiwan_future_draws_fills_to_configured_total_after_two_existing_rows(tmp_path):
    """Latest opened 100 plus preserved 101/102 must cover the full 101..112 target."""
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-total-twelve.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _insert_taiwan_draw(
            conn, year=2026, term=100, numbers="01,02,03,04,05,06,07",
            draw_time="2026-04-10 22:30:00", is_opened=1,
        )
        for term, numbers, date in (
            (101, "08,09,10,11,12,13,14", "2026-04-11 22:30:00"),
            (102, "15,16,17,18,19,20,21", "2026-04-12 22:30:00"),
        ):
            _insert_taiwan_draw(
                conn, year=2026, term=term, numbers=numbers, draw_time=date, is_opened=0,
            )

    result = autofill_taiwan_future_draws(db_path, count=12, rng=Random(31), target_total=True)

    assert result["created_count"] == 10
    assert result["preserved_existing_count"] == 2
    with connect(db_path) as conn:
        terms = [
            int(row["term"])
            for row in conn.execute(
                "SELECT term FROM lottery_draws WHERE lottery_type_id = 3 AND is_opened = 0 ORDER BY term"
            ).fetchall()
        ]
    assert terms == list(range(101, 113))


def test_scheduled_autofill_repairs_holes_in_the_contiguous_future_sequence(tmp_path):
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-contiguous.sqlite3"
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        _insert_taiwan_draw(
            conn, year=2026, term=222, numbers="01,02,03,04,05,06,07",
            draw_time="2026-08-10 22:32:00", is_opened=1,
        )
        for term in (224, 225, 226, 227, 229, 230, 231, 232, 233, 234):
            _insert_taiwan_draw(
                conn, year=2026, term=term, numbers="08,09,10,11,12,13,14",
                draw_time=f"2026-08-{term - 212:02d} 22:32:00", is_opened=0,
            )

    result = autofill_taiwan_future_draws(
        db_path, count=12, rng=Random(17), target_total=True,
    )

    assert [(item["year"], item["term"]) for item in result["created"]] == [
        (2026, 223), (2026, 228),
    ]
    with connect(db_path) as conn:
        terms = [
            int(row["term"])
            for row in conn.execute(
                "SELECT term FROM lottery_draws WHERE lottery_type_id = 3 AND is_opened = 0 ORDER BY term"
            ).fetchall()
        ]
    assert terms == list(range(223, 235))


def test_autofill_taiwan_future_draws_rejects_invalid_count_and_missing_baseline(tmp_path):
    from domains.lottery.service import autofill_taiwan_future_draws

    db_path = tmp_path / "autofill-invalid.sqlite3"
    ensure_admin_tables(db_path)

    for count in (0, 61):
        try:
            autofill_taiwan_future_draws(db_path, count=count)
        except ValueError as exc:
            assert "1 到 60" in str(exc)
        else:
            raise AssertionError("invalid count should fail")

    try:
        autofill_taiwan_future_draws(db_path)
    except ValueError as exc:
        assert "已开奖" in str(exc)
    else:
        raise AssertionError("missing opened baseline should fail")


def test_admin_crud_lottery_compat_delegates_to_domain_service(monkeypatch):
    from admin import crud

    calls: list[tuple[str, tuple[object, ...]]] = []

    def fake_list_lottery_types(*args, **kwargs):
        calls.append(("list_types", args + (kwargs,)))
        return [{"id": 3, "status": True}]

    def fake_save_lottery_type(*args, **kwargs):
        calls.append(("save_type", args + (kwargs,)))
        return {"id": 3, "name": "taiwan", "status": True}

    def fake_delete_lottery_type(*args, **kwargs):
        calls.append(("delete_type", args + (kwargs,)))
        return None

    def fake_list_draws(*args, **kwargs):
        calls.append(("list_draws", args + (kwargs,)))
        return {"draws": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 1}

    def fake_save_draw(*args, **kwargs):
        calls.append(("save_draw", args + (kwargs,)))
        return {"id": 88, "status": True, "is_opened": True}

    def fake_delete_draw(*args, **kwargs):
        calls.append(("delete_draw", args + (kwargs,)))
        return None

    monkeypatch.setattr("domains.lottery.service.list_lottery_types", fake_list_lottery_types)
    monkeypatch.setattr("domains.lottery.service.save_lottery_type", fake_save_lottery_type)
    monkeypatch.setattr("domains.lottery.service.delete_lottery_type", fake_delete_lottery_type)
    monkeypatch.setattr("domains.lottery.service.list_draws", fake_list_draws)
    monkeypatch.setattr("domains.lottery.service.save_draw", fake_save_draw)
    monkeypatch.setattr("domains.lottery.service.delete_draw", fake_delete_draw)

    db_path = Path("delegation-only.sqlite3")

    assert crud.list_lottery_types(db_path) == [{"id": 3, "status": True}]
    assert crud.save_lottery_type(db_path, {"name": "taiwan"}, lottery_id=3) == {
        "id": 3,
        "name": "taiwan",
        "status": True,
    }
    assert crud.delete_lottery_type(db_path, 3) is None
    assert crud.list_draws(db_path, limit=20, offset=40, lottery_type_id=3) == {
        "draws": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }
    assert crud.save_draw(db_path, {"term": 188}, draw_id=88) == {
        "id": 88,
        "status": True,
        "is_opened": True,
    }
    assert crud.delete_draw(db_path, 88) is None
    assert calls == [
        ("list_types", (db_path, {})),
        ("save_type", (db_path, {"name": "taiwan"}, {"lottery_id": 3})),
        ("delete_type", (db_path, 3, {})),
        ("list_draws", (db_path, {"limit": 20, "offset": 40, "lottery_type_id": 3})),
        ("save_draw", (db_path, {"term": 188}, {"draw_id": 88})),
        ("delete_draw", (db_path, 88, {})),
    ]


def test_lottery_service_get_latest_opened_draw_result(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "latest-opened-draw.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        rows = [
            (3, 2026, 126, "01,02,03,04,05,06,07", "2026-06-25 22:30:00", 1),
            (3, 2026, 127, "08,09,10,11,12,13,14", "2026-06-26 22:30:00", 1),
            (3, 2026, 128, "15,16,17,18,19,20,21", "2026-06-27 22:30:00", 0),
            (2, 2026, 200, "22,23,24,25,26,27,28", "2026-06-27 21:30:00", 1),
        ]
        for lottery_type_id, year, term, numbers, draw_time, is_opened in rows:
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, next_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lottery_type_id,
                    year,
                    term,
                    numbers,
                    draw_time,
                    "",
                    1,
                    is_opened,
                    term + 1,
                    "2026-06-27T00:00:00+00:00",
                    "2026-06-27T00:00:00+00:00",
                ),
            )

    assert service.get_latest_opened_draw_result(db_path, 3) == {
        "year": 2026,
        "term": 127,
        "numbers": "08,09,10,11,12,13,14",
    }
    assert service.get_latest_opened_draw_result(db_path, 1) is None


def test_lottery_service_get_latest_opened_draw_term_preserves_admin_shape(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "latest-opened-draw-term.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        rows = [
            (3, 2026, 126, "2026-06-25 22:30:00", 1),
            (3, 2026, 127, "2026-06-26 22:30:00", 1),
            (3, 2026, 128, "2026-06-27 22:30:00", 0),
            (2, 2026, 200, "2026-06-27 21:30:00", 1),
        ]
        for lottery_type_id, year, term, draw_time, is_opened in rows:
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, next_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lottery_type_id,
                    year,
                    term,
                    "01,02,03,04,05,06,07",
                    draw_time,
                    "",
                    1,
                    is_opened,
                    term + 1,
                    "2026-06-27T00:00:00+00:00",
                    "2026-06-27T00:00:00+00:00",
                ),
            )

    assert service.get_latest_opened_draw_term(db_path, 3) == {
        "year": 2026,
        "term": 127,
        "draw_time": "2026-06-26 22:30:00",
    }
    assert service.get_latest_opened_draw_term(db_path, 1) == {
        "year": 0,
        "term": 0,
        "draw_time": "",
    }


def test_admin_crud_save_draw_preserves_legacy_ensure_admin_tables_patch_point(monkeypatch, tmp_path):
    from admin import crud
    from domains.lottery import service

    db_path = tmp_path / "legacy-patch.sqlite3"
    patched_calls: list[Path] = []

    def fake_admin_tables(path):
        patched_calls.append(Path(path))

    def fake_save_draw(path, payload, draw_id=None):
        service.ensure_admin_tables(path)
        return {"id": draw_id or 1, "payload": payload}

    monkeypatch.setattr(crud, "ensure_admin_tables", fake_admin_tables)
    monkeypatch.setattr(service, "save_draw", fake_save_draw)

    result = crud.save_draw(db_path, {"term": 132}, draw_id=7)

    assert result == {"id": 7, "payload": {"term": 132}}
    assert patched_calls == [db_path]


def test_lottery_service_list_lottery_types_preserves_effective_next_time(tmp_path):
    from domains.lottery import service
    from helpers import draw_time_to_unix_ms

    db_path = tmp_path / "lottery_service.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE lottery_types
            SET next_time = ?
            WHERE id = ?
            """,
            ("stale-next-time", 3),
        )
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                2026,
                188,
                "01,02,03,04,05,06,07",
                "2026-06-27 22:30:00",
                "1782570600000",
                1,
                1,
                189,
                "2026-06-27T14:30:00+00:00",
                "2026-06-27T14:30:00+00:00",
            ),
        )

    rows = service.list_lottery_types(db_path)

    taiwan = next(row for row in rows if row["id"] == 3)
    assert taiwan["status"] is True
    expected_next_time = draw_time_to_unix_ms("2026-06-28 22:30:00")
    assert taiwan["next_time"] == expected_next_time

    with connect(db_path) as conn:
        stored = conn.execute(
            "SELECT next_time FROM lottery_types WHERE id = ?",
            (3,),
        ).fetchone()
    assert stored["next_time"] == expected_next_time


def test_lottery_service_save_lottery_type_preserves_admin_write_behavior(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "lottery_type_write.sqlite3"
    ensure_admin_tables(db_path)

    created = service.save_lottery_type(
        db_path,
        {
            "name": "custom lottery",
            "draw_time": "20:15",
            "collect_url": "https://example.test/api",
            "next_time": "ignored-by-service",
            "status": False,
        },
    )

    assert list(created.keys()) == [
        "id",
        "name",
        "draw_time",
        "collect_url",
        "status",
        "created_at",
        "updated_at",
        "next_time",
        "last_auto_task_status",
    ]
    assert created["name"] == "custom lottery"
    assert created["draw_time"] == "20:15"
    assert created["collect_url"] == "https://example.test/api"
    assert created["status"] is False
    assert created["next_time"] == ""

    updated = service.save_lottery_type(
        db_path,
        {
            "name": "renamed lottery",
            "draw_time": "21:30",
            "collect_url": "https://example.test/next",
            "next_time": "still-ignored",
            "status": True,
        },
        lottery_id=created["id"],
    )

    assert updated["id"] == created["id"]
    assert updated["name"] == "renamed lottery"
    assert updated["draw_time"] == "21:30"
    assert updated["collect_url"] == "https://example.test/next"
    assert updated["status"] is True
    assert updated["next_time"] == ""

    service.delete_lottery_type(db_path, created["id"])

    with connect(db_path) as conn:
        deleted = conn.execute(
            "SELECT id FROM lottery_types WHERE id = ?",
            (created["id"],),
        ).fetchone()
    assert deleted is None


def test_lottery_service_save_lottery_type_validates_name_and_missing_update(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "lottery_type_write_errors.sqlite3"
    ensure_admin_tables(db_path)

    try:
        service.save_lottery_type(db_path, {"name": "   "})
    except ValueError as exc:
        assert str(exc)
    else:
        raise AssertionError("empty lottery name should fail")

    try:
        service.save_lottery_type(db_path, {"name": "missing"}, lottery_id=99999)
    except KeyError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("missing lottery id should fail")

    try:
        service.delete_lottery_type(db_path, 99999)
    except KeyError as exc:
        assert "99999" in str(exc)
    else:
        raise AssertionError("missing lottery id delete should fail")


def test_lottery_service_list_draws_preserves_admin_payload_shape(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "lottery_draws.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        for term in (188, 189):
            conn.execute(
                """
                INSERT INTO lottery_draws (
                    lottery_type_id, year, term, numbers, draw_time, next_time, status,
                    is_opened, next_term, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    3,
                    2026,
                    term,
                    "01,02,03,04,05,06,07",
                    f"2026-06-{term - 161:02d} 22:30:00",
                    "1782570600000",
                    1,
                    term == 188,
                    term + 1,
                    "2026-06-27T14:30:00+00:00",
                    "2026-06-27T14:30:00+00:00",
                ),
            )

    payload = service.list_draws(db_path, limit=1, offset=1, lottery_type_id=3)

    assert list(payload.keys()) == ["draws", "total", "page", "page_size", "total_pages"]
    assert payload["total"] == 2
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert payload["total_pages"] == 2
    assert len(payload["draws"]) == 1
    assert payload["draws"][0]["term"] == 188
    assert payload["draws"][0]["lottery_name"]
    assert payload["draws"][0]["status"] is True
    assert payload["draws"][0]["is_opened"] is True


def test_lottery_service_rejects_changes_to_opened_draws(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "delete_draw.sqlite3"
    ensure_admin_tables(db_path)

    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                3,
                2026,
                188,
                "01,02,03,04,05,06,07",
                "2026-06-27 22:30:00",
                "1782570600000",
                1,
                1,
                189,
                "2026-06-27T14:30:00+00:00",
                "2026-06-27T14:30:00+00:00",
            ),
        ).fetchone()
        draw_id = int(row["id"])

    try:
        service.delete_draw(db_path, draw_id)
    except ValueError as exc:
        assert "已开奖" in str(exc)
    else:
        raise AssertionError("opened draw delete should fail")

    try:
        service.save_draw(
            db_path,
            {
                "lottery_type_id": 3,
                "year": 2026,
                "term": 188,
                "numbers": "08,09,10,11,12,13,14",
                "draw_time": "2026-06-27 22:30:00",
                "next_time": "1782570600000",
                "status": True,
                "is_opened": True,
                "next_term": 189,
            },
            draw_id=draw_id,
        )
    except ValueError as exc:
        assert "已开奖" in str(exc)
    else:
        raise AssertionError("opened draw update should fail")


def test_lottery_service_save_draw_preserves_admin_create_and_backfill_behavior(tmp_path):
    from domains.lottery import service
    from helpers import draw_time_to_unix_ms

    db_path = tmp_path / "save_draw.sqlite3"
    ensure_admin_tables(db_path)

    previous_draw_time = "2026-06-25 22:30:00"
    new_draw_time = "2026-06-26 22:30:00"
    with connect(db_path) as conn:
        previous = conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                3,
                2026,
                188,
                "01,02,03,04,05,06,07",
                previous_draw_time,
                draw_time_to_unix_ms(previous_draw_time),
                1,
                1,
                189,
                "2026-06-27T14:30:00+00:00",
                "2026-06-27T14:30:00+00:00",
            ),
        ).fetchone()
        previous_draw_id = int(previous["id"])

    created = service.save_draw(
        db_path,
        {
            "lottery_type_id": 3,
            "year": 2026,
            "term": 189,
            "numbers": "08,09,10,11,12,13,14",
            "draw_time": new_draw_time,
            "next_time": "1782743400000",
            "status": True,
            "is_opened": True,
            "next_term": 190,
        },
    )

    assert list(created.keys()) == [
        "id",
        "lottery_type_id",
        "year",
        "term",
        "numbers",
        "draw_time",
        "status",
        "is_opened",
        "next_term",
        "created_at",
        "updated_at",
        "next_time",
    ]
    assert created["lottery_type_id"] == 3
    assert created["year"] == 2026
    assert created["term"] == 189
    assert created["numbers"] == "08,09,10,11,12,13,14"
    assert created["draw_time"] == new_draw_time
    assert created["status"] is True
    assert created["is_opened"] is True

    with connect(db_path) as conn:
        previous_after = conn.execute(
            "SELECT next_time FROM lottery_draws WHERE id = ?",
            (previous_draw_id,),
        ).fetchone()
        lottery_type = conn.execute(
            "SELECT next_time FROM lottery_types WHERE id = ?",
            (3,),
        ).fetchone()

    assert previous_after["next_time"] == draw_time_to_unix_ms(new_draw_time)
    assert lottery_type["next_time"] == draw_time_to_unix_ms("2026-06-27 22:30:00")


def test_lottery_service_save_draw_preserves_admin_validation_behavior(tmp_path):
    from domains.lottery import service

    db_path = tmp_path / "save_draw_errors.sqlite3"
    ensure_admin_tables(db_path)

    invalid_payload = {
        "lottery_type_id": 3,
        "year": 2026,
        "term": 189,
        "numbers": "01,02",
        "draw_time": "2026-06-26 22:30:00",
        "status": True,
        "is_opened": True,
    }

    try:
        service.save_draw(db_path, invalid_payload)
    except ValueError as exc:
        assert "2" in str(exc)
    else:
        raise AssertionError("invalid number count should fail")

    unsupported_payload = dict(invalid_payload)
    unsupported_payload["lottery_type_id"] = 1
    unsupported_payload["numbers"] = "01,02,03,04,05,06,07"
    try:
        service.save_draw(db_path, unsupported_payload)
    except ValueError as exc:
        assert str(exc)
    else:
        raise AssertionError("unsupported lottery type should fail")
