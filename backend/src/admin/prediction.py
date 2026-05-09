"""
Admin 预测管理 —— 模块同步 / 生成 / 批量操作 / 安全控制。

提供以下核心能力：
- 站点预测模块的同步与蓝图查询
- 预测行数据的构建与规范化
- 开奖可见性安全控制（防止未开奖期次泄露号码）
- 预测 API 响应构建
- 期号范围解析与已开奖数据查询
- 批量生成预测数据 & 单表重生成

从 app.py 提取，不改变任何函数签名与行为。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PREDICT_ROOT = Path(__file__).resolve().parents[1] / "predict"
_UTILS_ROOT = Path(__file__).resolve().parents[1] / "utils"
for _p in (_PREDICT_ROOT, _UTILS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from common import DEFAULT_TARGET_HIT_RATE, predict  # noqa: E402
from db import connect as db_connect, quote_identifier
from helpers import (
    apply_lottery_draw_overlay, load_fixed_data_maps, normalize_issue_part,
    parse_issue_int, split_csv,
)
from mechanisms import get_prediction_config, list_prediction_configs  # noqa: E402
from utils.created_prediction_store import (  # noqa: E402
    CREATED_SCHEMA_NAME, created_table_exists, normalize_color_label,
    quote_qualified_identifier as quote_schema_table,
    schema_table_exists, table_column_names, upsert_created_prediction_row,
)

# 前端需要的站点预测模块 mode_id 清单，按展示顺序排列
REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 151, 197,
)


def utc_now() -> str:
    """获取当前 UTC 时间，返回 ISO 8601 格式字符串。

    :return: 当前 UTC 时间的 ISO 8601 字符串
    """
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | Path) -> Any:
    """打开并返回数据库连接对象。

    :param db_path: SQLite 数据库文件路径（字符串或 pathlib.Path 对象）
    :return: 数据库连接对象
    """
    return db_connect(db_path)


def get_site_prediction_module_blueprints() -> list[dict[str, Any]]:
    """获取站点预测模块的标准配置清单，按前端要求的 mode_id 顺序输出。

    遍历所有预测配置，根据 ``REQUIRED_SITE_PREDICTION_MODE_IDS`` 筛选并排序，
    生成每个模块的蓝图字典，包含 mode_id、sort_order 等字段。

    :return: 预测模块蓝图列表，每个元素包含 key、mode_id、sort_order 等字段
    :raises ValueError: 当某个必需 mode_id 在预测配置中不存在时抛出
    """
    configs_by_mode_id: dict[int, dict[str, Any]] = {}
    for item in list_prediction_configs():
        try:
            configs_by_mode_id[int(item["default_modes_id"])] = item
        except (TypeError, ValueError):
            continue

    missing = [mode_id for mode_id in REQUIRED_SITE_PREDICTION_MODE_IDS if mode_id not in configs_by_mode_id]
    if missing:
        raise ValueError(f"以下 mode_id 缺少预测配置，无法同步站点模块: {missing}")

    blueprints: list[dict[str, Any]] = []
    for index, mode_id in enumerate(REQUIRED_SITE_PREDICTION_MODE_IDS):
        item = dict(configs_by_mode_id[mode_id])
        item["mode_id"] = int(mode_id)
        item["sort_order"] = index * 10
        blueprints.append(item)
    return blueprints


def get_site_prediction_module_blueprint_by_key(mechanism_key: str) -> dict[str, Any]:
    """按 mechanism_key 获取站点允许使用的模块配置。

    从站点预测模块蓝图清单中查找匹配 mechanism_key 的配置项。

    :param mechanism_key: 预测机制的唯一标识 key
    :return: 匹配的模块蓝图字典
    :raises ValueError: 当 mechanism_key 不在站点模块同步清单中时抛出
    """
    for item in get_site_prediction_module_blueprints():
        if str(item["key"]) == str(mechanism_key):
            return item
    raise ValueError(f"机制 {mechanism_key} 不在站点模块同步清单中")


def resolve_prediction_table_for_mode(
    conn: Any,
    mode_id: int,
    fallback_table: str = "",
) -> str:
    """根据 mode_id 从 mode_payload_tables 解析对应的数据表名。

    优先从 mode_payload_tables 表中查找 mode_id 对应的 table_name；
    若未找到，则依次回退到 fallback_table 或默认格式 ``mode_payload_{mode_id}``。

    :param conn: 数据库连接对象
    :param mode_id: 预测模式 ID（modes_id）
    :param fallback_table: 可选，未找到映射时的回退表名
    :return: 解析后的数据表名
    """
    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id > 0 and conn.table_exists("mode_payload_tables"):
        row = conn.execute(
            """
            SELECT table_name
            FROM mode_payload_tables
            WHERE modes_id = ?
            LIMIT 1
            """,
            (resolved_mode_id,),
        ).fetchone()
        if row and str(row["table_name"] or "").strip():
            return str(row["table_name"]).strip()
    if fallback_table:
        return str(fallback_table)
    if resolved_mode_id > 0:
        return f"mode_payload_{resolved_mode_id}"
    return ""


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """将 site_prediction_modules 表与前端站点模块清单保持同步。

    对指定站点（或全部站点）的预测模块记录进行增量更新：
    已存在的记录仅更新 mode_id 和 sort_order；不存在的记录则插入新行。

    :param conn: 数据库连接对象
    :param site_id: 可选，指定要同步的站点 ID；为 None 时同步所有托管站点
    """
    blueprints = get_site_prediction_module_blueprints()
    allowed_keys = tuple(str(item["key"]) for item in blueprints)
    now = utc_now()

    site_query = "SELECT id FROM managed_sites"
    site_params: tuple[Any, ...] = ()
    if site_id is not None:
        site_query += " WHERE id = ?"
        site_params = (int(site_id),)
    site_rows = conn.execute(site_query, site_params).fetchall()

    for site_row in site_rows:
        current_site_id = int(site_row["id"])
        existing_rows = conn.execute(
            """
            SELECT mechanism_key, status, created_at
            FROM site_prediction_modules
            WHERE site_id = ?
            """,
            (current_site_id,),
        ).fetchall()
        existing_by_key = {str(row["mechanism_key"]): dict(row) for row in existing_rows}

        for item in blueprints:
            existing = existing_by_key.get(str(item["key"]))
            if existing:
                conn.execute(
                    """
                    UPDATE site_prediction_modules
                    SET mode_id = ?, sort_order = ?, updated_at = ?
                    WHERE site_id = ? AND mechanism_key = ?
                    """,
                    (
                        int(item["mode_id"]),
                        int(item["sort_order"]),
                        now,
                        current_site_id,
                        str(item["key"]),
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO site_prediction_modules (
                        site_id, mechanism_key, mode_id, status, sort_order, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        current_site_id,
                        str(item["key"]),
                        int(item["mode_id"]),
                        1,
                        int(item["sort_order"]),
                        now,
                        now,
                    ),
                )



# ─────────────────────────────────────────────────────────
# 预测行数据构建 / Prediction row data construction
# ─────────────────────────────────────────────────────────

def build_generated_prediction_row_data(
    *,
    mode_id: int,
    lottery_type: str = "",
    year: str = "",
    term: str = "",
    web_value: str = "4",
    res_code: str = "",
    generated_content: Any,
    db_path: str | Path = "",
) -> dict[str, Any]:
    """将 ``predict()`` 的输出转换成 created schema 可直接落库的行数据结构。

    自动处理：
    - 三期窗口字段（start / end）的计算与填充
    - 列表、字典等复杂类型的 JSON 序列化
    - 根据 res_code 计算 res_sx（生肖）和 res_color（波色）

    :param mode_id: 预测模式 ID
    :param lottery_type: 彩种类型，默认空字符串
    :param year: 年份，默认空字符串
    :param term: 期号，非空时自动计算三期窗口（start=term, end=term-2）
    :param web_value: 站点 web 标识，默认 "4"
    :param res_code: 开奖号码（逗号分隔的 7 个数字），用于计算 res_sx 和 res_color
    :param generated_content: ``predict()`` 返回的预测内容（dict / list / str）
    :param db_path: 数据库路径，用于加载固定数据映射以计算生肖/波色
    :return: 可直接写入数据库的行数据字典
    """
    web_val = str(web_value or "4")
    row_data: dict[str, Any] = {
        "type": str(lottery_type or ""),
        "year": str(year or ""),
        "term": str(term or ""),
        "web": web_val,
        "web_id": int(web_val) if web_val.isdigit() else 4,
        "modes_id": int(mode_id) if mode_id else 0,
        "res_code": str(res_code or ""),
    }

    # 若提供了 res_code，同步计算 res_sx 和 res_color
    if res_code and db_path:
        codes = [c.strip() for c in str(res_code).split(",") if c.strip()]
        if len(codes) == 7:
            special = codes[-1]
            from helpers import load_fixed_data_maps
            with connect(db_path) as _tmp_conn:
                zmap, cmap = load_fixed_data_maps(_tmp_conn)
            row_data["res_sx"] = zmap.get(special, "")
            color = cmap.get(special, "")
            if color:
                from utils.created_prediction_store import normalize_color_label
                row_data["res_color"] = normalize_color_label(color)

    # 三期窗口自动填充：每 3 期为一组，组内共享 start/end
    # 例如 term=127 → end=127, start=125；term=126 → end=127, start=125
    term_int = int(term) if str(term or "").strip().isdigit() else 0
    if term_int > 0:
        r = term_int % 3
        end_val = term_int + ((4 - r) % 3)
        start_val = max(1, end_val - 2)
        if isinstance(generated_content, dict):
            generated_content["start"] = str(start_val)
            generated_content["end"] = str(end_val)

    if isinstance(generated_content, dict):
        for key, value in generated_content.items():
            if key == "_labels":
                continue
            # 列表/字典类 value 需要 JSON 序列化，否则数据库存储为 Python repr 格式
            if isinstance(value, (list, dict, tuple, set)):
                row_data[key] = json.dumps(value, ensure_ascii=False)
            else:
                row_data[key] = value
    elif isinstance(generated_content, list):
        row_data["content"] = json.dumps(generated_content, ensure_ascii=False)
    else:
        row_data["content"] = str(generated_content or "")

    return row_data


def normalize_prediction_display_text(content: Any) -> str:
    """将预测内容统一转为前端可直接展示的文本字符串。

    :param content: 预测内容（可为 None、str、dict、list 等任意类型）
    :return: 标准化后的展示文本字符串
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


