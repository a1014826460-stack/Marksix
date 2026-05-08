"""
Rebuild PostgreSQL public.text_history_mappings from text-mode payload tables.

Rules:
1. Read all rows from public.mode_payload_tables where is_text = 1
2. Recreate public.text_history_mappings from scratch
3. Keep only id, mode_id, content, jiexi, title
4. Adapt to different source table structures by filling missing text columns with ''
5. Deduplicate inside the same mode_id by (mode_id, content, jiexi, title)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import auto_increment_primary_key  # pyright: ignore[reportMissingImports]
from db import connect  # pyright: ignore[reportMissingImports]


DEFAULT_DB_PATH = "postgresql://postgres:2225427@localhost:5432/liuhecai"
MAPPING_TABLE = "text_history_mappings"
TEXT_COLUMNS = ("content", "jiexi", "title")


def quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def get_text_mode_tables(conn: Any) -> list[dict[str, Any]]:
    if not conn.table_exists("mode_payload_tables"):
        raise ValueError("Database does not contain mode_payload_tables")

    rows = conn.execute(
        """
        SELECT modes_id, title, table_name
        FROM mode_payload_tables
        WHERE COALESCE(is_text, 0) = 1
        ORDER BY CAST(modes_id AS INTEGER)
        """
    ).fetchall()
    return [
        {
            "modes_id": int(row["modes_id"]),
            "title": str(row["title"] or ""),
            "table_name": str(row["table_name"] or f"mode_payload_{row['modes_id']}"),
        }
        for row in rows
    ]


def rebuild_mapping_table(conn: Any) -> None:
    table_name = quote_identifier(MAPPING_TABLE)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    conn.execute(
        f"""
        CREATE TABLE {table_name} (
            {auto_increment_primary_key('id', conn.engine)},
            mode_id INTEGER NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            jiexi TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        f"""
        CREATE UNIQUE INDEX idx_text_history_unique
        ON {table_name} (mode_id, content, jiexi, title)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX idx_text_history_mode_id
        ON {table_name} (mode_id)
        """
    )
    conn.commit()


def source_select_expr(columns: set[str], column_name: str) -> str:
    if column_name in columns:
        return f"COALESCE(CAST({quote_identifier(column_name)} AS TEXT), '')"
    return "''"


def insert_from_mode_table(conn: Any, modes_id: int, table_name: str) -> int:
    columns = set(conn.table_columns(table_name))
    if not any(column in columns for column in TEXT_COLUMNS):
        return 0

    where_parts = [
        f"{source_select_expr(columns, column)} != ''"
        for column in TEXT_COLUMNS
        if column in columns
    ]
    if not where_parts:
        return 0

    before_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    before_count = int(before_row["cnt"] or 0) if before_row else 0

    conn.execute(
        f"""
        INSERT INTO {quote_identifier(MAPPING_TABLE)} (mode_id, content, jiexi, title)
        SELECT DISTINCT
            {modes_id} AS mode_id,
            {source_select_expr(columns, 'content')} AS content,
            {source_select_expr(columns, 'jiexi')} AS jiexi,
            {source_select_expr(columns, 'title')} AS title
        FROM {quote_identifier(table_name)}
        WHERE {" OR ".join(where_parts)}
        ON CONFLICT (mode_id, content, jiexi, title) DO NOTHING
        """
    )
    conn.commit()

    after_row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
    ).fetchone()
    after_count = int(after_row["cnt"] or 0) if after_row else 0
    return after_count - before_count


def rebuild_text_history_mappings(db_path: str = DEFAULT_DB_PATH) -> dict[str, Any]:
    with connect(db_path) as conn:
        target_modes = get_text_mode_tables(conn)
        rebuild_mapping_table(conn)

        inserted = 0
        scanned_tables = 0
        missing_tables = 0
        skipped_without_text_columns = 0

        for mode in target_modes:
            modes_id = int(mode["modes_id"])
            table_name = str(mode["table_name"])

            if not conn.table_exists(table_name):
                missing_tables += 1
                print(f"[SKIP] modes_id={modes_id}: {table_name} does not exist")
                continue

            scanned_tables += 1
            columns = set(conn.table_columns(table_name))
            if not any(column in columns for column in TEXT_COLUMNS):
                skipped_without_text_columns += 1
                print(f"[SKIP] modes_id={modes_id}: {table_name} has no content/jiexi/title")
                continue

            delta = insert_from_mode_table(conn, modes_id, table_name)
            inserted += delta
            print(f"[OK] modes_id={modes_id}: inserted {delta} rows")

        total_row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {quote_identifier(MAPPING_TABLE)}"
        ).fetchone()
        total = int(total_row["cnt"] or 0) if total_row else 0

    return {
        "target_modes": len(target_modes),
        "scanned_tables": scanned_tables,
        "missing_tables": missing_tables,
        "skipped_without_text_columns": skipped_without_text_columns,
        "inserted": inserted,
        "total_after_dedup": total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild public.text_history_mappings from public.mode_payload_tables where is_text=1."
    )
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="PostgreSQL DSN")
    args = parser.parse_args()

    print("=" * 60)
    print("Rebuild text_history_mappings")
    print(f"Database: {args.db_path}")
    print("Source: public.mode_payload_tables where is_text=1")
    print("=" * 60)
    result = rebuild_text_history_mappings(args.db_path)
    print(result)


if __name__ == "__main__":
    main()
