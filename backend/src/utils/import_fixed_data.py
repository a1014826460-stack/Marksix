import argparse
import json
from pathlib import Path
from typing import Any

from db import connect


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXED_DATA_PATH = BACKEND_ROOT / "data" / "fixed_data.json"
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
FIXED_TABLE_NAME = "fixed_data"


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def load_fixed_data(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("data"), list):
        raise ValueError("fixed_data.json must contain a top-level data list.")
    if not all(isinstance(row, dict) for row in data["data"]):
        raise ValueError("fixed_data.json data must be a list of objects.")
    return data


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


def payload_value_to_sql(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def data_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(str(key))
    return columns


def drop_old_fixed_tables(conn: Any) -> None:
    for table_name in conn.list_tables():
        if table_name == FIXED_TABLE_NAME or table_name.startswith("fixed_"):
            conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")


def create_fixed_data_table(conn: Any, rows: list[dict[str, Any]]) -> list[str]:
    columns = data_columns(rows)
    if not columns:
        raise ValueError("fixed_data.json data is empty; cannot create fixed_data columns.")

    definitions = [
        f"{quote_identifier(column)} {infer_sql_type([row.get(column) for row in rows])}"
        for column in columns
    ]
    conn.execute(
        f"""
        CREATE TABLE {quote_identifier(FIXED_TABLE_NAME)} (
            {", ".join(definitions)}
        )
        """
    )

    if "id" in columns:
        conn.execute(
            f"CREATE INDEX idx_fixed_data_id ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('id')})"
        )
    if "sign" in columns:
        conn.execute(
            f"CREATE INDEX idx_fixed_data_sign ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('sign')})"
        )
    if "sign" in columns and "name" in columns:
        conn.execute(
            f"""
            CREATE INDEX idx_fixed_data_sign_name
            ON {quote_identifier(FIXED_TABLE_NAME)} ({quote_identifier('sign')}, {quote_identifier('name')})
            """
        )

    return columns


def insert_fixed_data_rows(
    conn: Any,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = (
        f"INSERT INTO {quote_identifier(FIXED_TABLE_NAME)} "
        f"({', '.join(quote_identifier(column) for column in columns)}) "
        f"VALUES ({placeholders})"
    )
    conn.executemany(
        insert_sql,
        [[payload_value_to_sql(row.get(column)) for column in columns] for row in rows],
    )


def import_fixed_data(
    fixed_data_path: str | Path = DEFAULT_FIXED_DATA_PATH,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    fixed_data_path = Path(fixed_data_path)
    db_path = Path(db_path)
    data = load_fixed_data(fixed_data_path)
    rows = data["data"]

    with connect(db_path) as conn:
        drop_old_fixed_tables(conn)
        columns = create_fixed_data_table(conn, rows)
        insert_fixed_data_rows(conn, columns, rows)

    print(f"imported fixed_data rows: {len(rows)}")
    print(f"columns: {', '.join(columns)}")
    print(f"database: {db_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import fixed_data.json data into one SQLite fixed_data table."
    )
    parser.add_argument(
        "--fixed-data-path",
        default=str(DEFAULT_FIXED_DATA_PATH),
        help="Path to fixed_data.json.",
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    import_fixed_data(args.fixed_data_path, args.db_path)