# ─────────────────────────────────────────────────────────
# 预测安全控制 / Prediction safety control
# ─────────────────────────────────────────────────────────

def lookup_draw_visibility(
    conn: Any,
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
) -> dict[str, Any]:
    """查询指定期次的开奖可见性，供预测接口做安全策略复用。

    根据 lottery_draws 表中的 is_opened 字段判断该期是否已开奖：
    - 已开奖（is_opened=1）：result_visibility = "visible"
    - 未开奖（is_opened=0）：result_visibility = "hidden"
    - 找不到记录：result_visibility = "unknown"

    :param conn: 数据库连接对象
    :param lottery_type: 彩种类型（支持字符串如 "3" 或整数）
    :param year: 年份
    :param term: 期号
    :return: 字典，包含以下字段：
             - ``issue``: 期次字符串
             - ``lottery_type`` / ``year`` / ``term``: 原始参数
             - ``result_visibility``: "visible" / "hidden" / "unknown"
             - ``reason``: "draw_found" / "draw_not_found" / "missing_issue_context"
    """
    lottery_type_id = parse_issue_int(lottery_type)
    year_value = parse_issue_int(year)
    term_value = parse_issue_int(term)

    issue = f"{year_value or ''}{term_value or ''}".strip()
    context: dict[str, Any] = {
        "issue": issue or "",
        "lottery_type": str(lottery_type or ""),
        "year": str(year or ""),
        "term": str(term or ""),
        "lottery_type_id": lottery_type_id,
        "year_value": year_value,
        "term_value": term_value,
    }

    if lottery_type_id is None or year_value is None or term_value is None:
        context["result_visibility"] = "unknown"
        context["reason"] = "missing_issue_context"
        return context

    row = conn.execute(
        """
        SELECT is_opened
        FROM lottery_draws
        WHERE lottery_type_id = ?
          AND year = ?
          AND term = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (lottery_type_id, year_value, term_value),
    ).fetchone()

    if not row:
        context["result_visibility"] = "unknown"
        context["reason"] = "draw_not_found"
        return context

    is_opened = bool(row["is_opened"])
    context["is_opened"] = is_opened
    context["reason"] = "draw_found"
    context["result_visibility"] = "visible" if is_opened else "hidden"
    return context


def redact_prediction_result_fields(row_data: dict[str, Any]) -> dict[str, Any]:
    """统一抹除开奖结果字段，避免未开奖期次泄露号码、生肖、波色。

    将 res_code、res_sx、res_color 三个字段置为空字符串。

    :param row_data: 预测行数据字典
    :return: 抹除敏感字段后的数据字典（新字典，不影响原数据）
    """
    sanitized = dict(row_data)
    for field_name in ("res_code", "res_sx", "res_color"):
        sanitized[field_name] = ""
    return sanitized


def apply_prediction_row_safety(
    conn: Any,
    row_data: dict[str, Any],
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
) -> dict[str, Any]:
    """根据开奖状态决定是否需要对预测行数据做安全处理。

    如果目标期次尚未开奖，则抹除 res_code / res_sx / res_color 字段；
    否则原样返回。

    :param conn: 数据库连接对象
    :param row_data: 预测行数据字典
    :param lottery_type: 彩种类型
    :param year: 年份
    :param term: 期号
    :return: 安全处理后的数据字典
    """
    visibility = lookup_draw_visibility(
        conn,
        lottery_type=lottery_type,
        year=year,
        term=term,
    )
    if visibility.get("result_visibility") == "hidden":
        return redact_prediction_result_fields(row_data)
    return dict(row_data)


def resolve_prediction_request_safety(
    conn: Any,
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
    res_code: Any = "",
) -> tuple[str | None, dict[str, Any]]:
    """检查预测请求是否允许携带 ``res_code`` 参与算法。

    若目标期次已开奖，则拒绝携带 res_code（返回 None），防止利用已知结果作弊；
    若未开奖，则正常传入 res_code。

    :param conn: 数据库连接对象
    :param lottery_type: 彩种类型
    :param year: 年份
    :param term: 期号
    :param res_code: 请求中携带的开奖号码
    :return: 元组 (safe_res_code, visibility_dict)
             - safe_res_code: 允许使用的 res_code（已开奖时为 None）
             - visibility_dict: 开奖可见性字典
    """
    normalized_res_code = str(res_code or "").strip() or ""
    visibility = lookup_draw_visibility(
        conn,
        lottery_type=lottery_type,
        year=year,
        term=term,
    )
    if visibility.get("result_visibility") == "hidden":
        return None, visibility
    return normalized_res_code or None, visibility


# ─────────────────────────────────────────────────────────
# API 响应构建 / API response construction
# ─────────────────────────────────────────────────────────

def build_prediction_api_response(
    *,
    mechanism_key: str,
    request_payload: dict[str, Any],
    raw_result: dict[str, Any],
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """将 ``predict()`` 的原始返回包装成对外稳定的 HTTP 协议格式。

    构建一个标准化的 API 响应字典，包含以下区块：
    - mechanism: 预测机制元信息
    - source: 数据源信息
    - request: 回显的请求参数
    - context: 上下文信息（最新期次、开奖可见性）
    - prediction: 预测结果（含标签、文本）
    - backtest: 回测结果
    - explanation: 解释信息
    - warning: 警告信息

    :param mechanism_key: 预测机制的唯一标识 key
    :param request_payload: 前端请求参数字典
    :param raw_result: ``predict()`` 的原始返回结果
    :param safety: 可选，开奖可见性字典（由 ``lookup_draw_visibility`` 返回）
    :return: 标准化的 API 响应字典
    """
    prediction_block = raw_result.get("prediction") or {}
    normalized_safety = dict(safety or {})

    if "result_visibility" not in normalized_safety:
        normalized_safety["result_visibility"] = "unknown"
    if "reason" not in normalized_safety:
        normalized_safety["reason"] = "not_evaluated"

    return {
        "ok": True,
        "protocol_version": 1,
        "generated_at": utc_now(),
        "data": {
            "mechanism": {
                "key": str(raw_result.get("mode", {}).get("key") or mechanism_key),
                "title": str(raw_result.get("mode", {}).get("title") or ""),
                "default_modes_id": raw_result.get("mode", {}).get("default_modes_id"),
                "default_table": str(raw_result.get("mode", {}).get("default_table") or ""),
                "resolved_labels": list(raw_result.get("mode", {}).get("resolved_labels") or []),
            },
            "source": {
                "db_path": str(raw_result.get("source", {}).get("db_path") or ""),
                "table": str(raw_result.get("source", {}).get("table") or ""),
                "source_modes_id": raw_result.get("source", {}).get("source_modes_id"),
                "source_table_title": str(raw_result.get("source", {}).get("source_table_title") or ""),
                "history_count": raw_result.get("source", {}).get("history_count"),
            },
            "request": {
                "res_code": request_payload.get("res_code"),
                "content": request_payload.get("content"),
                "source_table": request_payload.get("source_table"),
                "target_hit_rate": request_payload.get("target_hit_rate"),
                "lottery_type": request_payload.get("lottery_type"),
                "year": request_payload.get("year"),
                "term": request_payload.get("term"),
                "web": request_payload.get("web"),
            },
            "context": {
                "latest_term": raw_result.get("input", {}).get("latest_term"),
                "latest_outcome": raw_result.get("input", {}).get("latest_outcome"),
                "draw": normalized_safety,
            },
            "prediction": {
                "labels": list(prediction_block.get("labels") or []),
                "content": prediction_block.get("content"),
                "content_json": str(prediction_block.get("content_json") or ""),
                "display_text": normalize_prediction_display_text(prediction_block.get("content")),
            },
            "backtest": dict(raw_result.get("backtest") or {}),
            "explanation": list(raw_result.get("explanation") or []),
            "warning": str(raw_result.get("warning") or ""),
        },
        "legacy": raw_result,
    }


# ─────────────────────────────────────────────────────────
# 期号范围解析 & 开奖数据查询
# Issue range parsing & draw data query
# ─────────────────────────────────────────────────────────

def parse_issue_range_value(value: Any, label: str) -> tuple[int, int]:
    """解析前端传入的期号范围值，返回 (year, term) 元组。

    支持格式示例：``"2026001"``、``"2026-001"``、``"2026_001"`` 等，
    自动去除所有非数字字符后解析。

    :param value: 前端传入的期号值（字符串或数字）
    :param label: 字段标签（如 "起始期号"），用于错误提示
    :return: (year, term) 元组
    :raises ValueError: 当期号格式无效、年份/期数格式无效、或期数为 0 时抛出
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) < 5:
        raise ValueError(f"{label} 格式无效，请输入完整期号（例如 2026001）。")

    year_text = digits[:4]
    term_text = digits[4:]
    if not year_text.isdigit():
        raise ValueError(f"{label} 年份格式无效")
    if not term_text.isdigit():
        raise ValueError(f"{label} 期数格式无效")

    year = int(year_text)
    term = int(term_text)
    if term == 0:
        raise ValueError(f"{label} 期数不能为 0。")
    return year, term


