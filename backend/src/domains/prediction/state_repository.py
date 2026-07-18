from __future__ import annotations

from typing import Any


def get_mechanism_statuses(conn: Any) -> dict[str, int]:
    rows = conn.execute("SELECT mechanism_key, status FROM mechanism_status").fetchall()
    return {str(row["mechanism_key"]): int(row["status"]) for row in rows}


def set_mechanism_status(
    conn: Any,
    mechanism_key: str,
    status: int,
    *,
    updated_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO mechanism_status (mechanism_key, status, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(mechanism_key) DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (str(mechanism_key), int(status), str(updated_at)),
    )
