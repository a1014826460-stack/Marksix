"""预测资料批量生成服务。

编排站点预测模块的批量生成流程：
站点上下文解析 → 模块加载 → 期号范围加载 → 逐模块逐期生成 → 持久化。
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import logging
import random as _random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db import connect
from helpers import load_fixed_data_maps
from predict.common import predict
from predict.mechanisms import get_prediction_config
from predict.number_maps import SIZE_NUMBER_MAP
from prediction_generation.diversity import enforce_prediction_diversity
from runtime_config import get_config_from_conn
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    find_existing_created_row,
    normalize_color_label,
    table_column_names,
    upsert_created_prediction_row,
)

_logger = logging.getLogger("prediction.service")
_task_logger = logging.getLogger("prediction.task")


# ── 配置读取 ────────────────────────────────────────────


def _default_target_hit_rate(conn: Any) -> float:
    return float(get_config_from_conn(conn, "prediction.default_target_hit_rate", 0.65))


def _max_terms_per_year(conn: Any) -> int:
    return int(get_config_from_conn(conn, "prediction.max_terms_per_year", 365))


# ── 工具函数 ────────────────────────────────────────────


def compute_result_fields(numbers_str: str, zodiac_map: dict, color_map: dict) -> tuple[str, str]:
    res_sx_parts: list[str] = []
    res_color_parts: list[str] = []
    for num_str in (numbers_str or "").split(","):
        raw_num = num_str.strip()
        if not raw_num:
            continue
        try:
            num_zf = f"{int(raw_num):02d}"
        except ValueError:
            continue
        res_sx_parts.append(str(zodiac_map.get(num_zf) or ""))
        res_color_parts.append(normalize_color_label(color_map.get(num_zf, "")))
    return (
        ",".join(res_sx_parts) if any(res_sx_parts) else "",
        ",".join(res_color_parts) if any(res_color_parts) else "",
    )


def compute_next_issue(year: int, term: int, offset: int, *, max_terms_per_year: int = 365) -> tuple[int, int]:
    new_term = term + offset
    new_year = year
    while new_term > max_terms_per_year:
        new_term -= max_terms_per_year
        new_year += 1
    return new_year, new_term


def _make_seed_int(seed_str: str) -> int:
    """从种子字符串生成 32 位整数种子。"""
    return int(_hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)


# ── 期号与开奖数据加载 ──────────────────────────────────


def list_opened_draws_in_issue_range(
    conn: Any,
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

        normalized_numbers: list[str] = []
        for raw_number in str(row["numbers"] or "").split(","):
            text = raw_number.strip()
            if not text:
                continue
            try:
                normalized_numbers.append(f"{int(text):02d}")
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


def find_latest_opened_draw_before_issue(
    conn: Any,
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

        normalized_numbers: list[str] = []
        for raw_number in str(row["numbers"] or "").split(","):
            text = raw_number.strip()
            if not text:
                continue
            try:
                normalized_numbers.append(f"{int(text):02d}")
            except (TypeError, ValueError):
                continue
        if len(normalized_numbers) < 7:
            continue

        return {"year": year, "term": term, "numbers_str": ",".join(normalized_numbers)}
    return None


def _build_future_draws(
    draws: list[dict[str, Any]],
    future_periods: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    future_only: bool,
    max_terms_per_year: int,
) -> list[dict[str, Any]]:
    """根据已开奖期号推算未来期号列表。"""
    if int(future_periods or 0) <= 0:
        return []

    latest = draws[-1]
    generated: list[dict[str, Any]] = []
    for offset in range(1, int(future_periods) + 1):
        next_year, next_term = compute_next_issue(
            latest["year"], latest["term"], offset,
            max_terms_per_year=max_terms_per_year,
        )
        generated.append({
            "year": next_year,
            "term": next_term,
            "numbers_str": "",
            "_future": True,
        })

    if future_only:
        return [
            d for d in generated
            if start_issue <= (d["year"], d["term"]) <= end_issue
        ]
    return generated


def _build_safety_draw_map(conn: Any, lottery_type: int) -> dict[tuple[int, int], bool]:
    """构建未开奖期号的安全映射（仅对 type=3）。"""
    safety: dict[tuple[int, int], bool] = {}
    if int(lottery_type) != 3:
        return safety
    rows = conn.execute(
        """
        SELECT year, term, is_opened FROM lottery_draws
        WHERE lottery_type_id = ? AND is_opened = 0
        """,
        (int(lottery_type),),
    ).fetchall()
    for row in rows:
        safety[(int(row["year"]), int(row["term"]))] = True
    return safety


# ── 站点上下文解析 ──────────────────────────────────────


def _resolve_generation_context(db_path: str | Path, site_id: int) -> tuple[int, str]:
    """解析站点 web_id 和名称，校验 web_id 有效性。

    Returns:
        (site_web_id, site_name)
    """
    from domains.sites.service import get_site

    site = get_site(db_path, site_id)
    site_web_id = int(site.get("web_id") or 0)
    if site_web_id <= 0:
        raise ValueError(f"site_id={site_id} 缺少有效 web_id")
    return site_web_id, str(site.get("name") or "")


# ── 最近行加载（多样性用）────────────────────────────────


def _load_recent_rows(
    conn: Any,
    table_name: str,
    lottery_type: int,
    site_web_id: int,
    mode_id: int,
) -> list[dict[str, Any]]:
    """加载指定模式最近已持久化的行，用于跨期多样性校验。"""
    try:
        created_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
        if "content" not in created_columns:
            return []
        created_table = f"{CREATED_SCHEMA_NAME}.{table_name}"
        existing = conn.execute(
            f"SELECT content FROM {created_table} "
            f"WHERE type = ? AND web = ? AND modes_id = ? "
            f"ORDER BY year DESC, term DESC LIMIT 10",
            (str(lottery_type), str(site_web_id), mode_id),
        ).fetchall()
        return [{"content": row["content"]} for row in existing]
    except Exception:
        conn.rollback()
        return []


# ── 单期行生成（按 mode_id 分发）────────────────────────


def _resolve_safe_res_code(draw: dict[str, Any], draw_key: tuple, safety_map: dict) -> str | None:
    """解析安全开奖号码：若该期尚未开奖则返回 None，避免注入真实 res_code。"""
    if draw_key in safety_map:
        return None
    return draw["numbers_str"]


def _generate_mode_65_row(
    draw: dict[str, Any],
    is_future: bool,
    lottery_type: int,
    site_web_id: int,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=65：根据特码范围生成分组号码。"""
    if is_future:
        seed_int = _make_seed_int(f"{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
        special_code = _random.randint(1, 49)
    else:
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

    return build_row(
        mode_id=65, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id),
        res_code=_resolve_safe_res_code(draw, (draw["year"], draw["term"]), {}) or "",
        generated_content=content,
    )


