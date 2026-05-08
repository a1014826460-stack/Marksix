"""Admin 预测管理 — 模块同步/生成/批量操作/安全控制。

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

REQUIRED_SITE_PREDICTION_MODE_IDS = (
    3, 8, 12, 20, 28, 31, 34, 38, 42, 43,
    44, 45, 46, 49, 50, 51, 52, 53, 54, 56,
    57, 58, 59, 60, 61, 62, 63, 64, 65, 66,
    67, 68, 69, 151, 197,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str | Path) -> Any:
    return db_connect(db_path)


def get_site_prediction_module_blueprints() -> list[dict[str, Any]]:
    """返回站点预测模块的标准配置清单，并按前端要求的 mode_id 顺序输出。"""
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
    """按 mechanism_key 获取站点允许使用的模块配置。"""
    for item in get_site_prediction_module_blueprints():
        if str(item["key"]) == str(mechanism_key):
            return item
    raise ValueError(f"机制 {mechanism_key} 不在站点模块同步清单中")


def sync_site_prediction_modules(conn: Any, site_id: int | None = None) -> None:
    """将 site_prediction_modules 与前端站点模块清单保持同步。"""
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

        if allowed_keys:
            placeholders = ", ".join("?" for _ in allowed_keys)
            conn.execute(
                f"""
                DELETE FROM site_prediction_modules
                WHERE site_id = ?
                  AND mechanism_key NOT IN ({placeholders})
                """,
                (current_site_id, *allowed_keys),
            )


# ─────────────────────────────────────────────────────────
# 预测行数据构建
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
) -> dict[str, Any]:
    """将 predict() 的输出转换成 created schema 可直接落库的结构。

    若 term 非空，自动计算三期窗口字段 start=term, end=term-2，
    目标表无 start/end 列时由 upsert 自动忽略。
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

    # 三期窗口自动填充：start=当前term, end=start-2
    # 直接覆盖 formatter 中的旧值，确保 start/end 始终与当前 term 一致
    term_int = int(term) if str(term or "").strip().isdigit() else 0
    if term_int > 0:
        start_val = term_int
        end_val = max(1, start_val - 2)
        if isinstance(generated_content, dict):
            generated_content["start"] = str(start_val)
            generated_content["end"] = str(end_val)

    if isinstance(generated_content, dict):
        for key, value in generated_content.items():
            if key == "_labels":
                continue
            row_data[key] = value
    elif isinstance(generated_content, list):
        row_data["content"] = json.dumps(generated_content, ensure_ascii=False)
    else:
        row_data["content"] = str(generated_content or "")

    return row_data


def normalize_prediction_display_text(content: Any) -> str:
    """将预测内容统一转为前端可直接展示的文本。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (dict, list)):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


# ─────────────────────────────────────────────────────────
# 预测安全控制
# ─────────────────────────────────────────────────────────

def lookup_draw_visibility(
    conn: Any,
    *,
    lottery_type: Any = "",
    year: Any = "",
    term: Any = "",
) -> dict[str, Any]:
    """查询指定期次的开奖可见性，供预测接口做安全策略复用。"""
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
    """统一抹除开奖结果字段，避免未开奖期泄露号码、生肖、波色。"""
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
    """根据开奖状态决定是否需要对预测行做安全处理。"""
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
    """检查预测请求是否允许携带 `res_code` 参与算法。

    若目标期次已开奖，则拒绝携带 res_code（返回 None），防止利用已知结果作弊。
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
# API 响应构建
# ─────────────────────────────────────────────────────────

def build_prediction_api_response(
    *,
    mechanism_key: str,
    request_payload: dict[str, Any],
    raw_result: dict[str, Any],
    safety: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """将 `predict()` 的原始返回包装成对外稳定的 HTTP 协议。"""
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
# ─────────────────────────────────────────────────────────

def parse_issue_range_value(value: Any, label: str) -> tuple[int, int]:
    """解析前端传入的期号范围值，格式示例：2026001 / 2026-001。"""
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
    """获取指定彩种、指定期号范围内的已开奖期次。"""
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
# ─────────────────────────────────────────────────────────

def bulk_generate_site_prediction_data(
    db_path: str | Path,
    site_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """为站点所选模块批量生成指定期号范围内的预测数据。

    payload 可选字段:
    - mechanism_keys: 要生成的模块 key 列表，为空则生成全部
    - lottery_type / start_issue / end_issue: 期号范围
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
            table_name = config.default_table or f"mode_payload_{mode_id}"

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
    """调用 predict() 生成新预测，覆盖 mode_payload 表中同彩种同期数的数据。"""
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
