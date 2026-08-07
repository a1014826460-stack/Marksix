from __future__ import annotations

from typing import Any

from db import connect


def _probe_target(target: str) -> None:
    with connect(target) as conn:
        row = conn.execute("SELECT 1 AS ok").fetchone()
        if not row or int(row["ok"]) != 1:
            raise RuntimeError("database probe returned an invalid result")


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
