"""统一管理本地预测结果在 PostgreSQL `created` schema 下的落库逻辑。

设计目标：
1. 预测结果不再直接写入 `public.mode_payload_{mode_id}` 原始历史表。
2. 所有本地生成数据统一写入 `created.mode_payload_{mode_id}`。
3. 自动补齐 `id` 列，格式为 `c` 前缀加数字，例如 `c2333`。
4. 自动补齐 `created_at` 列，记录该条生成数据的创建时间。
5. 针对同一 `type + year + term + web/web_id` 的记录执行更新而非重复插入。
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

from db import utc_now  # noqa: E402


SOURCE_SCHEMA_NAME = "public"
CREATED_SCHEMA_NAME = "created"
MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\d+$")
THREE_PERIOD_SPECIAL_MODE_ID = 197
FIXED_DATA_ZODIAC_SIGN = "生肖"
FIXED_DATA_COLOR_SIGN = "波色"


@dataclass(frozen=True)
class TableColumn:
    """描述 PostgreSQL 表中的一列。

    Args:
        name: 列名。
        sql_type: PostgreSQL 原始列类型定义，例如 `text`、`integer`、`character varying(255)`。

    Returns:
        TableColumn: 不可变列定义对象。
    """

    name: str
    sql_type: str


def quote_identifier(identifier: str) -> str:
    """安全引用 PostgreSQL 标识符。

    Args:
        identifier: 表名、列名或 schema 名。

    Returns:
        str: 已用双引号包裹并完成转义的标识符。
    """

    return '"' + str(identifier).replace('"', '""') + '"'


def quote_qualified_identifier(schema_name: str, table_name: str) -> str:
    """构造 `schema.table` 形式的安全引用名称。

    Args:
        schema_name: schema 名称。
        table_name: 表名称。

    Returns:
        str: 形如 `"schema"."table"` 的安全 SQL 片段。
    """

    return f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"


utc_now_iso = utc_now  # 兼容别名，保留旧名称引用


def ensure_postgres_connection(conn: Any) -> None:
    """确保当前连接目标为 PostgreSQL。

    Args:
        conn: 数据库连接对象，支持项目的 `ConnectionAdapter` 或 `psycopg.Connection`。

    Returns:
        None: 仅做校验。

    Raises:
        ValueError: 当连接并非 PostgreSQL 时抛出。
    """

    engine = getattr(conn, "engine", "postgres")
    if engine != "postgres":
        raise ValueError("created schema 预测结果存储仅支持 PostgreSQL。")


def validate_mode_payload_table_name(table_name: str) -> str:
    """校验表名是否为合法的 `mode_payload_{数字}` 格式。

    Args:
        table_name: 待校验的表名。

    Returns:
        str: 校验通过后的标准表名。

    Raises:
        ValueError: 表名不合法时抛出。
    """

    normalized = str(table_name or "").strip()
    if not MODE_PAYLOAD_TABLE_RE.fullmatch(normalized):
        raise ValueError(f"无效的 mode_payload 表名: {table_name}")
    return normalized


def split_csv_text(value: Any) -> list[str]:
    """按逗号拆分文本并去除空白项。

    Args:
        value: 任意待拆分的值，通常为 `res_code`、`code` 或数据库中的文本列。

    Returns:
        list[str]: 去除空白与空字符串后的文本列表。
    """

    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def normalize_csv_placeholder_text(value: Any) -> str:
    """把只含逗号/空白的逗号分隔文本归一为空串。"""
    text = str(value or "")
    return "" if text.replace(",", "").strip() == "" else text


def normalize_res_code_numbers(res_code: Any) -> list[str]:
    """把 `res_code` 归一成两位数号码列表。

    这里会尽量容忍历史脏数据：
    1. 只接收能成功转成整数的片段。
    2. 输出统一补零为 `01`、`02` 这种两位格式。

    Args:
        res_code: 开奖号码原始值，通常形如 `01,12,23,34,45,46,49`。

    Returns:
        list[str]: 归一后的号码列表；若原值为空或无法解析则返回空列表。
    """

    normalized_numbers: list[str] = []
    for raw_value in split_csv_text(res_code):
        try:
            normalized_numbers.append(f"{int(str(raw_value)):02d}")
        except (TypeError, ValueError):
            continue
    return normalized_numbers


def normalize_prediction_result_placeholders(row_data: dict[str, Any]) -> dict[str, Any]:
    """归一化预测结果字段，避免 `,,,,,,` 这类伪空值进入 created schema。"""
    normalized = dict(row_data)
    for field_name in ("res_code", "res_sx", "res_color"):
        if field_name in normalized:
            normalized[field_name] = normalize_csv_placeholder_text(normalized[field_name])
    return normalized


def normalize_color_label(label: Any) -> str:
    """把 fixed_data 中的波色标签归一成历史表常用值。

    当前 `public.mode_payload_*` 的 `res_color` 历史数据以 `red/blue/green`
    为主，而 `fixed_data.sign='波色'` 中通常保存为 `红波/蓝波/绿波`。

    Args:
        label: fixed_data 中读取到的波色标签。

    Returns:
        str: 归一后的波色值；无法识别时原样返回去空白结果。
    """

    raw_text = str(label or "").strip()
    lowered = raw_text.lower()
    if lowered in {"red", "blue", "green"}:
        return lowered
    if any(token in raw_text for token in ("红", "紅")):
        return "red"
    if any(token in raw_text for token in ("蓝", "藍")):
        return "blue"
    if any(token in raw_text for token in ("绿", "綠")):
        return "green"
    if "红" in raw_text:
        return "red"
    if "蓝" in raw_text:
        return "blue"
    if "绿" in raw_text:
        return "green"
    return raw_text


def load_fixed_data_number_label_map(conn: Any, sign_name: str) -> dict[str, str]:
    """从 `public.fixed_data` 读取“号码 -> 标签”映射。

    例如：
    - `sign='生肖'` 时返回 `01 -> 马`
    - `sign='波色'` 时返回 `01 -> 红波`

    Args:
        conn: PostgreSQL 连接对象。
        sign_name: `fixed_data.sign` 的分类名，例如 `生肖`、`波色`。

    Returns:
        dict[str, str]: 两位号码到标签的映射表；若 `fixed_data` 不存在则返回空字典。
    """

    fixed_table_name = "fixed_data"
    if not schema_table_exists(conn, SOURCE_SCHEMA_NAME, fixed_table_name):
        return {}

    rows = conn.execute(
        f"""
        SELECT name, code
        FROM {quote_qualified_identifier(SOURCE_SCHEMA_NAME, fixed_table_name)}
        WHERE sign = %s
        ORDER BY id
        """,
        (sign_name,),
    ).fetchall()

    number_map: dict[str, str] = {}
    for row in rows:
        label = str(row["name"] or "").strip()
        if not label:
            continue
        for raw_number in split_csv_text(row["code"]):
            try:
                normalized_number = f"{int(raw_number):02d}"
            except (TypeError, ValueError):
                continue
            number_map.setdefault(normalized_number, label)
    return number_map


def load_fixed_data_label_code_map(conn: Any, sign_name: str) -> dict[str, tuple[str, ...]]:
    fixed_table_name = "fixed_data"
    if not schema_table_exists(conn, SOURCE_SCHEMA_NAME, fixed_table_name):
        return {}

    rows = conn.execute(
        f"""
        SELECT name, code
        FROM {quote_qualified_identifier(SOURCE_SCHEMA_NAME, fixed_table_name)}
        WHERE sign = %s
        ORDER BY id
        """,
        (sign_name,),
    ).fetchall()

    label_map: dict[str, tuple[str, ...]] = {}
    for row in rows:
        label = str(row["name"] or "").strip()
        if not label:
            continue
        codes = tuple(split_csv_text(row["code"]))
        if codes:
            label_map[label] = codes
    return label_map


def compact_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def compute_three_period_window(term_value: Any) -> tuple[str, str] | None:
    text = str(term_value or "").strip()
    if not text:
        return None
    try:
        term_int = int(text)
    except (TypeError, ValueError):
        return None
    if term_int <= 0:
        return None

    rem = term_int % 3
    end_val = term_int + ((4 - rem) % 3)
    start_val = max(1, end_val - 2)
    return str(start_val), str(end_val)


def is_three_period_special_row(source_table_name: str, row_data: dict[str, Any]) -> bool:
    if validate_mode_payload_table_name(source_table_name) == "mode_payload_197":
        return True

    for key in ("modes_id", "mode_id", "table_modes_id"):
        value = row_data.get(key)
        try:
            if value is not None and int(str(value).strip()) == THREE_PERIOD_SPECIAL_MODE_ID:
                return True
        except (TypeError, ValueError):
            continue
    return False


def normalize_three_period_special_row(
    conn: Any,
    source_table_name: str,
    row_data: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(row_data)
    if not is_three_period_special_row(source_table_name, normalized):
        return normalized

    window = compute_three_period_window(normalized.get("term"))
    if window is None:
        start_value = str(normalized.get("start") or "").strip()
        end_value = str(normalized.get("end") or "").strip()
        if not start_value or not end_value:
            return normalized
    else:
        start_value, end_value = window

    normalized["start"] = start_value
    normalized["end"] = end_value

    zodiac_label_map = load_fixed_data_label_code_map(conn, FIXED_DATA_ZODIAC_SIGN)
    zodiac_labels = list(zodiac_label_map.keys())
    if len(zodiac_labels) < 4:
        return normalized

    seed = "|".join(
        [
            str(THREE_PERIOD_SPECIAL_MODE_ID),
            str(normalized.get("type") or ""),
            str(normalized.get("year") or ""),
            str(normalized.get("web") or normalized.get("web_id") or ""),
            start_value,
            end_value,
        ]
    )
    rng = random.Random(seed)
    chosen_labels = rng.sample(zodiac_labels, 4)
    normalized["content"] = compact_json_dumps(
        [f"{label}|{','.join(zodiac_label_map[label])}" for label in chosen_labels]
    )
    return normalized


def build_three_period_special_window_filter(
    columns: set[str],
    row_data: dict[str, Any],
) -> tuple[list[str], list[Any]] | None:
    required_pairs = [
        ("type", row_data.get("type")),
        ("year", row_data.get("year")),
        ("start", row_data.get("start")),
        ("end", row_data.get("end")),
    ]
    where_clauses: list[str] = []
    params: list[Any] = []

    for column_name, raw_value in required_pairs:
        value = str(raw_value or "").strip()
        if column_name not in columns or not value:
            return None
        where_clauses.append(f"CAST({quote_identifier(column_name)} AS TEXT) = %s")
        params.append(value)

    web_value = str(row_data.get("web") or "").strip()
    web_id_value = str(row_data.get("web_id") or "").strip()
    if "web" in columns and web_value:
        where_clauses.append(f'CAST({quote_identifier("web")} AS TEXT) = %s')
        params.append(web_value)
    elif "web_id" in columns and web_id_value:
        where_clauses.append(f'CAST({quote_identifier("web_id")} AS TEXT) = %s')
        params.append(web_id_value)
    elif "web" in columns or "web_id" in columns:
        return None

    return where_clauses, params


def sync_three_period_special_window_rows(
    conn: Any,
    source_table_name: str,
    row_data: dict[str, Any],
) -> int:
    table_name = validate_mode_payload_table_name(source_table_name)
    normalized_row = normalize_three_period_special_row(conn, table_name, row_data)
    if not is_three_period_special_row(table_name, normalized_row):
        return 0

    target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    window_filter = build_three_period_special_window_filter(target_columns, normalized_row)
    if window_filter is None:
        return 0

    content_value = str(normalized_row.get("content") or "").strip()
    start_value = str(normalized_row.get("start") or "").strip()
    end_value = str(normalized_row.get("end") or "").strip()
    if not content_value or not start_value or not end_value:
        return 0

    update_values: dict[str, Any] = {}
    if "content" in target_columns:
        update_values["content"] = content_value
    if "start" in target_columns:
        update_values["start"] = start_value
    if "end" in target_columns:
        update_values["end"] = end_value
    if not update_values:
        return 0

    update_sql = ", ".join(
        f"{quote_identifier(column_name)} = %s"
        for column_name in update_values
    )
    where_clauses, where_params = window_filter
    rowcount = conn.execute(
        f"""
        UPDATE {quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)}
        SET {update_sql}
        WHERE {" AND ".join(where_clauses)}
        """,
        list(update_values.values()) + where_params,
    ).rowcount
    return max(int(rowcount), 0)


def repair_three_period_special_created_rows(
    conn: Any,
    source_table_name: str,
    *,
    lottery_type: str | int | None = None,
    web_value: str | int | None = None,
    year: str | int | None = None,
) -> dict[str, int]:
    table_name = validate_mode_payload_table_name(source_table_name)
    if not created_table_exists(conn, table_name):
        return {"windows": 0, "rows": 0}

    target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    required_columns = {"type", "year", "start", "end"}
    if not required_columns.issubset(target_columns):
        return {"windows": 0, "rows": 0}

    select_columns = [
        quote_identifier("type"),
        quote_identifier("year"),
        quote_identifier("start"),
        quote_identifier("end"),
    ]
    if "web" in target_columns:
        select_columns.append(quote_identifier("web"))
    if "web_id" in target_columns:
        select_columns.append(quote_identifier("web_id"))

    where_clauses = [
        f"COALESCE(CAST({quote_identifier('start')} AS TEXT), '') != ''",
        f"COALESCE(CAST({quote_identifier('end')} AS TEXT), '') != ''",
    ]
    params: list[Any] = []

    if lottery_type is not None and "type" in target_columns:
        where_clauses.append(f'CAST({quote_identifier("type")} AS TEXT) = %s')
        params.append(str(lottery_type))

    if year is not None and "year" in target_columns:
        where_clauses.append(f'CAST({quote_identifier("year")} AS TEXT) = %s')
        params.append(str(year))

    if web_value is not None:
        if "web" in target_columns:
            where_clauses.append(f'CAST({quote_identifier("web")} AS TEXT) = %s')
            params.append(str(web_value))
        elif "web_id" in target_columns:
            where_clauses.append(f'CAST({quote_identifier("web_id")} AS TEXT) = %s')
            params.append(str(web_value))

    rows = conn.execute(
        f"""
        SELECT DISTINCT {", ".join(select_columns)}
        FROM {quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)}
        WHERE {" AND ".join(where_clauses)}
        """,
        params,
    ).fetchall()

    repaired_rows = 0
    repaired_windows = 0
    for row in rows:
        row_data = {
            "type": row["type"],
            "year": row["year"],
            "start": row["start"],
            "end": row["end"],
        }
        if "web" in row:
            row_data["web"] = row["web"]
        if "web_id" in row:
            row_data["web_id"] = row["web_id"]
        repaired_rows += sync_three_period_special_window_rows(conn, table_name, row_data)
        repaired_windows += 1

    conn.commit()
    return {"windows": repaired_windows, "rows": repaired_rows}


def detect_public_result_field_policy(
    conn: Any,
    source_table_name: str,
    sample_web_value: str | int | None = None,
    sample_type_value: str | int = "3",
) -> dict[str, bool]:
    """根据 `public.mode_payload_{x}` 历史样本判断是否应生成 `res_sx/res_color`。

    规则遵循用户要求：
    1. 只参考对应模块 `public.mode_payload_{x}`。
    2. 只看 `web=4`、`type=3` 的历史数据。
    3. 若历史样本中某列曾出现非空值，则后续本地生成时补齐该列。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 对应模块的基础表名，例如 `mode_payload_57`。
        sample_web_value: 用于判断的历史 `web`/`web_id` 值，默认 `4`。
        sample_type_value: 用于判断的历史 `type` 值，默认 `3`。

    Returns:
        dict[str, bool]: 形如 `{"res_sx": True, "res_color": False}` 的策略字典。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    flags = {"res_sx": False, "res_color": False}
    if not schema_table_exists(conn, SOURCE_SCHEMA_NAME, table_name):
        return flags

    columns = set(table_column_names(conn, SOURCE_SCHEMA_NAME, table_name))
    if "type" not in columns:
        return flags

    web_column = "web" if "web" in columns else ("web_id" if "web_id" in columns else "")
    select_parts = [
        f"{quote_identifier('res_sx')}" if "res_sx" in columns else "NULL AS res_sx",
        f"{quote_identifier('res_color')}" if "res_color" in columns else "NULL AS res_color",
    ]
    where_clauses = [f"CAST({quote_identifier('type')} AS TEXT) = %s"]
    params: list[Any] = [str(sample_type_value)]

    if web_column and sample_web_value not in (None, ""):
        where_clauses.append(f"CAST({quote_identifier(web_column)} AS TEXT) = %s")
        params.append(str(sample_web_value))

    order_parts: list[str] = []
    if "year" in columns:
        order_parts.append(f"CAST({quote_identifier('year')} AS INTEGER) DESC")
    if "term" in columns:
        order_parts.append(f"CAST({quote_identifier('term')} AS INTEGER) DESC")
    if "id" in columns:
        order_parts.append(
            f"CAST(COALESCE(NULLIF(CAST({quote_identifier('id')} AS TEXT), ''), '0') AS BIGINT) DESC"
        )
    order_sql = f"ORDER BY {', '.join(order_parts)}" if order_parts else ""

    rows = conn.execute(
        f"""
        SELECT {", ".join(select_parts)}
        FROM {quote_qualified_identifier(SOURCE_SCHEMA_NAME, table_name)}
        WHERE {" AND ".join(where_clauses)}
        {order_sql}
        LIMIT 100
        """,
        params,
    ).fetchall()

    for row in rows:
        if not flags["res_sx"] and str(row["res_sx"] or "").strip():
            flags["res_sx"] = True
        if not flags["res_color"] and str(row["res_color"] or "").strip():
            flags["res_color"] = True
        if flags["res_sx"] and flags["res_color"]:
            break

    return flags