def _generate_mode_108_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=108：大小中特带1头。"""
    if is_future:
        result = predict(
            config=config, res_code=None, source_table=table_name,
            db_path=db_path, target_hit_rate=default_target_hit_rate,
            random_seed=f"{draw['year']}{draw['term']:03d}",
        )
        predicted_size = str(result["prediction"]["labels"][0])
        seed_int = _make_seed_int(f"{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
        size_numbers = SIZE_NUMBER_MAP.get(predicted_size, [])
        chosen_number = _random.choice(size_numbers) if size_numbers else "00"
    else:
        numbers = [n.strip() for n in (safe_res_code or "").split(",") if n.strip()]
        try:
            special_code = int(numbers[-1]) if numbers else 0
        except (ValueError, IndexError):
            special_code = 0
        chosen_number = f"{special_code:02d}"
        predicted_size = "大" if special_code >= 25 else "小"

    num_val = int(chosen_number) if chosen_number.lstrip("0") else 0
    if 10 <= num_val <= 19:
        head_text = "1头"
    elif 20 <= num_val <= 29:
        head_text = "2头"
    elif 30 <= num_val <= 39:
        head_text = "3头"
    elif 40 <= num_val <= 49:
        head_text = "4头"
    else:
        head_text = "0头"

    return build_row(
        mode_id=108, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content={
            "content": [f"{predicted_size}|{chosen_number}"],
            "tou": [head_text],
        },
    )


def _generate_mode_246_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    build_row: Any,
) -> dict[str, Any]:
    """mode_id=246：七肖七码（正常预测 + 随机平特生肖）。"""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name, db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
    )
    row_data = build_row(
        mode_id=246, lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )
    if is_future:
        seed_int = _make_seed_int(f"ping_{draw['year']}{draw['term']:03d}")
        _random.seed(seed_int)
    row_data["ping"] = _random.choice(list({v for v in zodiac_map.values() if v}))
    return row_data


def _generate_default_mode_row(
    draw: dict[str, Any],
    is_future: bool,
    safe_res_code: str | None,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    build_row: Any,
    lottery_type: int,
    site_web_id: int,
) -> dict[str, Any]:
    """通用模式：调用 predict() 生成预测内容。"""
    result = predict(
        config=config,
        res_code=None if is_future else safe_res_code,
        source_table=table_name, db_path=db_path,
        target_hit_rate=default_target_hit_rate,
        random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
    )
    return build_row(
        mode_id=config.default_modes_id,
        lottery_type=str(lottery_type),
        year=str(draw["year"]), term=str(draw["term"]),
        web_value=str(site_web_id), res_code=safe_res_code or "",
        generated_content=result["prediction"]["content"],
    )


def _generate_single_draw_row(
    draw: dict[str, Any],
    mode_id: int,
    is_future: bool,
    safe_res_code: str | None,
    lottery_type: int,
    site_web_id: int,
    config: Any,
    table_name: str,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    build_row: Any,
) -> dict[str, Any]:
    """根据 mode_id 分发生成单期预测行。"""
    if mode_id == 65:
        return _generate_mode_65_row(draw, is_future, lottery_type, site_web_id, build_row)
    if mode_id == 108:
        return _generate_mode_108_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, build_row,
        )
    if mode_id == 246:
        return _generate_mode_246_row(
            draw, is_future, safe_res_code, lottery_type, site_web_id,
            config, table_name, db_path, default_target_hit_rate, zodiac_map, build_row,
        )
    return _generate_default_mode_row(
        draw, is_future, safe_res_code, config, table_name, db_path,
        default_target_hit_rate, build_row, lottery_type, site_web_id,
    )


def _persist_generated_row(
    conn: Any,
    table_name: str,
    row_data: dict[str, Any],
    *,
    allow_overwrite: bool,
) -> dict[str, Any]:
    """持久化单行预测结果，自动任务默认只插入缺失行。"""
    if not allow_overwrite:
        existing = find_existing_created_row(conn, table_name, row_data)
        if existing:
            return {
                "action": "skipped_existing",
                "schema": CREATED_SCHEMA_NAME,
                "table": table_name,
                "id": str(existing["id"]),
                "created_at": str(existing["created_at"] or ""),
            }
    return upsert_created_prediction_row(conn, table_name, row_data)


# ── 结构化模块日志 ──────────────────────────────────────


def _write_task_log_to_db(
    db_path: str | Path,
    level: str,
    message: str,
    site_id: int = 0,
    web_id: int = 0,
    lottery_type_id: int = 0,
) -> None:
    """将预测任务日志直接写入 error_logs 表，确保后台日志管理页面可见。"""
    try:
        with connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO error_logs (
                    created_at, level, logger_name, module, func_name,
                    file_path, line_number, message,
                    site_id, web_id, lottery_type_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    level,
                    "prediction.task",
                    "prediction_generation",
                    "_log_module_result",
                    __file__, 0,
                    message,
                    site_id, web_id, lottery_type_id,
                ),
            )
    except Exception:
        pass


def _log_module_result(
    *,
    db_path: str | Path,
    site_id: int,
    site_name: str,
    site_web_id: int,
    lottery_type: int,
    mode_id: int,
    mechanism_key: str,
    report: dict[str, Any],
    elapsed_ms: float,
    trigger: str,
) -> None:
    """输出单个预测模块处理结果的结构化 JSON 日志（文件 + 数据库双写）。"""
    has_error = report.get("errors", 0) > 0
    has_changes = report.get("inserted", 0) > 0 or report.get("updated", 0) > 0

    if has_error:
        status = "error"
    elif has_changes:
        status = "updated"
    else:
        status = "unchanged"

    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "site_id": site_id,
        "site_name": site_name,
        "web_id": site_web_id,
        "lottery_type": lottery_type,
        "mode_id": mode_id,
        "mechanism_key": mechanism_key,
        "table": report.get("table_name", ""),
        "status": status,
        "draw_count": report.get("draw_count", 0),
        "inserted": report.get("inserted", 0),
        "updated": report.get("updated", 0),
        "skipped_existing": report.get("skipped_existing", 0),
        "errors": report.get("errors", 0),
        "elapsed_ms": elapsed_ms,
        "trigger": trigger,
    }

    if report.get("error_message"):
        log_entry["error_message"] = str(report["error_message"])
    if report.get("warnings"):
        log_entry["warnings"] = report["warnings"]

    json_msg = _json.dumps(log_entry, ensure_ascii=False)

    if has_error:
        _task_logger.warning("Module result: %s", json_msg)
        _write_task_log_to_db(db_path, "WARNING", json_msg,
                              site_id=site_id, web_id=site_web_id, lottery_type_id=lottery_type)
    else:
        _task_logger.info("Module result: %s", json_msg)
        if has_changes:
            _write_task_log_to_db(db_path, "INFO", json_msg,
                                  site_id=site_id, web_id=site_web_id, lottery_type_id=lottery_type)


# ── 单模块处理 ───────────────────────────────────────────


def _process_single_module(
    conn: Any,
    module_row: dict[str, Any],
    draws: list[dict[str, Any]],
    future_draws: list[dict[str, Any]],
    future_only: bool,
    safety_draw_map: dict,
    lottery_type: int,
    site_web_id: int,
    db_path: str | Path,
    default_target_hit_rate: float,
    zodiac_map: dict,
    color_map: dict,
    trigger: str,
    allow_overwrite: bool,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """处理单个模块的所有期号，返回模块报告。"""
    mechanism_key = str(module_row["mechanism_key"] or "")
    mode_id = int(module_row["mode_id"] or 0)

    module_report: dict[str, Any] = {
        "module_id": int(module_row["id"]),
        "mechanism_key": mechanism_key,
        "mode_id": mode_id,
        "table_name": f"mode_payload_{mode_id}" if mode_id > 0 else "",
        "draw_count": len(draws),
        "inserted": 0,
        "updated": 0,
        "skipped_existing": 0,
        "errors": 0,
        "error_message": "",
        "warnings": [],
        "trigger": trigger,
    }

    try:
        config = get_prediction_config(mechanism_key)
        table_name = resolve_prediction_table_for_mode(conn, mode_id, config.default_table)
        module_report["table_name"] = table_name
    except Exception as exc:
        conn.rollback()
        module_report["errors"] += 1
        module_report["error_message"] = str(exc)
        module_report["warnings"].append("module skipped because prediction config/table is unavailable")
        _logger.error(
            "Module generation skipped: mode_id=%d, key=%s — %s",
            mode_id, mechanism_key, exc,
        )
        return module_report

    recent_rows = _load_recent_rows(conn, table_name, lottery_type, site_web_id, mode_id)
    all_target_draws = list(future_draws) if future_only else list(draws) + list(future_draws)

    for draw in all_target_draws:
        try:
            is_future = bool(draw.get("_future"))
            draw_key = (draw["year"], draw["term"])
            safe_res_code = _resolve_safe_res_code(draw, draw_key, safety_draw_map)

            row_data = _generate_single_draw_row(
                draw=draw, mode_id=mode_id, is_future=is_future,
                safe_res_code=safe_res_code, lottery_type=lottery_type,
                site_web_id=site_web_id, config=config, table_name=table_name,
                db_path=db_path, default_target_hit_rate=default_target_hit_rate,
                zodiac_map=zodiac_map, build_row=build_generated_prediction_row_data,
            )

            if is_future:
                row_data["res_sx"] = ""
                row_data["res_color"] = ""
            else:
                row_data["res_sx"], row_data["res_color"] = compute_result_fields(
                    draw["numbers_str"], zodiac_map, color_map,
                )

            row_data = enforce_prediction_diversity(
                mode_id=mode_id, row_data=row_data,
                recent_rows=recent_rows, config=config,
            )
            diversity_warning = row_data.pop("_diversity_warning", None)
            if diversity_warning:
                module_report["warnings"].append(str(diversity_warning))

            stored = _persist_generated_row(
                conn,
                table_name,
                row_data,
                allow_overwrite=allow_overwrite,
            )
            if stored.get("action") == "inserted":
                module_report["inserted"] += 1
                recent_rows.insert(0, {"content": row_data.get("content")})
            elif stored.get("action") == "updated":
                module_report["updated"] += 1
                recent_rows.insert(0, {"content": row_data.get("content")})
            else:
                module_report["skipped_existing"] += 1
        except Exception as exc:
            conn.rollback()
            module_report["errors"] += 1
            if not module_report["error_message"]:
                module_report["error_message"] = str(exc)
            _logger.error(
                "Module generation error: mode_id=%d, key=%s, draw=%s/%d, future=%s — %s",
                mode_id, mechanism_key, draw.get("year"), draw.get("term"),
                draw.get("_future", False), exc,
            )

    return module_report


# ── 主入口 ──────────────────────────────────────────────


def generate_prediction_batch(
    db_path: str | Path,
    *,
    site_id: int,
    lottery_type: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    mechanism_keys: list[str] | None,
    future_periods: int,
    future_only: bool,
    trigger: str,
    allow_overwrite: bool = True,
    sync_site_modules: Any,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """批量生成预测资料的编排入口。

    params:
    - db_path: 数据库目标。
    - site_id: 站点 ID。
    - lottery_type: 彩种类型 ID。
    - start_issue / end_issue: 期号范围 (year, term)。
    - mechanism_keys: 要生成的机制键列表（None 表示全部）。
    - future_periods: 未来期号数量。
    - future_only: 是否只生成未来期。
    - trigger: 触发来源标识。
    - allow_overwrite: 是否允许覆盖既有 created 预测正文。
    - sync_site_modules / resolve_prediction_table_for_mode /
      build_generated_prediction_row_data: 回调函数。

    returns:
        生成结果摘要字典。
    """
    _t_start = time.perf_counter()
    requested_keys = list(mechanism_keys or [])

    _logger.info(
        "Batch generation started: site_id=%d, keys=%s, range=%s-%s, future=%d, future_only=%s, trigger=%s",
        site_id, requested_keys or ["all"],
        f"{start_issue[0]}{start_issue[1]:03d}",
        f"{end_issue[0]}{end_issue[1]:03d}",
        future_periods, bool(future_only), trigger,
    )

    site_web_id, site_name = _resolve_generation_context(db_path, site_id)

    with connect(db_path) as conn:
        sync_site_modules(conn, site_id)
        zodiac_map, color_map = load_fixed_data_maps(conn)
        default_target_hit_rate = _default_target_hit_rate(conn)
        max_terms_per_year = _max_terms_per_year(conn)

        module_rows = conn.execute(
            """
            SELECT id, mechanism_key, mode_id, status, sort_order
            FROM site_prediction_modules
            WHERE site_id = ? AND status = 1
            """
            + (
                f" AND mechanism_key IN ({', '.join('?' for _ in requested_keys)})"
                if requested_keys else ""
            )
            + " ORDER BY sort_order, id",
            [site_id] + (requested_keys if requested_keys else []),
        ).fetchall()

        draws = list_opened_draws_in_issue_range(conn, lottery_type, start_issue, end_issue)
        if not draws and future_only and int(future_periods or 0) > 0:
            fallback_draw = find_latest_opened_draw_before_issue(conn, lottery_type, start_issue)
            if fallback_draw:
                draws = [fallback_draw]
        # 纯未来期生成时，若无任何已开奖记录，用 start_issue 的前一期作为推算基准
        if not draws and future_only and int(future_periods or 0) > 0:
            ref_year, ref_term = start_issue
            if ref_term > 1:
                ref_term -= 1
            else:
                ref_year -= 1
                ref_term = max_terms_per_year
            draws = [{"year": ref_year, "term": ref_term, "numbers_str": ""}]
        if not draws:
            raise ValueError("指定期号范围内没有可用的已开奖数据。")

        future_draws = _build_future_draws(
            draws, future_periods, start_issue, end_issue,
            future_only, max_terms_per_year,
        )
        safety_draw_map = _build_safety_draw_map(conn, lottery_type)

        module_reports: list[dict[str, Any]] = []
        total_inserted = 0
        total_updated = 0
        total_skipped_existing = 0
        total_errors = 0

        for module_row in module_rows:
            mechanism_key = str(module_row["mechanism_key"] or "")
            mode_id = int(module_row["mode_id"] or 0)
            module_t0 = time.perf_counter()

            report = _process_single_module(
                conn=conn, module_row=module_row, draws=draws,
                future_draws=future_draws, future_only=future_only,
                safety_draw_map=safety_draw_map, lottery_type=int(lottery_type),
                site_web_id=site_web_id, db_path=db_path,
                default_target_hit_rate=default_target_hit_rate,
                zodiac_map=zodiac_map, color_map=color_map,
                trigger=trigger, allow_overwrite=bool(allow_overwrite),
                resolve_prediction_table_for_mode=resolve_prediction_table_for_mode,
                build_generated_prediction_row_data=build_generated_prediction_row_data,
            )
            module_reports.append(report)
            total_inserted += report["inserted"]
            total_updated += report["updated"]
            total_skipped_existing += report["skipped_existing"]
            total_errors += report["errors"]

            # 结构化日志：每个模块的处理结果
            _log_module_result(
                db_path=db_path,
                site_id=int(site_id), site_name=site_name,
                site_web_id=site_web_id, lottery_type=int(lottery_type),
                mode_id=mode_id, mechanism_key=mechanism_key,
                report=report, elapsed_ms=round((time.perf_counter() - module_t0) * 1000, 1),
                trigger=trigger,
            )

        elapsed_s = round(time.perf_counter() - _t_start, 2)
        _logger.info(
            "Batch generation completed: modules=%d, draws=%d, inserted=%d, updated=%d, skipped_existing=%d, errors=%d, elapsed=%.1fs",
            len(module_reports), len(draws), total_inserted, total_updated,
            total_skipped_existing, total_errors, elapsed_s,
        )
        if total_errors > 0:
            _logger.warning(
                "Batch generation had %d errors across %d modules",
                total_errors,
                sum(1 for m in module_reports if m.get("errors", 0) > 0),
            )

        # 站点级汇总日志
        _task_logger.info(
            "Site summary: %s",
            _json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "site_id": int(site_id),
                "site_name": site_name,
                "web_id": site_web_id,
                "lottery_type": int(lottery_type),
                "start_issue": f"{start_issue[0]}{start_issue[1]:03d}",
                "end_issue": f"{end_issue[0]}{end_issue[1]:03d}",
                "total_modules": len(module_reports),
                "draw_count": len(draws),
                "future_periods": int(future_periods or 0),
                "future_only": bool(future_only),
                "inserted": total_inserted,
                "updated": total_updated,
                "skipped_existing": total_skipped_existing,
                "errors": total_errors,
                "elapsed_s": elapsed_s,
                "trigger": trigger,
                "allow_overwrite": bool(allow_overwrite),
            }, ensure_ascii=False),
        )

        return {
            "site_id": int(site_id),
            "site_name": site_name,
            "lottery_type": int(lottery_type),
            "start_issue": f"{start_issue[0]}{start_issue[1]}",
            "end_issue": f"{end_issue[0]}{end_issue[1]}",
            "web_id": site_web_id,
            "future_periods": int(future_periods or 0),
            "future_only": bool(future_only),
            "total_modules": len(module_reports),
            "draw_count": len(draws),
            "inserted": total_inserted,
            "updated": total_updated,
            "skipped_existing": total_skipped_existing,
            "errors": total_errors,
            "trigger": trigger,
            "allow_overwrite": bool(allow_overwrite),
            "modules": module_reports,
        }
