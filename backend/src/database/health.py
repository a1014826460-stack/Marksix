from __future__ import annotations

from typing import Any

import psycopg


PROBE_CONNECT_TIMEOUT_SECONDS = 2


def _probe_target(target: str) -> None:
    connection = psycopg.connect(target, connect_timeout=PROBE_CONNECT_TIMEOUT_SECONDS)
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


def collect_database_health(write_target: str, read_target: str) -> dict[str, Any]:
    write = _role_health(write_target)
    read = _role_health(read_target)
    return {
        "ok": bool(write["ok"] and read["ok"]),
        "database": {"write": write, "read": read},
    }
