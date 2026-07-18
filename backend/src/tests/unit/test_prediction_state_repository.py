from __future__ import annotations

from db import connect
from domains.prediction import state_repository


def test_state_repository_upserts_and_lists_mechanism_statuses(tmp_path):
    db_path = tmp_path / "mechanism_status.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mechanism_status (
                mechanism_key TEXT PRIMARY KEY,
                status INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        state_repository.set_mechanism_status(conn, "pt3xiao", 1, updated_at="2026-07-17T00:00:00Z")
        state_repository.set_mechanism_status(conn, "pt3xiao", 0, updated_at="2026-07-17T00:01:00Z")

        assert state_repository.get_mechanism_statuses(conn) == {"pt3xiao": 0}
