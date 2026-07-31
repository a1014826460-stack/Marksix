"""Managed site repository."""

from __future__ import annotations

from typing import Any


def _site_select_parts(conn: Any) -> tuple[str, str]:
    select_columns = ["s.*"]
    joins: list[str] = []

    if conn.table_exists("lottery_types"):
        joins.append("LEFT JOIN lottery_types l ON l.id = s.lottery_type_id")
        select_columns.append("l.name AS lottery_name")

    if conn.table_exists("site_blueprint_profiles"):
        joins.append("LEFT JOIN site_blueprint_profiles bp ON bp.blueprint_name = s.blueprint_name")
        select_columns.extend(
            [
                "bp.required_mode_ids_json AS blueprint_required_mode_ids_json",
                "bp.known_unavailable_mode_ids_json AS blueprint_known_unavailable_mode_ids_json",
                "bp.blocked_items_json AS blueprint_blocked_items_json",
            ]
        )

    return ", ".join(select_columns), " ".join(joins)


def list_all_sites(conn: Any) -> list[dict[str, Any]]:
    select_sql, join_sql = _site_select_parts(conn)
    rows = conn.execute(
        f"""
        SELECT {select_sql}
        FROM managed_sites s
        {join_sql}
        ORDER BY s.enabled DESC, s.id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def find_site_by_id(conn: Any, site_id: int) -> dict[str, Any] | None:
    select_sql, join_sql = _site_select_parts(conn)
    row = conn.execute(
        f"""
        SELECT {select_sql}
        FROM managed_sites s
        {join_sql}
        WHERE s.id = ?
        """,
        (site_id,),
    ).fetchone()
    return dict(row) if row else None


def find_site_by_domain(conn: Any, domain: str) -> dict[str, Any] | None:
    select_sql, join_sql = _site_select_parts(conn)
    row = conn.execute(
        f"""
        SELECT {select_sql}
        FROM managed_sites s
        {join_sql}
        WHERE LOWER(COALESCE(s.domain, '')) = ?
        ORDER BY s.id
        LIMIT 1
        """,
        (domain.strip().lower(),),
    ).fetchone()
    return dict(row) if row else None


def find_first_site(conn: Any) -> dict[str, Any] | None:
    select_sql, join_sql = _site_select_parts(conn)
    row = conn.execute(
        f"""
        SELECT {select_sql}
        FROM managed_sites s
        {join_sql}
        ORDER BY s.id
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def count_sites(conn: Any) -> int:
    row = conn.execute("SELECT COUNT(*) AS total FROM managed_sites").fetchone()
    return int(row["total"] or 0)


def insert_site(conn: Any, fields: dict[str, Any], now: str) -> dict[str, Any]:
    web_id = int(fields["web_id"])
    row = conn.execute(
        """
        INSERT INTO managed_sites (
            id, web_id, name, domain, lottery_type_id, enabled,
            blueprint_name, announcement, notes,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
        """,
        (
            web_id,
            web_id,
            fields["name"],
            fields["domain"],
            fields["lottery_type_id"],
            fields["enabled"],
            fields["blueprint_name"],
            fields["announcement"],
            fields["notes"],
            now,
            now,
        ),
    ).fetchone()
    return dict(row)


def update_site(conn: Any, site_id: int, fields: dict[str, Any], now: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        UPDATE managed_sites
        SET name = ?, domain = ?, lottery_type_id = ?, enabled = ?,
            web_id = ?, blueprint_name = ?,
            announcement = ?, notes = ?,
            updated_at = ?
        WHERE id = ?
        RETURNING *
        """,
        (
            fields["name"],
            fields["domain"],
            fields["lottery_type_id"],
            fields["enabled"],
            fields["web_id"],
            fields["blueprint_name"],
            fields["announcement"],
            fields["notes"],
            now,
            site_id,
        ),
    ).fetchone()
    return dict(row) if row else None


def delete_site_by_id(conn: Any, site_id: int) -> bool:
    cur = conn.execute("DELETE FROM managed_sites WHERE id = ?", (site_id,))
    return cur.rowcount > 0


def get_site_web_id(conn: Any, site_id: int) -> int | None:
    row = conn.execute("SELECT web_id FROM managed_sites WHERE id = ?", (site_id,)).fetchone()
    return int(row["web_id"]) if row and row["web_id"] is not None else None


def find_enabled_site_announcement_by_web_id(conn: Any, web_id: int) -> str:
    row = conn.execute(
        """
        SELECT announcement
        FROM managed_sites
        WHERE enabled = 1
          AND (id = ? OR web_id = ?)
        ORDER BY id
        LIMIT 1
        """,
        (web_id, web_id),
    ).fetchone()
    return str(row["announcement"] or "") if row else ""


def list_public_enabled_sites(conn: Any) -> list[dict[str, Any]]:
    """Return enabled sites with non-empty domain for public consumption.

    Only projects id, name, domain, blueprint_name — no internal columns.
    """
    rows = conn.execute(
        """
        SELECT id, name, domain, blueprint_name
        FROM managed_sites
        WHERE enabled = 1
          AND TRIM(COALESCE(domain, '')) <> ''
        ORDER BY id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def backfill_site_web_ids(conn: Any) -> None:
    conn.execute("UPDATE managed_sites SET web_id = COALESCE(web_id, id)")
