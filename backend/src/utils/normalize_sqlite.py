import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db import connect


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
TABLE_PREFIX = "mode_payload_"
TABLE_MAP_NAME = "mode_payload_tables"


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalize_column_name(key: str) -> str:
    column = re.sub(r"\W+", "_", key.strip(), flags=re.ASCII).strip("_").lower()
    if not column:
        column = "value"
    if column[0].isdigit():
        column = f"field_{column}"
    return column


def payload_value_to_sql(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def infer_sql_type(values: list[Any]) -> str:
    non_empty_values = [value for value in values if value is not None and value != ""]
    if not non_empty_values:
        return "TEXT"

    if all(isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"

    if all(isinstance(value, int) and not isinstance(value, bool) for value in non_empty_values):
        return "INTEGER"

    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in non_empty_values):
        return "REAL"

    return "TEXT"


def ensure_mapping_table(conn: Any) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quote_identifier(TABLE_MAP_NAME)} (
            modes_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            table_name TEXT NOT NULL UNIQUE,
            record_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )


def get_existing_payload_tables(conn: Any) -> list[str]:
    ensure_mapping_table(conn)
    mapped_tables = [
        str(row["table_name"] if isinstance(row, dict) else row[0])
        for row in conn.execute(
            f"SELECT table_name FROM {quote_identifier(TABLE_MAP_NAME)}"
        ).fetchall()
    ]
    discovered_tables = [
        table_name
        for table_name in conn.list_tables(TABLE_PREFIX)
        if table_name != TABLE_MAP_NAME
    ]
    return sorted(set(mapped_tables + discovered_tables))


def drop_existing_payload_tables(conn: Any) -> None:
    for table_name in get_existing_payload_tables(conn):
        conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")
    conn.execute(f"DELETE FROM {quote_identifier(TABLE_MAP_NAME)}")


def load_mode_payloads(
    conn: Any,
    modes_id: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    mode = conn.execute(
        """
        SELECT
            modes_id,
            COALESCE(NULLIF(MIN(title), ''), '') AS title,
            COUNT(DISTINCT web_id) AS web_count,
            SUM(record_count) AS expected_record_count
        FROM fetched_modes
        WHERE modes_id = ?
        GROUP BY modes_id
        """,
        (modes_id,),
    ).fetchone()
    if mode is None:
        raise ValueError(f"modes_id={modes_id} does not exist in fetched_modes table.")

    rows = conn.execute(
        """
        SELECT web_id, modes_id, source_record_id, fetched_at, payload_json
        FROM fetched_mode_records
        WHERE modes_id = ?
        """,
        (modes_id,),
    ).fetchall()

    payloads: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        payload.setdefault("web_id", row["web_id"])
        payload.setdefault("modes_id", row["modes_id"])
        payload["source_record_id"] = row["source_record_id"]
        payload["fetched_at"] = row["fetched_at"]
        payloads.append(payload)

    # 这里改成 Python 侧排序，避免 SQLite json_extract 与 PostgreSQL JSON 表达式差异。
    payloads.sort(
        key=lambda item: (
            int(item.get("web_id") or 0),
            -(int(item.get("year") or 0) if str(item.get("year") or "").isdigit() else 0),
            -(int(item.get("term") or 0) if str(item.get("term") or "").isdigit() else 0),
            -(int(item.get("source_record_id") or 0) if str(item.get("source_record_id") or "").isdigit() else 0),
        )
    )

    mode_dict = dict(mode)
    mode_dict["filename"] = f"{mode_dict['modes_id']}.json"
    return mode_dict, payloads


def build_column_map(payloads: list[dict[str, Any]]) -> dict[str, str]:
    column_map: dict[str, str] = {}
    used_columns: set[str] = set()

    for payload in payloads:
        for key in payload:
            if key in column_map:
                continue

            column = normalize_column_name(key)
            candidate = column
            index = 2
            while candidate in used_columns:
                candidate = f"{column}_{index}"
                index += 1

            column_map[key] = candidate
            used_columns.add(candidate)

    return column_map


def create_mode_payload_table(
    conn: Any,
    mode: dict[str, Any],
    payloads: list[dict[str, Any]],
    created_at: str,
) -> str:
    table_name = f"{TABLE_PREFIX}{mode['modes_id']}"
    conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")

    column_map = build_column_map(payloads)
    column_definitions: list[str] = []
    for key, column in column_map.items():
        values = [payload.get(key) for payload in payloads]
        sql_type = infer_sql_type(values)
        column_definitions.append(f"{quote_identifier(column)} {sql_type}")

    if not column_definitions:
        column_definitions.append(f"{quote_identifier('id')} TEXT")

    conn.execute(
        f"""
        CREATE TABLE {quote_identifier(table_name)} (
            {", ".join(column_definitions)}
        )
        """
    )

    if payloads:
        columns = list(column_map.values())
        placeholders = ", ".join(["?"] * len(columns))
        insert_sql = (
            f"INSERT INTO {quote_identifier(table_name)} "
            f"({', '.join(quote_identifier(column) for column in columns)}) "
            f"VALUES ({placeholders})"
        )
        conn.executemany(
            insert_sql,
            [
                [payload_value_to_sql(payload.get(key)) for key in column_map]
                for payload in payloads
            ],
        )

    conn.execute(
        f"""
        INSERT INTO {quote_identifier(TABLE_MAP_NAME)}
            (modes_id, title, filename, table_name, record_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(modes_id) DO UPDATE SET
            title = excluded.title,
            filename = excluded.filename,
            table_name = excluded.table_name,
            record_count = excluded.record_count,
            created_at = excluded.created_at
        """,
        (
            mode["modes_id"],
            mode["title"],
            mode["filename"],
            table_name,
            len(payloads),
            created_at,
        ),
    )

    return table_name


def normalize_payload_tables(db_path: str | Path = DEFAULT_DB_PATH) -> dict[int, str]:
    created_at = datetime.now(timezone.utc).isoformat()

    with connect(db_path) as conn:
        ensure_mapping_table(conn)
        drop_existing_payload_tables(conn)

        if not conn.table_exists("fetched_mode_records"):
            raise ValueError("fetched_mode_records table does not exist. Run data_fetch.py first.")

        modes_ids = [
            int(row["modes_id"] if isinstance(row, dict) else row[0])
            for row in conn.execute(
                "SELECT DISTINCT modes_id FROM fetched_mode_records ORDER BY CAST(modes_id AS INTEGER)"
            ).fetchall()
        ]
        table_map: dict[int, str] = {}

        for modes_id in modes_ids:
            mode, payloads = load_mode_payloads(conn, modes_id)
            table_name = create_mode_payload_table(conn, mode, payloads, created_at)
            table_map[modes_id] = table_name
            print(
                f"created {table_name}: {mode['title']} "
                f"({mode['filename']}), {len(payloads)} rows"
            )

    return table_map


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split fetched_mode_records.payload_json into one SQLite table per modes_id."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    normalize_payload_tables(args.db_path)
