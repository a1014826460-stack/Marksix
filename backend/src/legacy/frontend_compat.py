"""旧站前端兼容层 — /api/kaijiang/* 和 /api/post/getList

为旧版本前端 JavaScript 提供数据接口兼容层。所有端点返回 ``{"data": [...]}`` 格式。

需求摘要
--------
- 所有端点必须返回 ``{"data": [...]}`` 或 ``{"data": {}}``（curTerm）
- ``res_code`` 与 ``res_sx`` 绝不返回 null —— 空值一律用 ``""``
- ``web`` 查询参数即站点隔离 ID，必须用于 ``web_id`` 过滤
- ``type`` 查询参数过滤 ``lottery_type``
- 空结果返回 ``{"data": []}``，不允许抛出 500
- 优先查询 ``created`` schema（PostgreSQL），回退到 ``public``
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any

from db import quote_identifier
from domains.prediction.repository import get_mode_authorization_for_web_id
from domains.legacy import repository as legacy_repository
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    created_table_exists,
    quote_qualified_identifier as quote_schema_table,
    table_column_names,
)


# ── 端点 → 输出字段映射 ──────────────────────────────────────────────
# 不在映射中的端点使用默认字段集：year, term, title, content, res_code, res_sx

_ENDPOINT_FIELDS: dict[str, tuple[str, ...]] = {
    "getJyxiao2": ("content", "res_code", "res_sx", "term", "xiao"),
    "getZyx": ("content", "res_code", "res_sx", "term"),
    "getYysx": ("content", "res_code", "res_sx", "term"),
    "getCyptwei": ("res_code", "res_sx", "term", "title"),
    "getX2jiam8": ("code", "content", "res_code", "res_sx", "term"),
    "getPtWei": ("content", "res_code", "res_sx", "term"),
    "getShama": ("content", "res_code", "res_sx", "term"),
    "getYzxj": ("jiexi", "res_code", "res_sx", "term", "xiao", "zi"),
    "getCypt": ("res_code", "res_sx", "term", "title"),
    "getNnnx": ("nan", "nv", "res_code", "res_sx", "term"),
    "getXysxma": ("code", "res_code", "res_sx", "term", "xiao"),
    "getShatou": ("content", "res_code", "res_sx", "term"),
    "getFsx": ("content", "res_code", "res_sx", "term"),
    "getDxd": ("content", "res_code", "res_sx", "term"),
    "getShaBds": ("content", "res_code", "res_sx", "term"),
    "getJuzi": ("term", "title", "res_code", "res_sx"),
    "getYjzy": ("term", "title", "content", "jiexi", "res_code", "res_sx"),
    "getSzxj": ("term", "title", "jiexi", "res_code", "res_sx"),
    "dssx": ("term", "xiao_1", "xiao_2", "res_code", "res_sx"),
    "getDsnx": ("term", "xiao_1", "xiao_2", "res_code", "res_sx"),
    "getHbnx": ("term", "hei", "bai", "res_code", "res_sx"),
    "qxbm": ("term", "xiao", "code", "ping", "res_code", "res_sx"),
    "getPmxjcz": ("year", "term", "title", "content", "image_url", "x7m14", "res_code", "res_sx"),
    "getShaXiao": ("term", "content", "res_code", "res_sx"),
}

_DEFAULT_FIELDS = ("year", "term", "title", "content", "res_code", "res_sx")
_MAX_FRONTEND_KAIJIANG_ROWS = 10

_ENDPOINT_MODE_IDS: dict[tuple[str, str], int] = {
    ("getjyxiao2", "2"): 251,
    ("getzyx", "2"): 152,
    ("getyysx", "2"): 141,
    ("getcyptwei", "2"): 336,
    ("getx2jiam8", "2"): 145,
    ("getptwei", "2"): 54,
    ("getshama", "7"): 88,
    ("getyzxj", "6/12"): 295,
    ("getcypt", "2"): 39,
    ("getnnnx", "4"): 24,
    ("getxysxma", "9/8"): 151,
    ("getshatou", "1"): 41,
    ("getfsx", "2"): 157,
    ("getdxd", "2"): 158,
    ("getshabds", "1"): 159,
}

_PMXJCZ_ALLOWED_ZODIACS = ("鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪")
_PMXJCZ_X7M14_PATTERN = re.compile(
    rf"^({'|'.join(_PMXJCZ_ALLOWED_ZODIACS)})\|\d{{2}},\d{{2}}$"
)


# ── 表名解析 ──────────────────────────────────────────────────────────

def _resolve_table_name(conn: Any, num: Any) -> str:
    """根据 ``num`` 参数解析对应的 ``mode_payload_*`` 表名。

    解析顺序：
    1. 若 ``num`` 可转为整数，在 ``mode_payload_tables`` 中按 ``modes_id`` 查找
    2. 直接尝试 ``mode_payload_{num}``
    3. 均不存在则返回空字符串

    Args:
        conn: ``ConnectionAdapter`` 实例
        num: 查询参数，可能为整数 mode_id 或特殊字符串

    Returns:
        str: 解析到的表名；未找到则返回 ``""``
    """
    # 0) 先尝试直表名，避免 mode_payload_tables 元数据误绑时串到别的玩法表
    raw_num = str(num).strip()
    if raw_num:
        direct_table_name = f"mode_payload_{raw_num}"
        if conn.table_exists(direct_table_name):
            return direct_table_name

    # 1) 尝试 mode_payload_tables 映射
    try:
        modes_id = int(str(num).strip())
        if modes_id > 0 and conn.table_exists("mode_payload_tables"):
            row = conn.execute(
                "SELECT table_name FROM mode_payload_tables WHERE modes_id = ?",
                (modes_id,),
            ).fetchone()
            if row:
                table_name = str(row["table_name"] or "").strip()
                if table_name and conn.table_exists(table_name):
                    return table_name
    except (ValueError, TypeError):
        pass

    # 2) 直接构造表名
    if not raw_num:
        return ""
    table_name = f"mode_payload_{raw_num}"
    if conn.table_exists(table_name):
        return table_name

    return ""


def _resolve_endpoint_table_name(conn: Any, endpoint: str, num: Any) -> str:
    """Resolve frontend endpoint requests to the correct payload table."""
    normalized_num = str(num).strip()
    mapped_mode_id = _ENDPOINT_MODE_IDS.get((endpoint.strip().lower(), normalized_num))
    if mapped_mode_id is not None:
        return _resolve_table_name(conn, mapped_mode_id)
    return _resolve_table_name(conn, num)


def _resolve_endpoint_mode_id(conn: Any, endpoint: str, num: Any) -> int | None:
    """Resolve the actual mode ID behind a legacy endpoint request."""
    normalized_num = str(num).strip()
    mapped_mode_id = _ENDPOINT_MODE_IDS.get((endpoint.strip().lower(), normalized_num))
    if mapped_mode_id is not None:
        return int(mapped_mode_id)
    try:
        mode_id = int(normalized_num)
    except (TypeError, ValueError):
        return None
    return mode_id if mode_id > 0 else None


# ── 表列名读取（兼容 SQLite / PostgreSQL）────────────────────────────

def _get_table_columns(conn: Any, table_name: str) -> set[str]:
    """读取表的列名集合，兼容 SQLite 与 PostgreSQL。

    Args:
        conn: ``ConnectionAdapter`` 实例
        table_name: 表名

    Returns:
        set[str]: 列名集合
    """
    if not conn.table_exists(table_name):
        return set()
    engine = getattr(conn, "engine", "sqlite")
    if engine == "postgres":
        # PostgreSQL: 查询 information_schema.columns
        rows = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            (table_name,),
        ).fetchall()
        return {str(r["column_name"]) for r in rows}
    # SQLite: 使用 PRAGMA
    rows = conn.execute(
        f"PRAGMA table_info({quote_identifier(table_name)})"
    ).fetchall()
    return {str(r[1]) for r in rows}


# ── 排序 SQL ──────────────────────────────────────────────────────────

def _build_order_clause(columns: set[str]) -> str:
    """按 year DESC, term DESC 构造排序子句。"""
    parts: list[str] = []
    for col in ("year", "term"):
        if col in columns:
            parts.append(
                "CAST(COALESCE(NULLIF(TRIM(CAST("
                f"{quote_identifier(col)} AS TEXT)), ''), '0') AS INTEGER) DESC"
            )
    return f" ORDER BY {', '.join(parts)}" if parts else ""


# ── 过滤条件 ──────────────────────────────────────────────────────────

def _build_web_type_filters(
    columns: set[str],
    web_id: int | None,
    type_val: int | None,
) -> tuple[list[str], list[Any]]:
    """构造 web_id / type 过滤条件。

    Args:
        columns: 表列名集合
        web_id: 站点 ID（对应 web_id 或 web 列）
        type_val: 彩种类型（对应 type 列）

    Returns:
        tuple[list[str], list[Any]]: (WHERE 子句列表, 参数列表)
    """
    filters: list[str] = []
    params: list[Any] = []

    # web_id 优先，其次 web
    web_col = "web_id" if "web_id" in columns else ("web" if "web" in columns else "")
    if web_col and web_id is not None:
        filters.append(
            "CAST(COALESCE(NULLIF(TRIM(CAST("
            f"{quote_identifier(web_col)} AS TEXT)), ''), '0') AS INTEGER) = ?"
        )
        params.append(int(web_id))

    if type_val is not None and "type" in columns:
        filters.append(
            "CAST(COALESCE(NULLIF(TRIM(CAST("
            f"{quote_identifier('type')} AS TEXT)), ''), '0') AS INTEGER) = ?"
        )
        params.append(int(type_val))

    return filters, params


# ── 数据查询 ──────────────────────────────────────────────────────────

def _query_mode_payload_table(
    conn: Any,
    table_name: str,
    web_id: int | None,
    type_val: int | None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """从指定的 mode_payload 表中按 web_id / type 过滤查询所有行。

    Args:
        conn: ``ConnectionAdapter`` 实例
        table_name: 表名
        web_id: 站点 ID 过滤
        type_val: 彩种类型过滤

    Returns:
        list[dict[str, Any]]: 查询到的行列表
    """
    if not table_name or not conn.table_exists(table_name):
        return []

    columns = _get_table_columns(conn, table_name)
    if not columns:
        return []

    filters, params = _build_web_type_filters(columns, web_id, type_val)
    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    order_clause = _build_order_clause(columns)
    limit_clause = ""
    if limit is not None and limit > 0:
        limit_clause = " LIMIT ?"
        params.append(int(limit))

    sql = f"SELECT * FROM {quote_identifier(table_name)}{where_clause}{order_clause}{limit_clause}"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def _query_created_schema(
    conn: Any,
    table_name: str,
    web_id: int | None,
    type_val: int | None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询 ``created`` schema 中的对应表。

    仅 PostgreSQL 连接支持此操作。不支持时返回空列表。

    Args:
        conn: ``ConnectionAdapter`` 实例
        table_name: 基础表名
        web_id: 站点 ID 过滤
        type_val: 彩种类型过滤

    Returns:
        list[dict[str, Any]]: created schema 中的行
    """
    engine = getattr(conn, "engine", "sqlite")
    if engine != "postgres":
        return []

    # created_table_exists 内部会校验表名格式（mode_payload_{数字}），
    # 非标准格式（如 mode_payload_yqmtm）会引发 ValueError，此时直接回退到 public。
    try:
        if not created_table_exists(conn, table_name):
            return []
    except ValueError:
        return []

    try:
        target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    except Exception:
        return []

    if not target_columns:
        return []

    filters, params = _build_web_type_filters(target_columns, web_id, type_val)
    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""
    order_clause = _build_order_clause(target_columns)
    limit_clause = ""
    if limit is not None and limit > 0:
        limit_clause = " LIMIT ?"
        params.append(int(limit))

    table_ref = quote_schema_table(CREATED_SCHEMA_NAME, table_name)
    sql = f"SELECT * FROM {table_ref}{where_clause}{order_clause}{limit_clause}"
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def _load_mode_payload_rows(
    conn: Any,
    table_name: str,
    web_id: int | None,
    type_val: int | None,
    limit: int = _MAX_FRONTEND_KAIJIANG_ROWS,
) -> list[dict[str, Any]]:
    """加载模式负载数据行，优先 ``created`` schema，回退 ``public``。

    Args:
        conn: ``ConnectionAdapter`` 实例
        table_name: 基础表名
        web_id: 站点 ID 过滤
        type_val: 彩种类型过滤

    Returns:
        list[dict[str, Any]]: 合并去重后的行（created 优先）
    """
    preferred_rows = _query_created_schema(
        conn,
        table_name,
        web_id,
        type_val,
        limit=max(limit * 2, limit),
    )
    fallback_rows = _query_mode_payload_table(
        conn,
        table_name,
        web_id,
        type_val,
        limit=max(limit * 3, limit),
    )

    # 按 (year, term) 去重，created 优先
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []

    for row in preferred_rows + fallback_rows:
        key = (str(row.get("year") or "").strip(), str(row.get("term") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)

    # 保持 year/term 降序
    def _safe_int(value: Any) -> int:
        try:
            s = str(value).strip() if value is not None else ""
            return int(s) if s else 0
        except (ValueError, TypeError):
            return 0

    merged.sort(key=lambda r: (_safe_int(r.get("year")), _safe_int(r.get("term"))), reverse=True)
    return merged[: max(1, int(limit))]


# ── 结果格式化 ────────────────────────────────────────────────────────

def _sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    """确保 ``res_code`` 和 ``res_sx`` 不为 None。

    Args:
        row: 原始行字典

    Returns:
        dict[str, Any]: 已消毒的行字典
    """
    sanitized = dict(row)
    if sanitized.get("res_code") is None:
        sanitized["res_code"] = ""
    if sanitized.get("res_sx") is None:
        sanitized["res_sx"] = ""
    return sanitized


def _build_seeded_rng(row: dict[str, Any]) -> random.Random:
    """基于行内容生成稳定随机源，避免同一期数据在重复请求时漂移。"""
    normalized_items = [
        (str(key), "" if value is None else str(value))
        for key, value in sorted(row.items(), key=lambda item: str(item[0]))
    ]
    seed_material = json.dumps(normalized_items, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(seed_material.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _is_valid_pmxjcz_x7m14(value: Any) -> bool:
    """校验 ``x7m14`` 是否为 7 组 ``生肖|两位数,两位数`` JSON 数组。"""
    raw = str(value or "").strip()
    if not raw:
        return False

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False

    if not isinstance(parsed, list) or len(parsed) != 7:
        return False

    seen_zodiacs: set[str] = set()
    seen_numbers: set[str] = set()
    for item in parsed:
        if not isinstance(item, str):
            return False
        candidate = item.strip()
        if not _PMXJCZ_X7M14_PATTERN.fullmatch(candidate):
            return False
        zodiac, numbers = candidate.split("|", 1)
        number_values = numbers.split(",")
        if zodiac in seen_zodiacs:
            return False
        if len(number_values) != 2 or number_values[0] == number_values[1]:
            return False
        if any(number in seen_numbers for number in number_values):
            return False
        seen_zodiacs.add(zodiac)
        seen_numbers.update(number_values)
    return True


def _generate_pmxjcz_x7m14(row: dict[str, Any]) -> str:
    """为 ``getPmxjcz`` 生成稳定随机的 ``x7m14``。"""
    rng = _build_seeded_rng(row)
    zodiacs = rng.sample(list(_PMXJCZ_ALLOWED_ZODIACS), 7)
    numbers = rng.sample(range(1, 50), 14)
    payload = [
        f"{zodiac}|{numbers[index * 2]:02d},{numbers[index * 2 + 1]:02d}"
        for index, zodiac in enumerate(zodiacs)
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _normalize_pmxjcz_row(row: dict[str, Any]) -> dict[str, Any]:
    """确保 ``getPmxjcz`` 行满足旧前端的固定字段约束。"""
    normalized = dict(row)

    year = str(normalized.get("year") or "").strip() or "0"
    term = str(normalized.get("term") or "").strip() or "0"
    title = str(normalized.get("title") or "").strip()
    content = str(normalized.get("content") or "").strip()

    if not title and content:
        title = content[:12]
    if not content and title:
        content = title
    if not title:
        title = f"{year}年{term}期平特梅花"
    if not content:
        content = f"{year}年{term}期参考资料，仅供交流。"

    normalized["year"] = year
    normalized["term"] = term
    normalized["title"] = title
    normalized["content"] = content

    if not _is_valid_pmxjcz_x7m14(normalized.get("x7m14")):
        normalized["x7m14"] = _generate_pmxjcz_x7m14(normalized)

    return normalized


def _parse_json_object(value: Any) -> dict[str, Any] | None:
    raw = str(value or "").strip()
    if not raw or not raw.startswith("{"):
        return None

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    return parsed if isinstance(parsed, dict) else None


def _parse_json_array(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _normalize_nnnx_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    parsed_object = (
        _parse_json_object(normalized.get("content"))
        or _parse_json_object(normalized.get("xiao"))
        or _parse_json_object(normalized.get("nan"))
    )
    parsed_array = _parse_json_array(normalized.get("content"))

    nan = str(normalized.get("nan") or "").strip()
    nv = str(normalized.get("nv") or "").strip()

    if parsed_object:
        nan = nan or str(
            parsed_object.get("nan")
            or parsed_object.get("nanx")
            or parsed_object.get("nan_sx")
            or parsed_object.get("xiao_1")
            or "",
        ).strip()
        nv = nv or str(
            parsed_object.get("nv")
            or parsed_object.get("nvx")
            or parsed_object.get("nv_sx")
            or parsed_object.get("xiao_2")
            or "",
        ).strip()

    if (not nan or not nv) and len(parsed_array) >= 2:
        nan = nan or parsed_array[0].strip()
        nv = nv or parsed_array[1].strip()

    normalized["nan"] = nan
    normalized["nv"] = nv
    return normalized


def _normalize_xysxma_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    parsed_object = (
        _parse_json_object(normalized.get("content"))
        or _parse_json_object(normalized.get("xiao"))
        or _parse_json_object(normalized.get("code"))
    )
    parsed_array = _parse_json_array(normalized.get("content"))

    code = str(normalized.get("code") or "").strip()
    xiao = str(normalized.get("xiao") or "").strip()

    if parsed_object:
        code = code or str(
            parsed_object.get("code")
            or parsed_object.get("codes")
            or parsed_object.get("code_list")
            or "",
        ).strip()
        xiao = xiao or str(
            parsed_object.get("xiao")
            or parsed_object.get("sx")
            or parsed_object.get("zodiac")
            or "",
        ).strip()

    if parsed_array:
        xiao_values: list[str] = []
        code_values: list[str] = []
        for item in parsed_array:
            name, _, codes = item.partition("|")
            normalized_codes = codes.replace(".", ",").strip()
            if name.strip():
                xiao_values.append(name.strip())
            if normalized_codes:
                code_values.append(normalized_codes)
        xiao = xiao or ",".join(xiao_values)
        code = code or ",".join(code_values)

    normalized["code"] = code
    normalized["xiao"] = xiao
    return normalized


def _pick_fields(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """从行中提取指定字段，缺失字段用空字符串填充。

    Args:
        row: 原始行字典
        fields: 需要输出的字段名元组

    Returns:
        dict[str, Any]: 仅含指定字段的字典
    """
    result: dict[str, Any] = {}
    for field_name in fields:
        value = row.get(field_name)
        # res_code / res_sx 绝不为 null
        if field_name in ("res_code", "res_sx") and value is None:
            value = ""
        elif value is None:
            value = ""
        if field_name != "id":
            value = str(value)
        result[field_name] = value
    return result


def _format_rows(
    rows: list[dict[str, Any]],
    endpoint: str,
) -> list[dict[str, Any]]:
    """按端点指定的字段映射格式化行列表。

    Args:
        rows: 已消毒的行列表
        endpoint: 端点名称（用于查找字段映射）

    Returns:
        list[dict[str, Any]]: 格式化后的行列表
    """
    fields = _ENDPOINT_FIELDS.get(endpoint, _DEFAULT_FIELDS)
    formatted_rows: list[dict[str, Any]] = []
    for row in rows:
        prepared_row = _normalize_pmxjcz_row(row) if endpoint == "getPmxjcz" else row
        if endpoint == "getNnnx":
            prepared_row = _normalize_nnnx_row(prepared_row)
        elif endpoint == "getXysxma":
            prepared_row = _normalize_xysxma_row(prepared_row)
        formatted_rows.append(_pick_fields(prepared_row, fields))
    return formatted_rows


# ── curTerm ────────────────────────────────────────────────────────────

def _handle_cur_term(query: dict, conn: Any) -> dict:
    """处理 ``curTerm`` 端点 —— 返回最新已开奖期号。

    Args:
        query: 解析后的查询参数字典
        conn: ``ConnectionAdapter`` 实例

    Returns:
        dict: ``{"data": {"term": "269"}}`` 格式
    """
    lottery_type_id = 1
    raw_type = query.get("type", [None])[0]
    if raw_type is not None and str(raw_type).strip():
        try:
            lottery_type_id = int(str(raw_type).strip())
        except (ValueError, TypeError):
            pass

    row = conn.execute(
        """
        SELECT term
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND is_opened = 1
        ORDER BY year DESC, term DESC, id DESC
        LIMIT 1
        """,
        (lottery_type_id,),
    ).fetchone()

    if not row:
        return {"data": {"term": ""}}

    return {"data": {"term": str(row["term"] or "")}}


# ── 标准 kaijiang 端点 ─────────────────────────────────────────────────

def _handle_standard_kaijiang(endpoint: str, query: dict, conn: Any) -> dict:
    """处理标准 ``/api/kaijiang/*`` 端点（除 curTerm 外）。

    解析 ``web``、``type``、``num`` 参数，查询对应 mode_payload 表。

    Args:
        endpoint: 端点名称（如 ``getShaXiao``）
        query: 解析后的查询参数字典
        conn: ``ConnectionAdapter`` 实例

    Returns:
        dict: ``{"data": [...]}`` 格式
    """
    # 解析参数
    raw_web = query.get("web", [None])[0]
    raw_type = query.get("type", [None])[0]
    raw_num = query.get("num", [None])[0]

    web_id: int | None = None
    if raw_web is not None and str(raw_web).strip():
        try:
            web_id = int(str(raw_web).strip())
        except (ValueError, TypeError):
            pass

    type_val: int | None = None
    if raw_type is not None and str(raw_type).strip():
        try:
            type_val = int(str(raw_type).strip())
        except (ValueError, TypeError):
            pass

    if raw_num is None or str(raw_num).strip() == "":
        return {"data": []}

    mode_id = _resolve_endpoint_mode_id(conn, endpoint, raw_num)
    authorization = (
        get_mode_authorization_for_web_id(conn, web_id=web_id, mode_id=mode_id)
        if web_id is not None and mode_id is not None
        else None
    )
    if web_id is not None and (mode_id is None or authorization is False):
        return {"data": []}

    # 解析表名
    table_name = _resolve_endpoint_table_name(conn, endpoint, raw_num)
    if not table_name:
        return {"data": []}

    # 查询数据
    rows = _load_mode_payload_rows(
        conn,
        table_name,
        web_id,
        type_val,
        limit=_MAX_FRONTEND_KAIJIANG_ROWS,
    )

    # 消毒
    rows = [_sanitize_row(row) for row in rows]

    # 格式化
    formatted = _format_rows(rows, endpoint)

    return {"data": formatted}


# ── /api/post/getList ──────────────────────────────────────────────────

def _handle_post_get_list(query: dict, conn: Any) -> dict:
    """处理 ``/api/post/getList`` 端点 —— 返回旧站图片资源列表。

    默认过滤：``type=3``、``web=4``、``pc=305``。

    Args:
        query: 解析后的查询参数字典
        conn: ``ConnectionAdapter`` 实例

    Returns:
        dict: ``{"data": [...]}`` 格式
    """
    raw_pc = query.get("pc", ["305"])[0]
    raw_web = query.get("web", ["4"])[0]
    raw_type = query.get("type", ["3"])[0]

    pc = 305
    try:
        pc = int(str(raw_pc).strip())
    except (ValueError, TypeError):
        pass

    web_id = 4
    try:
        web_id = int(str(raw_web).strip())
    except (ValueError, TypeError):
        pass

    type_val = 3
    try:
        type_val = int(str(raw_type).strip())
    except (ValueError, TypeError):
        pass

    return {
        "data": legacy_repository.list_frontend_post_images(
            conn,
            pc=pc,
            web_id=web_id,
            type_value=type_val,
        )
    }


# ── 公开入口 ───────────────────────────────────────────────────────────

def handle_frontend_kaijiang_api(path: str, query: dict, conn: Any) -> dict:
    """路由 ``/api/kaijiang/*`` 请求。

    根据路径末尾的端点名称分派到对应处理器。

    Args:
        path: 请求路径，如 ``/api/kaijiang/getShaXiao``
        query: 解析后的查询参数字典，值为 ``list[str]``
        conn: ``ConnectionAdapter`` 实例

    Returns:
        dict: 始终为 ``{"data": [...]}`` 或 ``{"data": {}}`` 格式
    """
    # 提取端点名称：/api/kaijiang/getShaXiao → getShaXiao
    endpoint = path.rsplit("/", 1)[-1].strip()
    if not endpoint or endpoint == "kaijiang":
        return {"data": []}

    endpoint_lower = endpoint.lower()

    # curTerm 特殊处理
    if endpoint_lower == "curterm":
        return _handle_cur_term(query, conn)

    # 标准模式：解析 web/type/num 并查询 mode_payload 表
    return _handle_standard_kaijiang(endpoint, query, conn)


def handle_frontend_post_api(path: str, query: dict, conn: Any) -> dict:
    """路由 ``/api/post/getList`` 请求。

    Args:
        path: 请求路径，如 ``/api/post/getList``
        query: 解析后的查询参数字典，值为 ``list[str]``
        conn: ``ConnectionAdapter`` 实例

    Returns:
        dict: ``{"data": [...]}`` 格式
    """
    # 目前仅处理 getList
    if "getList" in path:
        return _handle_post_get_list(query, conn)

    return {"data": []}