def enrich_prediction_result_fields(
    conn: Any,
    source_table_name: str,
    row_data: dict[str, Any],
) -> dict[str, Any]:
    """按历史样本策略补齐本地预测结果的 `res_sx` 与 `res_color`。

    该函数不会无条件覆盖传入值，而是仅在以下条件同时满足时补齐：
    1. 当前行存在可解析的 `res_code`
    2. 对应 `public.mode_payload_{x}` 的 `web=4,type=3` 历史样本需要该列
    3. 传入 `row_data` 中该列当前为空

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 对应模块的基础表名，例如 `mode_payload_44`。
        row_data: 即将写入 created schema 的业务数据字典。

    Returns:
        dict[str, Any]: 补齐后的新字典；原始 `row_data` 不会被原地修改。
    """

    enriched_data = dict(row_data)
    numbers = normalize_res_code_numbers(enriched_data.get("res_code"))
    if not numbers:
        return enriched_data

    field_policy = detect_public_result_field_policy(
        conn,
        source_table_name,
        sample_web_value=enriched_data.get("web") or enriched_data.get("web_id"),
        sample_type_value=enriched_data.get("type") or "3",
    )
    if field_policy.get("res_sx") and not str(enriched_data.get("res_sx") or "").strip():
        zodiac_map = load_fixed_data_number_label_map(conn, FIXED_DATA_ZODIAC_SIGN)
        zodiac_values = [zodiac_map.get(number, "") for number in numbers]
        if any(zodiac_values):
            enriched_data["res_sx"] = ",".join(zodiac_values)

    if field_policy.get("res_color") and not str(enriched_data.get("res_color") or "").strip():
        color_map = load_fixed_data_number_label_map(conn, FIXED_DATA_COLOR_SIGN)
        color_values = [normalize_color_label(color_map.get(number, "")) for number in numbers]
        if any(color_values):
            enriched_data["res_color"] = ",".join(color_values)

    return enriched_data