def list_opened_draws_in_issue_range(
    conn: Any,
    lottery_type_id: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
) -> list[dict[str, Any]]:
    """获取指定彩种、指定期号范围内的已开奖期次列表。

    返回仅包含已开奖（is_opened=1）且在期号范围内的记录，
    号码会规范化为两位数格式（如 "01,15,23,..."）。

    :param conn: 数据库连接对象
    :param lottery_type_id: 彩种类型 ID
    :param start_issue: 起始期号 (year, term) 元组
    :param end_issue: 结束期号 (year, term) 元组
    :return: 已开奖期次列表，每个元素包含 year、term、numbers_str 字段
    """
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

        if current < start_issue:
            continue
        if current > end_issue:
            continue

        raw_numbers = str(row["numbers"] or "")
        normalized_numbers: list[str] = []
        for n in raw_numbers.split(","):
            n = n.strip()
            if not n:
                continue
            try:
                normalized_numbers.append(f"{int(n):02d}")
            except (TypeError, ValueError):
                continue
        if len(normalized_numbers) < 7:
            continue

        draws.append({
            "year": year,
            "term": term,
            "numbers_str": ",".join(normalized_numbers),
        })

    return draws


# ─────────────────────────────────────────────────────────
# 批量生成 & 单表重生成
# Bulk generation & single-table regeneration
# ─────────────────────────────────────────────────────────

