"""Number data service backed by fixed_data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db import connect
from helpers import parse_bool
from tables import ensure_admin_tables


def list_numbers(
    db_path: str | Path,
    limit: int = 300,
    keyword: str = "",
    sign: str = "",
) -> list[dict[str, Any]]:
    """List fixed_data rows using the admin payload shape."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        params: list[Any] = []
        conditions: list[str] = []
        if sign:
            conditions.append("sign = ?")
            params.append(sign)
        if keyword:
            conditions.append("(name LIKE ? OR sign LIKE ? OR code LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            f"""
            SELECT id, name, code, sign AS category_key, year, status, type, xu
            FROM fixed_data
            {where}
            ORDER BY xu ASC, id ASC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
        return [dict(row) | {"status": bool(row["status"])} for row in rows]


def update_number(db_path: str | Path, number_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Update a fixed_data row."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            UPDATE fixed_data
            SET name = ?,
                code = ?,
                sign = ?,
                year = ?,
                status = ?
            WHERE id = ?
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                number_id,
            ),
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")
        return dict(row) | {"status": bool(row["status"])}


def create_number(db_path: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a fixed_data row."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            INSERT INTO fixed_data (name, code, sign, year, status, type, xu)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id, name, code, sign AS category_key, year, status, type, xu
            """,
            (
                str(payload.get("name") or "").strip(),
                str(payload.get("code") or "").strip(),
                str(payload.get("category_key") or payload.get("sign") or "").strip(),
                str(payload.get("year") or "").strip(),
                1 if parse_bool(payload.get("status"), True) else 0,
                str(payload.get("type") or "").strip(),
                int(payload.get("xu") or 0),
            ),
        ).fetchone()
        return dict(row) | {"status": bool(row["status"])}


def delete_number(db_path: str | Path, number_id: int) -> None:
    """Delete a fixed_data row."""
    ensure_admin_tables(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "DELETE FROM fixed_data WHERE id = ? RETURNING id",
            (number_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"number_id={number_id} 不存在")