def schema_table_exists(conn: Any, schema_name: str, table_name: str) -> bool:
    """判断指定 schema 下的目标表是否存在。

    Args:
        conn: PostgreSQL 连接对象。
        schema_name: schema 名称。
        table_name: 表名称。

    Returns:
        bool: 存在返回 `True`，否则返回 `False`。
    """

    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
        LIMIT 1
        """,
        (schema_name, table_name),
    ).fetchone()
    return bool(row)


def list_table_columns(conn: Any, schema_name: str, table_name: str) -> list[TableColumn]:
    """读取指定表的列定义。

    使用 `pg_catalog.format_type()` 保留 PostgreSQL 列类型的真实定义，
    例如 `character varying(255)`、`numeric(10,2)` 等。

    Args:
        conn: PostgreSQL 连接对象。
        schema_name: schema 名称。
        table_name: 表名称。

    Returns:
        list[TableColumn]: 按列顺序排列的列定义列表。
    """

    rows = conn.execute(
        """
        SELECT
            attr.attname AS column_name,
            pg_catalog.format_type(attr.atttypid, attr.atttypmod) AS column_type
        FROM pg_catalog.pg_attribute AS attr
        JOIN pg_catalog.pg_class AS cls
          ON attr.attrelid = cls.oid
        JOIN pg_catalog.pg_namespace AS nsp
          ON cls.relnamespace = nsp.oid
        WHERE nsp.nspname = %s
          AND cls.relname = %s
          AND attr.attnum > 0
          AND NOT attr.attisdropped
        ORDER BY attr.attnum
        """,
        (schema_name, table_name),
    ).fetchall()

    return [
        TableColumn(
            name=str(row["column_name"]),
            sql_type=str(row["column_type"]),
        )
        for row in rows
    ]


def table_column_names(conn: Any, schema_name: str, table_name: str) -> tuple[str, ...]:
    """返回表的列名元组。

    Args:
        conn: PostgreSQL 连接对象。
        schema_name: schema 名称。
        table_name: 表名称。

    Returns:
        tuple[str, ...]: 目标表全部列名。
    """

    return tuple(column.name for column in list_table_columns(conn, schema_name, table_name))


def ensure_created_schema(conn: Any) -> None:
    """确保 `created` schema 已存在。

    Args:
        conn: PostgreSQL 连接对象。

    Returns:
        None: 仅创建 schema，不返回结果。
    """

    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(CREATED_SCHEMA_NAME)}")


def ensure_created_prediction_table(conn: Any, source_table_name: str) -> str:
    """确保 `created.mode_payload_{mode_id}` 目标表存在且结构正确。

    结构来源：
    1. 先以 `public.mode_payload_{mode_id}` 为源复制业务列
    2. 强制新增或修正 `id TEXT`
    3. 强制新增或修正 `created_at TEXT`
    4. 为本地生成链路补齐 `mode_id INTEGER`，便于后台统计和前端识别来源模块

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 原始公共表名，格式必须为 `mode_payload_{数字}`。

    Returns:
        str: 目标表的完整限定名，例如 `"created"."mode_payload_53"`。
    """

    ensure_postgres_connection(conn)
    table_name = validate_mode_payload_table_name(source_table_name)
    source_qualified = quote_qualified_identifier(SOURCE_SCHEMA_NAME, table_name)
    target_qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)

    if not schema_table_exists(conn, SOURCE_SCHEMA_NAME, table_name):
        raise ValueError(f"源表不存在: {SOURCE_SCHEMA_NAME}.{table_name}")

    ensure_created_schema(conn)
    source_columns = list_table_columns(conn, SOURCE_SCHEMA_NAME, table_name)
    target_exists = schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name)

    if not target_exists:
        column_definitions: list[str] = []
        seen_columns: set[str] = set()

        for column in source_columns:
            if column.name == "id":
                column_definitions.append(f'{quote_identifier("id")} TEXT')
                seen_columns.add("id")
                continue
            if column.name == "created_at":
                column_definitions.append(f'{quote_identifier("created_at")} TEXT')
                seen_columns.add("created_at")
                continue

            column_definitions.append(
                f"{quote_identifier(column.name)} {column.sql_type}"
            )
            seen_columns.add(column.name)

        if "id" not in seen_columns:
            column_definitions.insert(0, f'{quote_identifier("id")} TEXT')
        if "created_at" not in seen_columns:
            column_definitions.append(f'{quote_identifier("created_at")} TEXT')

        conn.execute(
            f"""
            CREATE TABLE {target_qualified} (
                {", ".join(column_definitions)}
            )
            """
        )

    target_columns = {column.name: column.sql_type for column in list_table_columns(conn, CREATED_SCHEMA_NAME, table_name)}

    if "id" not in target_columns:
        conn.execute(f'ALTER TABLE {target_qualified} ADD COLUMN {quote_identifier("id")} TEXT')
    elif target_columns["id"].lower() != "text":
        conn.execute(
            f"""
            ALTER TABLE {target_qualified}
            ALTER COLUMN {quote_identifier("id")} TYPE TEXT
            USING CASE
                WHEN {quote_identifier("id")} IS NULL THEN NULL
                ELSE CAST({quote_identifier("id")} AS TEXT)
            END
            """
        )

    if "created_at" not in target_columns:
        conn.execute(
            f'ALTER TABLE {target_qualified} ADD COLUMN {quote_identifier("created_at")} TEXT'
        )
    elif target_columns["created_at"].lower() != "text":
        conn.execute(
            f"""
            ALTER TABLE {target_qualified}
            ALTER COLUMN {quote_identifier("created_at")} TYPE TEXT
            USING CASE
                WHEN {quote_identifier("created_at")} IS NULL THEN NULL
                ELSE CAST({quote_identifier("created_at")} AS TEXT)
            END
            """
        )

    existing_target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    for column in source_columns:
        if column.name in {"id", "created_at"}:
            continue
        if column.name not in existing_target_columns:
            conn.execute(
                f"""
                ALTER TABLE {target_qualified}
                ADD COLUMN {quote_identifier(column.name)} {column.sql_type}
                """
            )

    existing_target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    if "mode_id" not in existing_target_columns:
        conn.execute(
            f"""
            ALTER TABLE {target_qualified}
            ADD COLUMN {quote_identifier("mode_id")} INTEGER
            """
        )

    # 如果历史遗留数据中存在非 `c数字` 形式的 id，这里统一规范成带 c 前缀。
    conn.execute(
        f"""
        UPDATE {target_qualified}
        SET {quote_identifier("id")} = CASE
            WHEN {quote_identifier("id")} IS NULL THEN NULL
            WHEN BTRIM({quote_identifier("id")}) = '' THEN {quote_identifier("id")}
            WHEN {quote_identifier("id")} ~ '^c[0-9]+$' THEN {quote_identifier("id")}
            ELSE 'c' || REGEXP_REPLACE(BTRIM({quote_identifier("id")}), '^[cC]+', '')
        END
        WHERE {quote_identifier("id")} IS NOT NULL
        """
    )

    conn.execute(
        f"""
        UPDATE {target_qualified}
        SET {quote_identifier("created_at")} = %s
        WHERE {quote_identifier("created_at")} IS NULL
           OR BTRIM(CAST({quote_identifier("created_at")} AS TEXT)) = ''
        """,
        (utc_now_iso(),),
    )
    conn.commit()
    return target_qualified


def next_created_row_id(conn: Any, source_table_name: str) -> str:
    """生成下一条 `c` 前缀预测记录 id。

    规则示例：
    - 已存在 `c1, c2, c2333`
    - 下一条返回 `c2334`

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 目标表名，格式为 `mode_payload_{数字}`。

    Returns:
        str: 新生成的 `c` 前缀 id。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    target_qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    row = conn.execute(
        f"""
        SELECT COALESCE(
            MAX(CAST(SUBSTRING({quote_identifier("id")} FROM 2) AS BIGINT)),
            0
        ) AS max_suffix
        FROM {target_qualified}
        WHERE {quote_identifier("id")} ~ '^c[0-9]+$'
        """
    ).fetchone()
    next_suffix = int(row["max_suffix"] or 0) + 1 if row else 1
    return f"c{next_suffix}"