def _compute_res_fields(numbers_str: str, zodiac_map: dict, color_map: dict) -> tuple[str, str]:
    """根据开奖号码字符串计算 res_sx（生肖）和 res_color（波色）逗号分隔值。

    内部辅助函数，供批量生成时使用。

    :param numbers_str: 逗号分隔的开奖号码字符串（如 "01,15,23,34,42,08,11"）
    :param zodiac_map: 号码 → 生肖映射字典（{生肖名: [号码列表], ...}）
    :param color_map: 号码 → 波色映射字典（{波色名: [号码列表], ...}）
    :return: (res_sx, res_color) 元组，均为逗号分隔的字符串
    """
    res_sx_parts: list[str] = []
    res_color_parts: list[str] = []
    for num_str in (numbers_str or "").split(","):
        num_str = num_str.strip()
        if not num_str:
            continue
        try:
            num_zf = f"{int(num_str):02d}"
        except ValueError:
            continue
        sx = ""
        for z, codes in zodiac_map.items():
            if num_zf in codes:
                sx = z
                break
        res_sx_parts.append(sx)
        col = ""
        for c, codes in color_map.items():
            if num_zf in codes:
                col = c
                break
        res_color_parts.append(col)
    return ",".join(res_sx_parts), ",".join(res_color_parts)


