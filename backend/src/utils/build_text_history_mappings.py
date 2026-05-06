"""Build historical text-to-result mappings from normalized mode payload tables.

文本类玩法没有稳定的语义解析规则，例如“四字词语”“谜语”“玄机”等内容通常
依赖人工联想。这里不尝试解释文本含义，只把历史中已经出现过的
`文本内容 -> 当期特码号码/特码生肖` 关系沉淀到 SQLite，供预测时随机抽取。
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db import auto_increment_primary_key, connect


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_ROOT / "data" / "lottery_modes.sqlite3"
MAPPING_TABLE_NAME = "text_history_mappings"
TEXT_COLUMNS = ("content", "title", "jiexi")
PAYLOAD_COLUMNS = ("title", "content", "jiexi", "code")
ZODIAC_ALIASES = {
    "龍": "龙",
    "馬": "马",
    "雞": "鸡",
    "豬": "猪",
}


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def normalize_zodiac(value: str) -> str:
    value = str(value or "").strip()
    return ZODIAC_ALIASES.get(value, value)


def special_code_from_res_code(res_code: str) -> str:
    codes = [code.strip().zfill(2) for code in str(res_code or "").split(",") if code.strip()]
    return codes[-1] if codes else ""


def special_zodiac_from_res_sx(res_sx: str) -> str:
    values = [value.strip() for value in str(res_sx or "").split(",") if value.strip()]
    return normalize_zodiac(values[-1]) if values else ""


def table_exists(conn: Any, table_name: str) -> bool:
    return conn.table_exists(table_name)


def table_columns(conn: Any, table_name: str) -> tuple[str, ...]:
    return conn.table_columns(table_name)


def ensure_mapping_table(conn: Any, rebuild: bool) -> None:
    if rebuild:
        conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(MAPPING_TABLE_NAME)}")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quote_identifier(MAPPING_TABLE_NAME)} (
            {auto_increment_primary_key('id', conn.engine)},
            modes_id INTEGER NOT NULL,
            source_title TEXT NOT NULL,
            source_table TEXT NOT NULL,
            text_column TEXT NOT NULL,
            text_content TEXT NOT NULL,
            special_code TEXT NOT NULL,
            special_zodiac TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            first_year INTEGER,
            first_term INTEGER,
            last_year INTEGER,
            last_term INTEGER,
            occurrence_count INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_text_history_mapping_unique
        ON {quote_identifier(MAPPING_TABLE_NAME)}
        (modes_id, text_column, text_content, special_code, special_zodiac)
        """
    )
    conn.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_text_history_mapping_lookup
        ON {quote_identifier(MAPPING_TABLE_NAME)}
        (modes_id, text_column, special_zodiac)
        """
    )


def load_mode_tables(conn: Any) -> list[Any]:
    if not table_exists(conn, "mode_payload_tables"):
        raise ValueError("mode_payload_tables does not exist. Run normalize_sqlite.py first.")

    return conn.execute(
        """
        SELECT modes_id, title, table_name
        FROM mode_payload_tables
        ORDER BY CAST(modes_id AS INTEGER)
        """
    ).fetchall()


def build_payload(row: Any, columns: tuple[str, ...]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for column in PAYLOAD_COLUMNS:
        if column in columns and row[column] not in (None, ""):
            payload[column] = row[column]
    return payload


def upsert_mapping(
    conn: Any,
    *,
    modes_id: int,
    source_title: str,
    source_table: str,
    text_column: str,
    text_content: str,
    special_code: str,
    special_zodiac: str,
    payload_json: str,
    year: int | None,
    term: int | None,
    timestamp: str,
) -> None:
    existing = conn.execute(
        f"""
        SELECT id, first_year, first_term, last_year, last_term, occurrence_count
        FROM {quote_identifier(MAPPING_TABLE_NAME)}
        WHERE modes_id = ?
          AND text_column = ?
          AND text_content = ?
          AND special_code = ?
          AND special_zodiac = ?
        """,
        (modes_id, text_column, text_content, special_code, special_zodiac),
    ).fetchone()
    if existing:
        first_year = existing["first_year"]
        first_term = existing["first_term"]
        last_year = existing["last_year"]
        last_term = existing["last_term"]

        # 同一文本可能在不同期重复出现；保留最早和最近一次出现位置，便于后续审计。
        if year is not None and term is not None:
            if first_year is None or (year, term) < (int(first_year), int(first_term or 0)):
                first_year, first_term = year, term
            if last_year is None or (year, term) > (int(last_year), int(last_term or 0)):
                last_year, last_term = year, term

        conn.execute(
            f"""
            UPDATE {quote_identifier(MAPPING_TABLE_NAME)}
            SET payload_json = ?,
                first_year = ?,
                first_term = ?,
                last_year = ?,
                last_term = ?,
                occurrence_count = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload_json,
                first_year,
                first_term,
                last_year,
                last_term,
                int(existing["occurrence_count"] or 0) + 1,
                timestamp,
                existing["id"],
            ),
        )
        return

    conn.execute(
        f"""
        INSERT INTO {quote_identifier(MAPPING_TABLE_NAME)} (
            modes_id, source_title, source_table, text_column, text_content,
            special_code, special_zodiac, payload_json,
            first_year, first_term, last_year, last_term,
            occurrence_count, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            modes_id,
            source_title,
            source_table,
            text_column,
            text_content,
            special_code,
            special_zodiac,
            payload_json,
            year,
            term,
            year,
            term,
            timestamp,
            timestamp,
        ),
    )


def build_text_history_mappings(db_path: str | Path = DEFAULT_DB_PATH, rebuild: bool = True) -> dict[str, int]:
    db_path = Path(db_path)
    timestamp = datetime.now(UTC).isoformat()
    inserted_or_updated = 0
    scanned_tables = 0

    with connect(db_path) as conn:
        ensure_mapping_table(conn, rebuild)

        for mode in load_mode_tables(conn):
            table_name = str(mode["table_name"] or "")
            if not table_name or not table_exists(conn, table_name):
                continue

            columns = table_columns(conn, table_name)
            text_columns = [column for column in TEXT_COLUMNS if column in columns]
            if not text_columns or "res_code" not in columns:
                continue

            scanned_tables += 1
            select_columns = sorted(set(("year", "term", "res_code", "res_sx", *text_columns, *PAYLOAD_COLUMNS)) & set(columns))
            rows = conn.execute(
                f"""
                SELECT {", ".join(quote_identifier(column) for column in select_columns)}
                FROM {quote_identifier(table_name)}
                WHERE res_code IS NOT NULL AND res_code != ''
                """
            ).fetchall()

            for row in rows:
                special_code = special_code_from_res_code(row["res_code"])
                special_zodiac = special_zodiac_from_res_sx(row["res_sx"] if "res_sx" in columns else "")
                if not special_code or not special_zodiac:
                    continue

                year = int(row["year"]) if "year" in columns and str(row["year"] or "").isdigit() else None
                term = int(row["term"]) if "term" in columns and str(row["term"] or "").isdigit() else None
                payload = build_payload(row, columns)
                payload["mapped_special_code"] = special_code
                payload["mapped_special_zodiac"] = special_zodiac
                payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

                for text_column in text_columns:
                    text_content = str(row[text_column] or "").strip()
                    if not text_content:
                        continue
                    upsert_mapping(
                        conn,
                        modes_id=int(mode["modes_id"]),
                        source_title=str(mode["title"] or ""),
                        source_table=table_name,
                        text_column=text_column,
                        text_content=text_content,
                        special_code=special_code,
                        special_zodiac=special_zodiac,
                        payload_json=payload_json,
                        year=year,
                        term=term,
                        timestamp=timestamp,
                    )
                    inserted_or_updated += 1

    return {
        "scanned_tables": scanned_tables,
        "inserted_or_updated_pairs": inserted_or_updated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build SQLite text_history_mappings from normalized mode_payload tables."
    )
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="SQLite database path.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append/update existing mappings instead of rebuilding the mapping table.",
    )
    args = parser.parse_args()
    result = build_text_history_mappings(args.db_path, rebuild=not args.append)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
