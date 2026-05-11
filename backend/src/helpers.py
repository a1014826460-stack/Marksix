"""跨模块共享工具函数 — 字符串处理、数据转换、SQL 构造、开奖映射。

从 app.py 提取，不改变任何函数签名与行为。
"""

from __future__ import annotations

from typing import Any

from db import quote_identifier
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    normalize_color_label,
    quote_qualified_identifier as quote_schema_table,
    schema_table_exists,
    table_column_names,
)


# 前端需要的站点预测模块 mode_id 清单，按展示顺序排列
REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 108, 151, 197,
)


def row_to_dict(row: Any | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "是", "启用"}


def split_csv(value: Any) -> list[str]:
    """把逗号分隔的字符串安全转成列表，去除空白项。 
    例如 "01, 02,03,, " → ["01", "02", "03"]，而不是 ["01", "02", "03", "", ""]。
    
    param 
        - value: 可能是逗号分隔的字符串，也可能是 None 或其他类型。
    return: 
        - list[str]: 去除空白项后的字符串列表。
    
    """
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_issue_part(value: Any) -> str:
    """把 year / term 统一成可比较的纯文本，避免空白字符串污染排序与匹配。"""
    return str(value or "").strip()


def parse_issue_int(value: Any) -> int | None:
    """把 year / term / type 这类期号字段安全转成整数。"""
    text = normalize_issue_part(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def sql_safe_int_expr(column_name: str) -> str:
    """构造跨 SQLite / PostgreSQL 都可用的"空串转 0 再转整数"表达式。"""
    quoted = quote_identifier(column_name)
    return (
        f"CAST(COALESCE(NULLIF(TRIM(CAST({quoted} AS TEXT)), ''), '0') AS INTEGER)"
    )


def build_mode_payload_order_clause(columns: set[str]) -> str:
    """统一 mode_payload_* 历史记录排序，避免空字符串强转整数报错。"""
    order_parts: list[str] = []
    if "year" in columns:
        order_parts.append(f"{sql_safe_int_expr('year')} DESC")
    if "term" in columns:
        order_parts.append(f"{sql_safe_int_expr('term')} DESC")
    if "source_record_id" in columns:
        order_parts.append(f"{sql_safe_int_expr('source_record_id')} DESC")
    elif "created_at" in columns:
        order_parts.append("CAST(created_at AS TEXT) DESC")
    elif "id" in columns:
        order_parts.append(f"{sql_safe_int_expr('id')} DESC")
    return f" ORDER BY {', '.join(order_parts)}" if order_parts else ""


def build_mode_payload_filters(
    columns: set[str],
    *,
    lottery_type_id: int | None = None,
    web_start: int | None = None,
    web_end: int | None = None,
    web_exact: int | None = None,
    require_result_consistency: bool = False,
) -> tuple[list[str], list[Any]]:
    """按彩种与站点来源构造 mode_payload 过滤条件。"""
    filters: list[str] = []
    params: list[Any] = []

    if lottery_type_id is not None and "type" in columns:
        filters.append(f"{sql_safe_int_expr('type')} = ?")
        params.append(int(lottery_type_id))

    web_column = "web_id" if "web_id" in columns else ("web" if "web" in columns else "")
    if web_column:
        if web_exact is not None:
            filters.append(f"{sql_safe_int_expr(web_column)} = ?")
            params.append(int(web_exact))
        elif web_start is not None and web_end is not None:
            filters.append(f"{sql_safe_int_expr(web_column)} BETWEEN ? AND ?")
            params.extend((int(web_start), int(web_end)))

    if require_result_consistency and "res_code" in columns and "res_sx" in columns:
        filters.append(
            "((COALESCE(res_code, '') != '' AND COALESCE(res_sx, '') != '') "
            "OR (COALESCE(res_code, '') = '' AND COALESCE(res_sx, '') = ''))"
        )

    return filters, params


def load_fixed_data_maps(conn: Any) -> tuple[dict[str, str], dict[str, str]]:
    """读取 fixed_data 中的生肖 / 波色映射，统一给多个公开接口复用。
    
    params:
    - conn: 数据库连接对象，必须具有 table_exists 和 execute 方法。
    returns:
    - tuple[dict[str, str], dict[str, str]]: 包含两个字典的元组，分别是：
        - zodiac_map: 号码（两位字符串）到生肖标签的映射，以及号码（整数形式）到生肖标签的映射。
        - color_map: 号码（两位字符串）到波色标签的映射，以及号码（整数形式）到波色标签的映射。
    """
    zodiac_map: dict[str, str] = {}
    color_map: dict[str, str] = {}
    if not conn.table_exists("fixed_data"):
        return zodiac_map, color_map

    for sign, target in (("生肖", zodiac_map), ("波色", color_map)):
        rows = conn.execute(
            """
            SELECT name, code
            FROM fixed_data
            WHERE sign = ?
            """,
            (sign,),
        ).fetchall()
        for row in rows:
            label = str(row["name"] or "").strip()
            if not label:
                continue
            for code in split_csv(row["code"]):
                try:
                    normalized = f"{int(str(code)):02d}"
                except ValueError:
                    continue
                target.setdefault(normalized, label)
                target.setdefault(str(int(normalized)), label)

    return zodiac_map, color_map


def color_name_to_key(value: str) -> str:
    """把中文/英文波色名统一为前端使用的英文字符串。"""
    lowered = str(value or "").strip().lower()
    if lowered in {"red", "blue", "green"}:
        return lowered
    mapping = {
        "红": "red",
        "红波": "red",
        "red波": "red",
        "蓝": "blue",
        "蓝波": "blue",
        "blue波": "blue",
        "绿": "green",
        "绿波": "green",
        "green波": "green",
    }
    return mapping.get(str(value or "").strip(), "red")


def build_draw_result_payload(
    numbers: Any,
    zodiac_map: dict[str, str],
    color_map: dict[str, str],
) -> dict[str, Any]:
    """把 lottery_draws.numbers 还原成旧表 / 新站都能复用的开奖结构。"""
    normalized_codes: list[str] = []
    zodiacs: list[str] = []
    colors: list[str] = []
    balls: list[dict[str, str]] = []

    for raw_number in split_csv(numbers):
        try:
            normalized_code = f"{int(str(raw_number)):02d}"
        except ValueError:
            continue

        zodiac = zodiac_map.get(normalized_code, "")
        color = normalize_color_label(color_map.get(normalized_code, ""))
        normalized_codes.append(normalized_code)
        zodiacs.append(zodiac)
        colors.append(color)
        balls.append(
            {
                "value": normalized_code,
                "zodiac": zodiac,
                "color": color_name_to_key(color),
            }
        )

    return {
        "res_code": ",".join(normalized_codes),
        "res_sx": ",".join(zodiacs) if any(zodiacs) else "",
        "res_color": ",".join(colors) if any(colors) else "",
        "balls": balls,
    }


def load_lottery_draw_map(
    conn: Any,
    lottery_type_id: int,
    issues: set[tuple[int, int]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """按 `year + term` 批量读取开奖状态，统一覆盖各类模块历史结果。"""
    if not issues:
        return {}

    years = sorted({year for year, _term in issues})
    terms = sorted({term for _year, term in issues})
    if not years or not terms:
        return {}

    year_placeholders = ", ".join("?" for _ in years)
    term_placeholders = ", ".join("?" for _ in terms)
    rows = conn.execute(
        f"""
        SELECT id, lottery_type_id, year, term, numbers, is_opened, next_term
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND year IN ({year_placeholders})
          AND term IN ({term_placeholders})
        ORDER BY year DESC, term DESC, id DESC
        """,
        (int(lottery_type_id), *years, *terms),
    ).fetchall()

    draw_map: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["year"]), int(row["term"]))
        draw_map.setdefault(key, dict(row))
    return draw_map


def apply_lottery_draw_overlay(
    conn: Any,
    rows: list[dict[str, Any]],
    *,
    default_lottery_type_id: int | None = None,
) -> list[dict[str, Any]]:
    """以 `public.lottery_draws` 为准修正开奖结果，并隐藏未开奖期的号码。"""
    if not rows:
        return rows

    grouped_issues: dict[int, set[tuple[int, int]]] = {}
    for row in rows:
        lottery_type_id = default_lottery_type_id or parse_issue_int(row.get("type"))
        year = parse_issue_int(row.get("year"))
        term = parse_issue_int(row.get("term"))
        if lottery_type_id is None or year is None or term is None:
            continue
        grouped_issues.setdefault(lottery_type_id, set()).add((year, term))

    if not grouped_issues:
        return rows

    zodiac_map, color_map = load_fixed_data_maps(conn)
    draw_maps = {
        lottery_type_id: load_lottery_draw_map(conn, lottery_type_id, issues)
        for lottery_type_id, issues in grouped_issues.items()
    }

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized = dict(row)
        lottery_type_id = default_lottery_type_id or parse_issue_int(row.get("type"))
        year = parse_issue_int(row.get("year"))
        term = parse_issue_int(row.get("term"))
        if lottery_type_id is None or year is None or term is None:
            normalized_rows.append(normalized)
            continue

        draw_row = draw_maps.get(lottery_type_id, {}).get((year, term))
        if not draw_row:
            normalized_rows.append(normalized)
            continue

        is_opened = bool(draw_row.get("is_opened"))
        normalized["draw_is_opened"] = is_opened
        normalized["draw_issue"] = f"{draw_row.get('year') or ''}{draw_row.get('term') or ''}"

        if not is_opened:
            normalized["res_code"] = ""
            normalized["res_sx"] = ""
            normalized["res_color"] = ""
            normalized_rows.append(normalized)
            continue

        draw_result = build_draw_result_payload(
            draw_row.get("numbers"),
            zodiac_map,
            color_map,
        )
        if draw_result["res_code"]:
            normalized["res_code"] = draw_result["res_code"]
        if draw_result["res_sx"]:
            normalized["res_sx"] = draw_result["res_sx"]
        if draw_result["res_color"]:
            normalized["res_color"] = draw_result["res_color"]
        normalized_rows.append(normalized)

    return normalized_rows


def build_mode_payload_row_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    """为 created / public 双来源记录构造去重键，保证同期期号优先采用 created。"""
    type_value = normalize_issue_part(row.get("type"))
    year = normalize_issue_part(row.get("year"))
    term = normalize_issue_part(row.get("term"))
    web_value = normalize_issue_part(row.get("web_id") or row.get("web"))
    if year or term:
        return (type_value, year, term, web_value)
    return (
        type_value,
        normalize_issue_part(row.get("source_record_id")),
        normalize_issue_part(row.get("id")),
        web_value,
    )


def merge_preferred_mode_payload_rows(
    preferred_rows: list[dict[str, Any]],
    fallback_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """合并 created / public 两套来源，保留 created 优先级并按期号去重。"""
    merged: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()

    for row in [*preferred_rows, *fallback_rows]:
        row_key = build_mode_payload_row_key(row)
        if row_key in seen_keys:
            continue
        seen_keys.add(row_key)
        merged.append(row)
        if len(merged) >= limit:
            break

    # 合并后可能因回填打破降序，重新按 year/term 降序排列
    merged.sort(
        key=lambda row: (
            _safe_issue_int(row.get("year")),
            _safe_issue_int(row.get("term")),
        ),
        reverse=True,
    )

    return merged


def _safe_issue_int(value: Any) -> int:
    """将 year/term 安全转为整数用于排序，无效值返回 0。"""
    try:
        s = str(value).strip() if value is not None else ""
        return int(s) if s else 0
    except (ValueError, TypeError):
        return 0


def load_mode_payload_rows_from_source(
    conn: Any,
    *,
    table_name: str,
    limit: int,
    schema_name: str | None = None,
    lottery_type_id: int | None = None,
    web_start: int | None = None,
    web_end: int | None = None,
    web_exact: int | None = None,
    require_result_consistency: bool = False,
) -> list[dict[str, Any]]:
    """按来源 schema 读取 mode_payload 历史记录。"""
    if schema_name:
        if getattr(conn, "engine", "") != "postgres" or not schema_table_exists(conn, schema_name, table_name):
            return []
        columns = set(table_column_names(conn, schema_name, table_name))
        table_ref = quote_schema_table(schema_name, table_name)
    else:
        if not conn.table_exists(table_name):
            return []
        columns = set(conn.table_columns(table_name))
        table_ref = quote_identifier(table_name)

    filters, params = build_mode_payload_filters(
        columns,
        lottery_type_id=lottery_type_id,
        web_start=web_start,
        web_end=web_end,
        web_exact=web_exact,
        require_result_consistency=require_result_consistency,
    )
    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    order_clause = build_mode_payload_order_clause(columns)

    rows = conn.execute(
        f"""
        SELECT *
        FROM {table_ref}
        {where_clause}
        {order_clause}
        LIMIT ?
        """,
        (*params, max(1, limit)),
    ).fetchall()
    return [dict(row) for row in rows]