def bulk_generate_site_prediction_data(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """为站点所选模块批量生成指定期号范围内的预测数据。

    对指定期号范围内的每一期已开奖数据，依次对每个启用的预测模块执行
    ``predict()`` 并写入 created schema 对应的 mode_payload 表中。
    支持以下 payload 字段：

    - ``mechanism_keys``: 要生成的模块 key 列表（list），为空则生成全部启用模块
    - ``lottery_type``: 彩种类型 ID
    - ``start_issue``: 起始期号（如 "2026001"）
    - ``end_issue``: 结束期号（如 "2026127"）

    特殊处理：
    - mode_id=65（特码段数）：不调用 predict()，根据特码直接生成 12 个号码段
    - 台湾彩（lottery_type_id=3）：未开奖期次不传 res_code，防止号码泄露

    :param db_path: 数据库文件路径
    :param site_id: 站点 ID
    :param payload: 批量生成参数字典
    :return: 批量生成报告字典，包含 site_id、site_name、total_modules、
             draw_count、inserted、updated、errors 及各模块详细报告
    :raises ValueError: 当起始期号大于结束期号或范围内无已开奖数据时抛出
    """
    from admin.crud import get_site as _get_site

    site = _get_site(db_path, site_id)
    lottery_type = int(
        payload.get("lottery_type")
        or site.get("lottery_type_id")
        or 3
    )
    start_issue = parse_issue_range_value(payload.get("start_issue"), "起始期号")
    end_issue = parse_issue_range_value(payload.get("end_issue"), "结束期号")

    if start_issue > end_issue:
        raise ValueError("起始期号不能大于结束期号。")

    requested_keys = payload.get("mechanism_keys") or []
    if isinstance(requested_keys, str):
        requested_keys = [k.strip() for k in requested_keys.split(",") if k.strip()]

    with connect(db_path) as conn:
        sync_site_prediction_modules(conn, site_id)
        zodiac_map, color_map = load_fixed_data_maps(conn)

        query = """
            SELECT id, mechanism_key, mode_id, status, sort_order
            FROM site_prediction_modules
            WHERE site_id = ?
              AND status = 1
        """
        params: list[Any] = [site_id]
        if requested_keys:
            placeholders = ", ".join("?" for _ in requested_keys)
            query += f" AND mechanism_key IN ({placeholders})"
            params.extend(requested_keys)
        query += " ORDER BY sort_order, id"

        module_rows = conn.execute(query, params).fetchall()

        draws = list_opened_draws_in_issue_range(conn, lottery_type, start_issue, end_issue)
        if not draws:
            raise ValueError("指定期号范围内没有可用的已开奖数据。")

        # 安全机制：台湾彩 (type=3) 未开奖期次的号码不能用于预测
        safety_draw_map: dict[tuple[int, int], bool] = {}
        if int(lottery_type) == 3:
            safety_rows = conn.execute(
                """
                SELECT year, term, is_opened FROM lottery_draws
                WHERE lottery_type_id = ? AND is_opened = 0
                """,
                (int(lottery_type),),
            ).fetchall()
            for sr in safety_rows:
                safety_draw_map[(int(sr["year"]), int(sr["term"]))] = True

        module_reports: list[dict[str, Any]] = []
        total_inserted = 0
        total_updated = 0
        total_errors = 0

        for module_row in module_rows:
            mechanism_key = str(module_row["mechanism_key"] or "")
            mode_id = int(module_row["mode_id"] or 0)
            config = get_prediction_config(mechanism_key)
            table_name = resolve_prediction_table_for_mode(conn, mode_id, config.default_table)

            module_report: dict[str, Any] = {
                "module_id": int(module_row["id"]),
                "mechanism_key": mechanism_key,
                "mode_id": mode_id,
                "table_name": table_name,
                "draw_count": len(draws),
                "inserted": 0,
                "updated": 0,
                "errors": 0,
                "error_message": "",
            }

            for draw in draws:
                try:
                    draw_key = (draw["year"], draw["term"])
                    # 台湾彩未开奖期次不传 res_code，防止泄密
                    safe_res_code: str | None = draw["numbers_str"]
                    if draw_key in safety_draw_map:
                        safe_res_code = None

                    # ── mode_id=65 特码段数：根据特码生成连续12个号码段 ──
                    if mode_id == 65:
                        numbers = [n.strip() for n in draw["numbers_str"].split(",") if n.strip()]
                        try:
                            special_code = int(numbers[-1]) if numbers else 0
                        except (ValueError, IndexError):
                            special_code = 0

                        if special_code <= 12:
                            content = ",".join(f"{i:02d}" for i in range(1, 13))
                        elif special_code <= 24:
                            content = ",".join(f"{i:02d}" for i in range(13, 25))
                        elif special_code <= 36:
                            content = ",".join(f"{i:02d}" for i in range(25, 37))
                        else:
                            content = ",".join(f"{i:02d}" for i in range(37, 50))

                        row_data = build_generated_prediction_row_data(
                            mode_id=mode_id,
                            lottery_type=str(lottery_type),
                            year=str(draw["year"]),
                            term=str(draw["term"]),
                            web_value="4",
                            res_code=safe_res_code or "",
                            generated_content=content,
                        )
                        row_data["res_sx"], row_data["res_color"] = _compute_res_fields(
                            draw["numbers_str"], zodiac_map, color_map,
                        )
                        stored = upsert_created_prediction_row(conn, table_name, row_data)
                        if stored.get("action") == "inserted":
                            module_report["inserted"] += 1
                            total_inserted += 1
                        else:
                            module_report["updated"] += 1
                            total_updated += 1
                        continue

                    result = predict(
                        config=config,
                        res_code=safe_res_code,
                        source_table=table_name,
                        db_path=db_path,
                        target_hit_rate=DEFAULT_TARGET_HIT_RATE,
                    )
                    row_data = build_generated_prediction_row_data(
                        mode_id=mode_id,
                        lottery_type=str(lottery_type),
                        year=str(draw["year"]),
                        term=str(draw["term"]),
                        web_value="4",
                        res_code=safe_res_code or "",
                        generated_content=result["prediction"]["content"],
                    )
                    # 统一补充 res_sx / res_color，避免 enrich_prediction_result_fields
                    # 因 public 表无历史样本而跳过填充
                    row_data["res_sx"], row_data["res_color"] = _compute_res_fields(
                        draw["numbers_str"], zodiac_map, color_map,
                    )
                    stored = upsert_created_prediction_row(conn, table_name, row_data)
                    if stored.get("action") == "inserted":
                        module_report["inserted"] += 1
                        total_inserted += 1
                    else:
                        module_report["updated"] += 1
                        total_updated += 1
                except Exception as exc:
                    conn.rollback()
                    module_report["errors"] += 1
                    total_errors += 1
                    if not module_report["error_message"]:
                        module_report["error_message"] = str(exc)

            module_reports.append(module_report)

        return {
            "site_id": int(site_id),
            "site_name": str(site.get("name") or ""),
            "lottery_type": lottery_type,
            "start_issue": f"{start_issue[0]}{start_issue[1]}",
            "end_issue": f"{end_issue[0]}{end_issue[1]}",
            "web_id": 4,
            "total_modules": len(module_reports),
            "draw_count": len(draws),
            "inserted": total_inserted,
            "updated": total_updated,
            "errors": total_errors,
            "modules": module_reports,
        }


def regenerate_payload_data(
    db_path: str | Path,
    table_name: str,
    mechanism_key: str = "",
    res_code: str = "",
    lottery_type: str = "3",
    year: str = "",
    term: str = "",
) -> dict[str, Any]:
    """调用 ``predict()`` 生成新预测，覆盖 mode_payload 表中同彩种同期数的数据。

    用于后台"重新生成"单条预测数据的操作。对输入参数进行严格校验：
    - table_name 必须符合 ``mode_payload_{数字}`` 格式
    - res_code 必须为 7 个逗号分隔的数字
    - year 必须为 4 位数字
    - term 必须为 1-5 位数字且不为 0

    特殊处理：
    - mode_id=65（特码段数）：根据特码直接计算 12 个号码段，不调用 predict()

    :param db_path: 数据库文件路径
    :param table_name: 目标 mode_payload 表名（如 "mode_payload_8"）
    :param mechanism_key: 预测机制的唯一标识 key
    :param res_code: 开奖号码（逗号分隔的 7 个数字）
    :param lottery_type: 彩种类型，默认 "3"
    :param year: 年份（4 位数字），可选
    :param term: 期号（1-5 位数字），可选
    :return: 字典，包含 inserted_id、action、created_at、prediction_labels、
             content、table、qualified_table 等字段
    :raises ValueError: 当 mechanism_key 为空、res_code 格式无效、year/term 格式无效、
                        表不存在或生成数据无法匹配目标表列时抛出
    """
    from admin.payload import validate_mode_payload_table as _validate

    table_name = _validate(table_name)
    mechanism_key = str(mechanism_key or "").strip()
    if not mechanism_key:
        raise ValueError("mechanism_key 不能为空")

    res_code = str(res_code or "").strip()
    if res_code:
        codes = [c.strip() for c in res_code.split(",") if c.strip()]
        if len(codes) != 7:
            raise ValueError("开奖号码必须为7个数字，逗号分隔。")
        for c in codes:
            if not re.fullmatch(r"\d{1,2}", c):
                raise ValueError(f"无效号码: {c}")

    year = str(year or "").strip()
    if year and not re.fullmatch(r"\d{4}", year):
        raise ValueError("年份必须为4位数字。")

    term = str(term or "").strip()
    if term and not re.fullmatch(r"\d{1,5}", term):
        raise ValueError("期数必须为1-5位数字。")
    if term and int(term) == 0:
        raise ValueError("期数不能为0。")

    config = get_prediction_config(mechanism_key)
    mode_id = int(config.default_modes_id or 0)

    # ── mode_id=65 特码段数：根据特码生成连续12个号码段 ──
    if mode_id == 65:
        codes_list = [c.strip() for c in res_code.split(",") if c.strip()]
        try:
            special_code = int(codes_list[-1]) if codes_list else 0
        except (ValueError, IndexError):
            special_code = 0

        if special_code <= 12:
            content = ",".join(f"{i:02d}" for i in range(1, 13))
        elif special_code <= 24:
            content = ",".join(f"{i:02d}" for i in range(13, 25))
        elif special_code <= 36:
            content = ",".join(f"{i:02d}" for i in range(25, 37))
        else:
            content = ",".join(f"{i:02d}" for i in range(37, 50))

        with connect(db_path) as conn:
            if not conn.table_exists(table_name):
                raise ValueError(f"表 {table_name} 不存在。")
            zodiac_map, color_map = load_fixed_data_maps(conn)
            columns = set(conn.table_columns(table_name))

            res_sx_parts = []
            res_color_parts = []
            for num_str in codes_list:
                try:
                    num_val = int(num_str)
                    num_zf = f"{num_val:02d}"
                except ValueError:
                    continue
                sx = ""
                for z, codes in zodiac_map.items():
                    if num_zf in codes:
                        sx = z
                        break
                res_sx_parts.append(sx)
                col = ""
                for c, codes in color_map.items():
                    if num_zf in codes:
                        col = c
                        break
                res_color_parts.append(col)

            insert_data: dict[str, Any] = {
                "type": str(lottery_type),
                "year": str(year) if year else "",
                "term": str(term) if term else "",
                "web": "4",
                "web_id": 4,
                "modes_id": 65,
                "res_code": res_code,
                "res_sx": ",".join(res_sx_parts),
                "res_color": ",".join(res_color_parts),
                "content": content,
                "status": 1,
            }

            filtered_data = {k: v for k, v in insert_data.items() if k in columns}
            if not filtered_data:
                raise ValueError("生成的预测数据无法匹配目标表任何列。")

            stored = upsert_created_prediction_row(conn, table_name, filtered_data)
            return {
                "inserted_id": stored.get("id"),
                "action": stored.get("action"),
                "created_at": stored.get("created_at"),
                "prediction_labels": [],
                "content": content,
                "table": stored.get("table"),
                "qualified_table": stored.get("qualified_table"),
            }

    result = predict(
        config=config,
        res_code=res_code or None,
        source_table=table_name,
        db_path=db_path,
        target_hit_rate=DEFAULT_TARGET_HIT_RATE,
    )

    generated_content = result["prediction"]["content"]
    prediction_labels = result["prediction"]["labels"]

    with connect(db_path) as conn:
        if not conn.table_exists(table_name):
            raise ValueError(f"表 {table_name} 不存在。")

        columns = set(conn.table_columns(table_name))

        insert_data: dict[str, Any] = {
            "type": str(lottery_type),
            "year": str(year) if year else "",
            "term": str(term) if term else "",
            "web": "4",
        }

        if res_code:
            insert_data["res_code"] = res_code

        if isinstance(generated_content, dict):
            for key, value in generated_content.items():
                if key == "_labels":
                    continue
                if key in columns:
                    insert_data[key] = value
        elif "content" in columns:
            insert_data["content"] = (
                str(generated_content)
                if isinstance(generated_content, str)
                else json.dumps(generated_content, ensure_ascii=False)
            )

        filtered_data = {k: v for k, v in insert_data.items() if k in columns}
        if not filtered_data:
            raise ValueError("生成的预测数据无法匹配目标表任何列。")

        stored = upsert_created_prediction_row(conn, table_name, filtered_data)

        return {
            "inserted_id": stored.get("id"),
            "action": stored.get("action"),
            "created_at": stored.get("created_at"),
            "prediction_labels": prediction_labels,
            "content": generated_content,
            "table": stored.get("table"),
            "qualified_table": stored.get("qualified_table"),
        }