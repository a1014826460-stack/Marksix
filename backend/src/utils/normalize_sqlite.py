import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = BACKEND_ROOT / "src"
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
TABLE_PREFIX = "mode_payload_"
TABLE_MAP_NAME = "mode_payload_tables"
TEXT_HISTORY_TITLES = {
    "澳门传真",
    "白小姐幽默（9肖10码 + 特码）",
    "财神爷一句中特",
    "藏宝图解析",
    "成语平特",
    "成语平特尾",
    "东南漫画解特",
    "大小肖--选四连肖--每肖选2码",
    "独家玄机",
    "独家幽默",
    "独解传真",
    "独解蓝月亮点特图",
    "赌王玄机",
    "挂牌解析",
    "管家婆解梦",
    "红字解六肖",
    "火车头",
    "解传真四字",
    "解红字肖（词7肖14码）",
    "解话中有意",
    "解今日闲情",
    "解今日闲情2",
    "解蓝月亮玄机报",
    "解六合皇",
    "解苹果报",
    "解苹果报2",
    "解蛇蛋图",
    "解释奇缘玄机",
    "解西游玄机",
    "解相入非非",
    "解寻宝图",
    "解正卦成语",
    "今日闲情",
    "金牌谜语",
    "精解跑马测字",
    "老黄历玄机",
    "另版挂牌",
    "另版管家婆解梦",
    "另版诗象",
    "梅花诗",
    "买定离手",
    "每日闲情",
    "谜语平特",
    "密码玄机",
    "民间大神解跑马",
    "跑马玄机测字(7肖14码)",
    "跑马玄机测字7肖10码",
    "平特藏宝",
    "平特二肖",
    "平特玄机",
    "破成语",
    "七字波色",
    "奇缘解析",
}

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from db import connect


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
            filename TEXT NOT NULL DEFAULT '',
            table_name TEXT NOT NULL UNIQUE,
            record_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            is_image INTEGER NOT NULL DEFAULT 0,
            is_text INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def table_record_count(conn: Any, table_name: str) -> int:
    row = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM {quote_identifier(table_name)}"
    ).fetchone()
    return int(row["cnt"] or 0) if row else 0


def resolve_mode_title(conn: Any, modes_id: int, table_name: str) -> str:
    if conn.table_exists("fetched_modes"):
        row = conn.execute(
            """
            SELECT COALESCE(NULLIF(MIN(title), ''), ?) AS title
            FROM fetched_modes
            WHERE modes_id = ?
            """,
            (table_name, modes_id),
        ).fetchone()
        if row and str(row["title"] or "").strip():
            return str(row["title"])
    return table_name


def rebuild_mode_payload_metadata(
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[int, dict[str, Any]]:
    created_at = datetime.now(timezone.utc).isoformat()
    rebuilt: dict[int, dict[str, Any]] = {}

    with connect(db_path) as conn:
        payload_tables = sorted(
            table_name
            for table_name in conn.list_tables(TABLE_PREFIX)
            if table_name != TABLE_MAP_NAME
        )

        conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(TABLE_MAP_NAME)}")
        ensure_mapping_table(conn)

        for table_name in payload_tables:
            suffix = table_name.removeprefix(TABLE_PREFIX)
            if not suffix.isdigit():
                continue

            modes_id = int(suffix)
            title = resolve_mode_title(conn, modes_id, table_name)
            record_count = table_record_count(conn, table_name)
            is_text = 1 if title in TEXT_HISTORY_TITLES else 0
            is_image = 0

            conn.execute(
                f"""
                INSERT INTO {quote_identifier(TABLE_MAP_NAME)}
                    (modes_id, title, filename, table_name, record_count, created_at, is_image, is_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    modes_id,
                    title,
                    "",
                    table_name,
                    record_count,
                    created_at,
                    is_image,
                    is_text,
                ),
            )
            rebuilt[modes_id] = {
                "title": title,
                "table_name": table_name,
                "record_count": record_count,
                "is_image": is_image,
                "is_text": is_text,
            }

    return rebuilt


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
            (modes_id, title, filename, table_name, record_count, created_at, is_image, is_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(modes_id) DO UPDATE SET
            title = excluded.title,
            filename = excluded.filename,
            table_name = excluded.table_name,
            record_count = excluded.record_count,
            created_at = excluded.created_at,
            is_image = excluded.is_image,
            is_text = excluded.is_text
        """,
        (
            mode["modes_id"],
            mode["title"],
            "",
            table_name,
            len(payloads),
            created_at,
            0,
            1 if str(mode["title"] or "") in TEXT_HISTORY_TITLES else 0,
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
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        default=False,
        help="Only rebuild mode_payload_tables metadata, keep existing mode_payload_xxx tables.",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.metadata_only:
        rebuilt = rebuild_mode_payload_metadata(args.db_path)
        for modes_id, meta in rebuilt.items():
            print(
                f"rebuilt metadata for {modes_id}: {meta['title']} "
                f"(table={meta['table_name']}, rows={meta['record_count']}, "
                f"is_text={meta['is_text']}, is_image={meta['is_image']})"
            )
    else:
        normalize_payload_tables(args.db_path)