def find_existing_created_row(
    conn: Any,
    source_table_name: str,
    row_data: dict[str, Any],
) -> dict[str, Any] | None:
    """按业务期次定位 `created` schema 中已存在的预测记录。

    匹配优先级：
    1. `type + year + term + web`
    2. 若无 `web` 列，则改为 `type + year + term + web_id`
    3. 若两种列都不存在，则退化为 `type + year + term`

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 目标表名。
        row_data: 待写入的业务数据。

    Returns:
        dict[str, Any] | None: 匹配到时返回现有行的 `id` 和 `created_at`，否则返回 `None`。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    target_qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))

    where_clauses: list[str] = []
    params: list[Any] = []

    for required_column in ("type", "year", "term"):
        if required_column not in columns or required_column not in row_data:
            return None
        where_clauses.append(f"CAST({quote_identifier(required_column)} AS TEXT) = %s")
        params.append(str(row_data[required_column]))

    if "web" in columns and "web" in row_data:
        where_clauses.append(f'CAST({quote_identifier("web")} AS TEXT) = %s')
        params.append(str(row_data["web"]))
    elif "web_id" in columns and "web_id" in row_data:
        where_clauses.append(f'CAST({quote_identifier("web_id")} AS TEXT) = %s')
        params.append(str(row_data["web_id"]))

    row = conn.execute(
        f"""
        SELECT {quote_identifier("id")}, {quote_identifier("created_at")}
        FROM {target_qualified}
        WHERE {" AND ".join(where_clauses)}
        ORDER BY CAST({quote_identifier("created_at")} AS TEXT) DESC, {quote_identifier("id")} DESC
        LIMIT 1
        """,
        params,
    ).fetchone()
    return dict(row) if row else None


def upsert_created_prediction_row(
    conn: Any,
    source_table_name: str,
    row_data: dict[str, Any],
) -> dict[str, Any]:
    """向 `created.mode_payload_{mode_id}` 写入或更新一条本地预测结果。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 对应 `public.mode_payload_{mode_id}` 的基础表名。
        row_data: 待写入的业务字段字典。函数会自动过滤为目标表真实存在的列，
            并自动补齐 `id` 与 `created_at`。

    Returns:
        dict[str, Any]: 包含写入动作、目标表、生成 id 和创建时间的结果字典。
    """

    ensure_postgres_connection(conn)
    table_name = validate_mode_payload_table_name(source_table_name)
    target_qualified = ensure_created_prediction_table(conn, table_name)
    target_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    normalized_row_data = normalize_three_period_special_row(conn, table_name, row_data)
    enriched_row_data = enrich_prediction_result_fields(conn, table_name, normalized_row_data)
    prepared_row_data = normalize_prediction_result_placeholders(enriched_row_data)

    filtered_data = {
        key: value
        for key, value in prepared_row_data.items()
        if key in target_columns and key not in {"id", "created_at"}
    }

    if not filtered_data:
        raise ValueError("待写入数据与 created schema 目标表没有可匹配列。")

    existing_row = find_existing_created_row(conn, table_name, filtered_data)
    if existing_row:
        update_columns = list(filtered_data.keys())
        update_sql = ", ".join(
            f"{quote_identifier(column)} = %s" for column in update_columns
        )
        conn.execute(
            f"""
            UPDATE {target_qualified}
            SET {update_sql}
            WHERE {quote_identifier("id")} = %s
            """,
            [filtered_data[column] for column in update_columns] + [existing_row["id"]],
        )
        sync_three_period_special_window_rows(conn, table_name, filtered_data)
        conn.commit()
        return {
            "action": "updated",
            "schema": CREATED_SCHEMA_NAME,
            "table": table_name,
            "qualified_table": f"{CREATED_SCHEMA_NAME}.{table_name}",
            "id": str(existing_row["id"]),
            "created_at": str(existing_row["created_at"] or ""),
        }

    created_id = next_created_row_id(conn, table_name)
    created_at = utc_now_iso()
    insert_data = {
        **filtered_data,
        "id": created_id,
        "created_at": created_at,
    }
    insert_columns = list(insert_data.keys())
    placeholders = ", ".join(["%s"] * len(insert_columns))
    conn.execute(
        f"""
        INSERT INTO {target_qualified} (
            {", ".join(quote_identifier(column) for column in insert_columns)}
        )
        VALUES ({placeholders})
        """,
        [insert_data[column] for column in insert_columns],
    )
    sync_three_period_special_window_rows(conn, table_name, insert_data)
    conn.commit()
    return {
        "action": "inserted",
        "schema": CREATED_SCHEMA_NAME,
        "table": table_name,
        "qualified_table": f"{CREATED_SCHEMA_NAME}.{table_name}",
        "id": created_id,
        "created_at": created_at,
    }


def created_table_exists(conn: Any, source_table_name: str) -> bool:
    """判断 `created` schema 中是否已存在目标预测表。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 基础表名。

    Returns:
        bool: 存在返回 `True`，否则返回 `False`。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    return schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name)


