"""managed_sites / site_fetch_runs tables."""

from __future__ import annotations

from typing import Any

from database.connection import quote_identifier
from database.migrations import add_column_if_missing, drop_column_if_exists


RETIRED_MANAGED_SITE_COLUMNS = (
    "start_web_id",
    "end_web_id",
    "manage_url_template",
    "modes_data_url",
    "token",
    "request_limit",
    "request_delay",
)


def _sync_site_id_related_tables(conn: Any, old_site_id: int, new_site_id: int) -> None:
    related_tables = ("site_fetch_runs", "site_prediction_modules", "scheduler_tasks", "error_logs")
    for table_name in related_tables:
        if not conn.table_exists(table_name):
            continue
        columns = set(conn.table_columns(table_name))
        if "site_id" not in columns:
            continue
        conn.execute(
            f"UPDATE {quote_identifier(table_name)} SET site_id = ? WHERE site_id = ?",
            (new_site_id, old_site_id),
        )


def align_managed_site_ids_with_web_ids(conn: Any) -> None:
    """Align existing managed_sites rows so id matches web_id when possible."""
    if not conn.table_exists("managed_sites"):
        return

    rows = conn.execute(
        """
        SELECT id, web_id, name, domain, lottery_type_id, enabled,
               blueprint_name, announcement, notes, created_at, updated_at
        FROM managed_sites
        WHERE web_id IS NOT NULL AND id <> web_id
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        old_site_id = int(row["id"])
        new_site_id = int(row["web_id"])
        conflict = conn.execute(
            "SELECT id FROM managed_sites WHERE id = ? LIMIT 1",
            (new_site_id,),
        ).fetchone()
        if conflict and int(conflict["id"]) != old_site_id:
            raise ValueError(
                f"无法将 managed_sites.id={old_site_id} 对齐到 web_id={new_site_id}：目标 ID 已被占用"
            )

        conn.execute(
            """
            INSERT INTO managed_sites (
                id, web_id, name, domain, lottery_type_id, enabled,
                blueprint_name, announcement, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_site_id,
                int(row["web_id"]),
                row["name"],
                row["domain"],
                row["lottery_type_id"],
                row["enabled"],
                row["blueprint_name"],
                row["announcement"],
                row["notes"],
                row["created_at"],
                row["updated_at"],
            ),
        )
        _sync_site_id_related_tables(conn, old_site_id, new_site_id)
        conn.execute("DELETE FROM managed_sites WHERE id = ?", (old_site_id,))

    if rows and getattr(conn, "engine", "") == "postgres":
        seq_row = conn.execute(
            "SELECT pg_get_serial_sequence('managed_sites', 'id') AS seq_name"
        ).fetchone()
        seq_name = str(seq_row["seq_name"] or "") if seq_row else ""
        if seq_name:
            max_row = conn.execute(
                "SELECT COALESCE(MAX(id), 1) AS max_id FROM managed_sites"
            ).fetchone()
            max_id = int(max_row["max_id"] or 1) if max_row else 1
            conn.execute("SELECT setval(?::regclass, ?, true)", (seq_name, max_id))


def _ensure_web_id_backfill(conn: Any) -> None:
    if not conn.table_exists("managed_sites"):
        return

    columns = set(conn.table_columns("managed_sites"))
    if "web_id" not in columns:
        return

    if "start_web_id" in columns:
        conn.execute(
            "UPDATE managed_sites SET web_id = COALESCE(web_id, start_web_id, id)"
        )
    else:
        conn.execute("UPDATE managed_sites SET web_id = COALESCE(web_id, id)")


def _drop_retired_columns(conn: Any) -> None:
    for column_name in RETIRED_MANAGED_SITE_COLUMNS:
        drop_column_if_exists(conn, "managed_sites", column_name)


def ensure_site_tables(conn: Any, pk_sql: str) -> None:
    """Create managed_sites and site_fetch_runs."""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS managed_sites (
            {pk_sql},
            web_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            domain TEXT,
            lottery_type_id INTEGER,
            enabled INTEGER NOT NULL DEFAULT 1,
            blueprint_name TEXT,
            announcement TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (lottery_type_id) REFERENCES lottery_types(id) ON DELETE SET NULL
        )
        """
    )
    add_column_if_missing(conn, "managed_sites", "domain", "TEXT")
    add_column_if_missing(conn, "managed_sites", "lottery_type_id", "INTEGER")
    add_column_if_missing(conn, "managed_sites", "announcement", "TEXT")
    add_column_if_missing(conn, "managed_sites", "web_id", "INTEGER")
    add_column_if_missing(conn, "managed_sites", "blueprint_name", "TEXT")
    add_column_if_missing(conn, "managed_sites", "notes", "TEXT")

    _ensure_web_id_backfill(conn)
    align_managed_site_ids_with_web_ids(conn)
    _drop_retired_columns(conn)

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS site_fetch_runs (
            {pk_sql},
            site_id INTEGER,
            status TEXT NOT NULL,
            message TEXT,
            modes_count INTEGER NOT NULL DEFAULT 0,
            records_count INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE SET NULL
        )
        """
    )
