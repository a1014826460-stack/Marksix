"""Repository helpers for prediction batch generation."""

from __future__ import annotations

from typing import Any

from db import quote_identifier
from utils.created_prediction_store import CREATED_SCHEMA_NAME, table_column_names

from .models import DrawTruth


def normalize_draw_numbers(numbers: Any) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_number in str(numbers or "").split(","):
        text = raw_number.strip()
        if not text:
            continue
        try:
            value = int(text)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 49:
            normalized.append(f"{value:02d}")
    return tuple(normalized)


def list_opened_draws_in_issue_range(
    conn: Any,
    *,
    lottery_type_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year ASC, term ASC, id ASC
        """,
        (int(lottery_type_id),),
    ).fetchall()

    draws: list[dict[str, Any]] = []
    for row in rows:
        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        current = (year, term)
        if current < start_issue or current > end_issue:
            continue
        numbers = normalize_draw_numbers(row["numbers"])
        if len(numbers) < 7:
            continue
        draws.append({"year": year, "term": term, "numbers_str": ",".join(numbers)})
    return draws


def find_latest_opened_draw_before_issue(
    conn: Any,
    *,
    lottery_type_id: int,
    target_issue: tuple[int, int],
) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT year, term, numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year DESC, term DESC, id DESC
        """,
        (int(lottery_type_id),),
    ).fetchall()

    for row in rows:
        year = int(row["year"] or 0)
        term = int(row["term"] or 0)
        if (year, term) >= target_issue:
            continue
        numbers = normalize_draw_numbers(row["numbers"])
        if len(numbers) < 7:
            continue
        return {"year": year, "term": term, "numbers_str": ",".join(numbers)}
    return None


def list_unopened_issue_keys(conn: Any, *, lottery_type_id: int) -> dict[tuple[int, int], bool]:
    rows = conn.execute(
        """
        SELECT year, term, is_opened
        FROM lottery_draws
        WHERE lottery_type_id = ? AND is_opened = 0
        """,
        (int(lottery_type_id),),
    ).fetchall()
    return {
        (int(row["year"] or 0), int(row["term"] or 0)): True
        for row in rows
    }


def get_future_draw_truth(
    conn: Any,
    *,
    lottery_type_id: int,
    year: int,
    term: int,
    zodiac_map: dict[str, str],
    color_map: dict[str, str],
) -> DrawTruth | None:
    row = conn.execute(
        """
        SELECT numbers
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND year = ?
          AND term = ?
          AND is_opened = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (int(lottery_type_id), int(year), int(term)),
    ).fetchone()
    if not row:
        return None
    numbers = normalize_draw_numbers(row["numbers"])
    if len(numbers) < 7:
        return None
    special_code = numbers[-1]
    return DrawTruth(
        numbers=numbers,
        special_code=special_code,
        special_zodiac=str(zodiac_map.get(special_code) or ""),
        special_color=str(color_map.get(special_code) or ""),
    )


def list_enabled_site_prediction_modules(
    conn: Any,
    *,
    site_id: int,
    mechanism_keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    requested_keys = [str(item) for item in mechanism_keys or [] if str(item).strip()]
    query = """
        SELECT id, mechanism_key, mode_id, status, sort_order
        FROM site_prediction_modules
        WHERE site_id = ? AND status = 1
    """
    params: list[Any] = [int(site_id)]
    if requested_keys:
        query += f" AND mechanism_key IN ({', '.join('?' for _ in requested_keys)})"
        params.extend(requested_keys)
    query += " ORDER BY sort_order, id"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def load_recent_created_rows(
    conn: Any,
    *,
    table_name: str,
    lottery_type: int,
    site_web_id: int,
    mode_id: int,
) -> list[dict[str, Any]]:
    try:
        created_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
        selected_columns = [column for column in ("title", "content", "jiexi") if column in created_columns]
        if "content" not in created_columns or not selected_columns:
            return []
        selected_sql = ", ".join(quote_identifier(column) for column in selected_columns)
        table_ref = f'{quote_identifier(CREATED_SCHEMA_NAME)}.{quote_identifier(table_name)}'
        rows = conn.execute(
            f"""
            SELECT {selected_sql}
            FROM {table_ref}
            WHERE type = ? AND web = ? AND modes_id = ?
            ORDER BY year DESC, term DESC
            LIMIT 10
            """,
            (str(lottery_type), str(site_web_id), int(mode_id)),
        ).fetchall()
        return [{column: row[column] for column in selected_columns} for row in rows]
    except Exception:
        conn.rollback()
        return []


def load_text_history_candidate_rows(
    conn: Any,
    *,
    table_name: str,
    mode_id: int,
    limit: int = 50,
) -> list[Any]:
    if int(mode_id or 0) <= 0 or not conn.table_exists(table_name):
        return []

    columns = set(conn.table_columns(table_name))
    mode_column = "mode_id" if "mode_id" in columns else ("modes_id" if "modes_id" in columns else "")
    if not mode_column:
        return []

    return conn.execute(
        f"""
        SELECT *
        FROM {quote_identifier(table_name)}
        WHERE {quote_identifier(mode_column)} = ?
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (int(mode_id), int(limit)),
    ).fetchall()
