from __future__ import annotations

from pathlib import Path

from db import connect
from public.api import get_public_latest_draw
from helpers import get_effective_next_draw_payload
from runtime_config import ensure_system_config_table, seed_system_config_defaults
from tables import ensure_admin_tables


def _setup_db(tmp_path: Path) -> str:
    db_path = str(tmp_path / "taiwan_next_issue.sqlite3")
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        seed_system_config_defaults(conn, now="2026-01-01T00:00:00+00:00")
    return db_path


def test_taiwan_next_issue_uses_current_plus_one(tmp_path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3, 2026, 131, "01,02,03,04,05,06,07", "2026-05-14 22:30:00",
                "", 1, 1, 132, "2026-05-14 14:30:00", "2026-05-14 14:30:00",
            ),
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
                3, 2026, 133, "", "2026-05-16 22:30:00",
                "", 1, 0, 134, "2026-05-15 14:30:00", "2026-05-15 14:30:00",
            ),
        )
        payload = get_effective_next_draw_payload(conn, 3)

    assert payload["current_issue"] == "2026131"
    assert payload["next_issue"] == "2026132"


def test_taiwan_next_issue_crosses_year_boundary(tmp_path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3, 2024, 365, "01,02,03,04,05,06,07", "2024-12-31 22:30:00",
                "", 1, 1, 366, "2024-12-31 14:30:00", "2024-12-31 14:30:00",
            ),
        )
        payload = get_effective_next_draw_payload(conn, 3)

    assert payload["current_issue"] == "2024365"
    assert payload["next_issue"] == "2025001"


def test_taiwan_missing_issue_sends_gap_alert_once(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    sent: list[tuple[str, str, str]] = []

    def fake_send_alert_async(target, subject, body_html):
        sent.append((str(target), subject, body_html))

    monkeypatch.setattr("alerts.email_service.send_alert_async", fake_send_alert_async)

    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3, 2026, 131, "01,02,03,04,05,06,07", "2026-05-14 22:30:00",
                "", 1, 1, 132, "2026-05-14 14:30:00", "2026-05-14 14:30:00",
            ),
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
                3, 2026, 133, "", "2026-05-16 22:30:00",
                "", 1, 0, 134, "2026-05-15 14:30:00", "2026-05-15 14:30:00",
            ),
        )

        payload_first = get_effective_next_draw_payload(conn, 3)
        payload_second = get_effective_next_draw_payload(conn, 3)

    assert payload_first["next_issue"] == "2026132"
    assert payload_second["next_issue"] == "2026132"
    assert len(sent) == 1
    assert "2026132" in sent[0][1]


def test_public_latest_draw_includes_draw_time(tmp_path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lottery_draws (
                lottery_type_id, year, term, numbers, draw_time, next_time, status,
                is_opened, next_term, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3, 2026, 131, "01,02,03,04,05,06,07", "2026-05-14 22:30:00",
                "", 1, 1, 132, "2026-05-14 14:30:00", "2026-05-14 14:30:00",
            ),
        )

    payload = get_public_latest_draw(db_path, 3)

    assert payload["current_issue"] == "2026131"
    assert payload["draw_time"] == "2026-05-14 22:30:00"
