from __future__ import annotations

from typing import Any

import psycopg


PROBE_CONNECT_TIMEOUT_SECONDS = 2
PROBE_STATEMENT_TIMEOUT_MILLISECONDS = 2000


def _probe_target(target: str) -> None:
    connection = psycopg.connect(
        target,
        connect_timeout=PROBE_CONNECT_TIMEOUT_SECONDS,
        options=f"-c statement_timeout={PROBE_STATEMENT_TIMEOUT_MILLISECONDS}",
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
        if not row or int(row[0]) != 1:
            raise RuntimeError("database probe returned an invalid result")
    finally:
        connection.close()


def _role_health(target: str) -> dict[str, Any]:
    try:
        _probe_target(target)
    except Exception:
        return {"ok": False, "error": "dependency unavailable"}
    return {"ok": True}


def _collect_operational_metrics(target: str) -> dict[str, Any]:
    connection = psycopg.connect(
        target,
        connect_timeout=PROBE_CONNECT_TIMEOUT_SECONDS,
        options=f"-c statement_timeout={PROBE_STATEMENT_TIMEOUT_MILLISECONDS}",
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE state = 'idle in transaction'),
                COALESCE(MAX(EXTRACT(EPOCH FROM (clock_timestamp() - state_change)))
                    FILTER (WHERE state = 'idle in transaction'), 0),
                COUNT(*) FILTER (WHERE wait_event_type = 'Lock'),
                COALESCE(MAX(EXTRACT(EPOCH FROM (clock_timestamp() - query_start)))
                    FILTER (WHERE wait_event_type = 'Lock'), 0)
            FROM pg_stat_activity
            WHERE datname = current_database() AND pid <> pg_backend_pid()
            """
        )
        activity = cursor.fetchone() or (0, 0, 0, 0)
        cursor.execute(
            "SELECT COUNT(*) FROM publication_outbox WHERE status IN ('pending', 'processing')"
        )
        outbox = cursor.fetchone() or (0,)
        return {
            "available": True,
            "idle_in_transaction": {
                "count": int(activity[0] or 0),
                "longest_seconds": int(activity[1] or 0),
            },
            "lock_waits": {
                "count": int(activity[2] or 0),
                "longest_seconds": int(activity[3] or 0),
            },
            "publication_outbox_unpublished": int(outbox[0] or 0),
        }
    finally:
        connection.close()


def collect_database_health(
    write_target: str,
    read_target: str,
    *,
    include_operational: bool = False,
) -> dict[str, Any]:
    write = _role_health(write_target)
    read = _role_health(read_target)
    payload = {
        "ok": bool(write["ok"] and read["ok"]),
        "database": {"write": write, "read": read},
    }
    if include_operational:
        try:
            operational = _collect_operational_metrics(write_target) if write["ok"] else {"available": False}
        except Exception:
            operational = {"available": False, "error": "dependency unavailable"}
        payload["operational"] = operational
    return payload