def count_created_prediction_rows(
    conn: Any,
    source_table_name: str,
    lottery_type: str | int | None = None,
    web_value: str | int | None = None,
    only_filled: bool = False,
) -> int:
    """统计 `created` schema 中指定表的预测记录数。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 基础表名。
        lottery_type: 可选，按 `type` 过滤。
        web_value: 可选，按 `web` 或 `web_id` 过滤。
        only_filled: 是否只统计 `res_code` 非空的记录。

    Returns:
        int: 命中的记录数。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    if not created_table_exists(conn, table_name):
        return 0

    target_qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    where_clauses: list[str] = []
    params: list[Any] = []

    if lottery_type is not None and "type" in columns:
        where_clauses.append(f'CAST({quote_identifier("type")} AS TEXT) = %s')
        params.append(str(lottery_type))

    if web_value is not None:
        if "web" in columns:
            where_clauses.append(f'CAST({quote_identifier("web")} AS TEXT) = %s')
            params.append(str(web_value))
        elif "web_id" in columns:
            where_clauses.append(f'CAST({quote_identifier("web_id")} AS TEXT) = %s')
            params.append(str(web_value))

    if only_filled and "res_code" in columns:
        where_clauses.append(f"{quote_identifier('res_code')} IS NOT NULL")
        where_clauses.append(f"{quote_identifier('res_code')} != ''")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    row = conn.execute(
        f"SELECT COUNT(*) AS total FROM {target_qualified} {where_sql}",
        params,
    ).fetchone()
    return int(row["total"] or 0) if row else 0


def list_created_prediction_terms(
    conn: Any,
    source_table_name: str,
    lottery_type: str | int | None = None,
    web_value: str | int | None = None,
    only_filled: bool = False,
) -> set[tuple[int, int]]:
    """列出 `created` schema 中已存在的 `(year, term)` 组合。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 基础表名。
        lottery_type: 可选，按 `type` 过滤。
        web_value: 可选，按 `web` 或 `web_id` 过滤。
        only_filled: 是否仅统计 `res_code` 非空记录。

    Returns:
        set[tuple[int, int]]: 已存在的期次集合。
    """

    table_name = validate_mode_payload_table_name(source_table_name)
    if not created_table_exists(conn, table_name):
        return set()

    target_qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
    columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
    if "year" not in columns or "term" not in columns:
        return set()

    where_clauses: list[str] = []
    params: list[Any] = []

    if lottery_type is not None and "type" in columns:
        where_clauses.append(f'CAST({quote_identifier("type")} AS TEXT) = %s')
        params.append(str(lottery_type))

    if web_value is not None:
        if "web" in columns:
            where_clauses.append(f'CAST({quote_identifier("web")} AS TEXT) = %s')
            params.append(str(web_value))
        elif "web_id" in columns:
            where_clauses.append(f'CAST({quote_identifier("web_id")} AS TEXT) = %s')
            params.append(str(web_value))

    if only_filled and "res_code" in columns:
        where_clauses.append(f"{quote_identifier('res_code')} IS NOT NULL")
        where_clauses.append(f"{quote_identifier('res_code')} != ''")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = conn.execute(
        f"""
        SELECT {quote_identifier("year")}, {quote_identifier("term")}
        FROM {target_qualified}
        {where_sql}
        """,
        params,
    ).fetchall()

    result: set[tuple[int, int]] = set()
    for row in rows:
        try:
            result.add((int(row["year"] or 0), int(row["term"] or 0)))
        except (TypeError, ValueError):
            continue
    return result


def created_prediction_issue_exists(
    conn: Any,
    source_table_name: str,
    lottery_type: str | int,
    year: str | int,
    term: str | int,
    web_value: str | int | None = None,
) -> bool:
    """判断 `created` schema 中某一期预测记录是否已存在。

    Args:
        conn: PostgreSQL 连接对象。
        source_table_name: 基础表名。
        lottery_type: 彩种类型。
        year: 年份。
        term: 期号。
        web_value: 可选，站点值。

    Returns:
        bool: 已存在返回 `True`，否则返回 `False`。
    """

    probe_data: dict[str, Any] = {
        "type": str(lottery_type),
        "year": str(year),
        "term": str(term),
    }
    if web_value is not None:
        probe_data["web"] = str(web_value)
        probe_data["web_id"] = str(web_value)
    return find_existing_created_row(conn, source_table_name, probe_data) is not None
