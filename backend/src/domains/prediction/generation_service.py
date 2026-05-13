"""预测资料生成服务。

包含模块同步、期号解析、表解析、行数据构建等核心生成函数。
这些函数原本分散在 admin/prediction.py 中，现集中于此以避免 domains → admin 反向依赖。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from db import connect, quote_identifier, utc_now
from helpers import (
    load_fixed_data_maps,
    parse_bool,
    REQUIRED_SITE_PREDICTION_MODE_IDS,
)
from predict.mechanisms import get_prediction_config, list_prediction_configs
from utils.created_prediction_store import (
    normalize_color_label,
    upsert_created_prediction_row,
)

_logger = logging.getLogger("domains.prediction.generation")


# ── 模块蓝图 ────────────────────────────────────────────


def get_site_prediction_module_blueprints() -> list[dict[str, Any]]:
    """获取站点预测模块的标准配置清单。"""
    configs_by_mode_id: dict[int, dict[str, Any]] = {}
    for item in list_prediction_configs():
        try:
            configs_by_mode_id[int(item["default_modes_id"])] = item
        except (TypeError, ValueError):
            continue

    missing = [mode_id for mode_id in REQUIRED_SITE_PREDICTION_MODE_IDS if mode_id not in configs_by_mode_id]
    if missing:
        _logger.warning("以下 mode_id 暂无预测配置，同步时跳过: %s", missing)

    blueprints: list[dict[str, Any]] = []
    for index, mode_id in enumerate(REQUIRED_SITE_PREDICTION_MODE_IDS):
        if mode_id not in configs_by_mode_id:
            continue
        item = dict(configs_by_mode_id[mode_id])
        item["mode_id"] = int(mode_id)
        item["sort_order"] = index * 10
        blueprints.append(item)
    return blueprints


def get_site_prediction_module_blueprint_by_key(mechanism_key: str) -> dict[str, Any]:
    """按 mechanism_key 获取站点允许使用的模块配置。"""
    for item in get_site_prediction_module_blueprints():
        if str(item["key"]) == str(mechanism_key):
            return item
    raise ValueError(f"机制 {mechanism_key} 不在站点模块同步清单中")


# ── 模块同步 ────────────────────────────────────────────


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """将 site_prediction_modules 表与前端站点模块清单保持同步。"""
    blueprints = get_site_prediction_module_blueprints()
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


# ── 表解析 ──────────────────────────────────────────────


def resolve_prediction_table_for_mode(
    conn: Any,
    mode_id: int,
    fallback_table: str = "",
) -> str:
    """根据 mode_id 从 mode_payload_tables 解析对应的数据表名。"""
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


# ── 期号范围解析 ────────────────────────────────────────


def parse_issue_range_value(value: Any, label: str) -> tuple[int, int]:
    """解析前端传入的期号范围值，返回 (year, term) 元组。"""
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


# ── 预测行数据构建 ──────────────────────────────────────


def build_generated_prediction_row_data(
    *,
    mode_id: int,
    lottery_type: str = "",
    year: str = "",
    term: str = "",
    web_value: str = "",
    res_code: str = "",
    generated_content: Any,
    db_path: str | Path = "",
) -> dict[str, Any]:
    """将 predict() 的输出转换成 created schema 可直接落库的行数据结构。"""
    web_val = str(web_value or "").strip()
    if not web_val:
        raise ValueError("web_value 不能为空")
    if not web_val.isdigit():
        raise ValueError("web_value 必须为整数")
    row_data: dict[str, Any] = {
        "type": str(lottery_type or ""),
        "year": str(year or ""),
        "term": str(term or ""),
        "web": web_val,
        "web_id": int(web_val),
        "modes_id": int(mode_id) if mode_id else 0,
        "res_code": str(res_code or ""),
    }

    if res_code and db_path:
        codes = [c.strip() for c in str(res_code).split(",") if c.strip()]
        if len(codes) == 7:
            special = codes[-1]
            with connect(db_path) as _tmp_conn:
                zmap, cmap = load_fixed_data_maps(_tmp_conn)
            row_data["res_sx"] = zmap.get(special, "")
            color = cmap.get(special, "")
            if color:
                row_data["res_color"] = normalize_color_label(color)

    term_int = int(term) if str(term or "").strip().isdigit() else 0
    if term_int > 0:
        rem = term_int % 3
        if rem == 2:
            start_val = term_int
        elif rem == 0:
            start_val = max(1, term_int - 1)
        else:
            start_val = max(1, term_int - 2)
        end_val = start_val + 2
        if isinstance(generated_content, dict):
            generated_content["start"] = str(start_val)
            generated_content["end"] = str(end_val)

    if isinstance(generated_content, dict):
        for key, value in generated_content.items():
            if key == "_labels":
                continue
            if isinstance(value, (list, dict, tuple, set)):
                row_data[key] = json.dumps(value, ensure_ascii=False)
            else:
                row_data[key] = value
    elif isinstance(generated_content, list):
        row_data["content"] = json.dumps(generated_content, ensure_ascii=False)
    else:
        row_data["content"] = str(generated_content or "")

    return row_data
