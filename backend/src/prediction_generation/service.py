from __future__ import annotations

import hashlib as _hashlib
import logging
import random as _random
import time
from pathlib import Path
from typing import Any

from common import predict
from db import connect
from helpers import load_fixed_data_maps
from mechanisms import SIZE_NUMBER_MAP, get_prediction_config
from prediction_generation.diversity import enforce_prediction_diversity
from runtime_config import get_config_from_conn

_logger = logging.getLogger("prediction.service")
from utils.created_prediction_store import (
    CREATED_SCHEMA_NAME,
    table_column_names,
    upsert_created_prediction_row,
)


def _default_target_hit_rate(conn: Any) -> float:
    return float(get_config_from_conn(conn, "prediction.default_target_hit_rate", 0.65))


def _max_terms_per_year(conn: Any) -> int:
    return int(get_config_from_conn(conn, "prediction.max_terms_per_year", 365))


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
        sx = ""
        for zodiac_name, codes in zodiac_map.items():
            if num_zf in codes:
                sx = zodiac_name
                break
        res_sx_parts.append(sx)
        color = ""
        for color_name, codes in color_map.items():
            if num_zf in codes:
                color = color_name
                break
        res_color_parts.append(color)
    return ",".join(res_sx_parts), ",".join(res_color_parts)


def compute_next_issue(year: int, term: int, offset: int, *, max_terms_per_year: int = 365) -> tuple[int, int]:
    new_term = term + offset
    new_year = year
    while new_term > max_terms_per_year:
        new_term -= max_terms_per_year
        new_year += 1
    return new_year, new_term


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

        draws.append(
            {
                "year": year,
                "term": term,
                "numbers_str": ",".join(normalized_numbers),
            }
        )
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

        return {
            "year": year,
            "term": term,
            "numbers_str": ",".join(normalized_numbers),
        }
    return None


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
    sync_site_modules: Any,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """Shared batch generation service.

    This is the canonical orchestration point for admin, automation, and CLI wrappers.
    
    共享批量生成服务。

    这是管理、自动化和命令行界面（CLI）包装器的标准编排点。

    params:
    - db_path: 数据库文件路径，支持字符串或Path对象。
    - site_id: 生成预测的站点ID。
    - lottery_type: 彩票类型ID。
    - start_issue: 生成预测的起始期号，格式为(year, term)。
    - end_issue: 生成预测的结束期号，格式为(year, term)。
    - mechanism_keys: 可选的机制键列表，用于过滤要生成的模块；如果为None或空列表，则生成所有模块。
    - future_periods: 未来期号的数量，生成时会基于最后一个已开奖的期号进行推算。
    - trigger: 触发生成的来源标识，如"admin_manual"、"scheduled_task"等。
    - sync_site_modules: 同步站点模块的函数，接受数据库连接和站点ID作为参数。
    - resolve_prediction_table_for_mode: 根据模式ID和默认表名解析实际使用的预测表名的函数，接受数据库连接、模式ID和默认表名作为参数。
    - build_generated_prediction_row_data: 构建生成的预测行数据的函数，接受模式ID、彩票类型、年、期、web值、开奖号码和生成内容等参数，返回一个包含预测数据的字典。
    returns:
    - dict[str, Any]: 包含生成结果摘要和详细模块报告的字典。
    """
    from admin.crud import get_site as _get_site

    _t_start = time.perf_counter()
    site = _get_site(db_path, site_id)
    requested_keys = list(mechanism_keys or [])

    _logger.info(
        "Batch generation started: site_id=%d, keys=%s, range=%s-%s, future=%d, future_only=%s, trigger=%s",
        site_id, requested_keys or ["all"], f"{start_issue[0]}{start_issue[1]:03d}",
        f"{end_issue[0]}{end_issue[1]:03d}", future_periods, bool(future_only), trigger,
    )

    with connect(db_path) as conn:
        sync_site_modules(conn, site_id)
        zodiac_map, color_map = load_fixed_data_maps(conn)
        default_target_hit_rate = _default_target_hit_rate(conn)
        max_terms_per_year = _max_terms_per_year(conn)

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
        if not draws and future_only and int(future_periods or 0) > 0:
            fallback_draw = find_latest_opened_draw_before_issue(conn, lottery_type, start_issue)
            if fallback_draw:
                draws = [fallback_draw]
        if not draws:
            raise ValueError("指定期号范围内没有可用的已开奖数据。")

        future_draws: list[dict[str, Any]] = []
        if int(future_periods or 0) > 0:
            latest = draws[-1]
            generated_future_draws: list[dict[str, Any]] = []
            for offset in range(1, int(future_periods) + 1):
                next_year, next_term = compute_next_issue(
                    latest["year"],
                    latest["term"],
                    offset,
                    max_terms_per_year=max_terms_per_year,
                )
                generated_future_draws.append(
                    {
                        "year": next_year,
                        "term": next_term,
                        "numbers_str": "",
                        "_future": True,
                    }
                )
            future_draws = [
                draw for draw in generated_future_draws
                if start_issue <= (draw["year"], draw["term"]) <= end_issue
            ] if future_only else generated_future_draws

        safety_draw_map: dict[tuple[int, int], bool] = {}
        if int(lottery_type) == 3:
            safety_rows = conn.execute(
                """
                SELECT year, term, is_opened FROM lottery_draws
                WHERE lottery_type_id = ? AND is_opened = 0
                """,
                (int(lottery_type),),
            ).fetchall()
            for row in safety_rows:
                safety_draw_map[(int(row["year"]), int(row["term"]))] = True

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
                "warnings": [],
                "trigger": trigger,
            }

            # 查询该模块最近已持久化的行，用于跨期多样性校验
            recent_rows: list[dict[str, Any]] = []
            try:
                created_columns = set(table_column_names(conn, CREATED_SCHEMA_NAME, table_name))
                if "content" in created_columns:
                    created_table = f"{CREATED_SCHEMA_NAME}.{table_name}"
                    existing = conn.execute(
                        f"SELECT content FROM {created_table} "
                        f"WHERE type = ? AND web = ? AND modes_id = ? "
                        f"ORDER BY year DESC, term DESC LIMIT 10",
                        (str(lottery_type), "4", mode_id),
                    ).fetchall()
                    recent_rows = [{"content": row["content"]} for row in existing]
            except Exception:
                conn.rollback()
                recent_rows = []

            all_target_draws = list(future_draws) if future_only else list(draws) + list(future_draws)
            for draw in all_target_draws:
                try:
                    is_future = bool(draw.get("_future"))

                    draw_key = (draw["year"], draw["term"])
                    safe_res_code: str | None = draw["numbers_str"]
                    if draw_key in safety_draw_map:
                        safe_res_code = None

                    if mode_id == 65:
                        if is_future:
                            seed_str = f"{draw['year']}{draw['term']:03d}"
                            seed_int = int(_hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
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

                        row_data = build_generated_prediction_row_data(
                            mode_id=mode_id,
                            lottery_type=str(lottery_type),
                            year=str(draw["year"]),
                            term=str(draw["term"]),
                            web_value="4",
                            res_code=safe_res_code or "",
                            generated_content=content,
                        )
                    elif mode_id == 108:
                        # 大小中特带1头：生成 content（大小|号码）和 tou（头数）
                        if is_future:
                            result = predict(
                                config=config,
                                res_code=None,
                                source_table=table_name,
                                db_path=db_path,
                                target_hit_rate=default_target_hit_rate,
                                random_seed=f"{draw['year']}{draw['term']:03d}",
                            )
                            predicted_size = str(result["prediction"]["labels"][0])
                            seed_str = f"{draw['year']}{draw['term']:03d}"
                            seed_int = int(_hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
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

                        row_data = build_generated_prediction_row_data(
                            mode_id=mode_id,
                            lottery_type=str(lottery_type),
                            year=str(draw["year"]),
                            term=str(draw["term"]),
                            web_value="4",
                            res_code=safe_res_code or "",
                            generated_content={
                                "content": [f"{predicted_size}|{chosen_number}"],
                                "tou": [head_text],
                            },
                        )
                    elif mode_id == 246:
                        # 七肖七码(一肖一码)：正常预测 + 随机平特生肖
                        result = predict(
                            config=config,
                            res_code=None if is_future else safe_res_code,
                            source_table=table_name,
                            db_path=db_path,
                            target_hit_rate=default_target_hit_rate,
                            random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
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
                        # 随机选取一个生肖作为 ping 值
                        if is_future:
                            seed_str = f"ping_{draw['year']}{draw['term']:03d}"
                            seed_int = int(_hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)
                            _random.seed(seed_int)
                        row_data["ping"] = _random.choice(list({v for v in zodiac_map.values() if v}))
                    else:
                        result = predict(
                            config=config,
                            res_code=None if is_future else safe_res_code,
                            source_table=table_name,
                            db_path=db_path,
                            target_hit_rate=default_target_hit_rate,
                            random_seed=f"{draw['year']}{draw['term']:03d}" if is_future else None,
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

                    if is_future:
                        row_data["res_sx"] = ""
                        row_data["res_color"] = ""
                    else:
                        row_data["res_sx"], row_data["res_color"] = compute_result_fields(
                            draw["numbers_str"], zodiac_map, color_map
                        )

                    row_data = enforce_prediction_diversity(
                        mode_id=mode_id,
                        row_data=row_data,
                        recent_rows=recent_rows,
                        config=config,
                    )
                    diversity_warning = row_data.pop("_diversity_warning", None)
                    if diversity_warning:
                        module_report["warnings"].append(str(diversity_warning))

                    stored = upsert_created_prediction_row(conn, table_name, row_data)
                    if stored.get("action") == "inserted":
                        module_report["inserted"] += 1
                        total_inserted += 1
                    else:
                        module_report["updated"] += 1
                        total_updated += 1

                    # 将当前行加入最近行缓存，供后续期号多样性比较
                    recent_rows.insert(0, {"content": row_data.get("content")})
                except Exception as exc:
                    conn.rollback()
                    module_report["errors"] += 1
                    total_errors += 1
                    if not module_report["error_message"]:
                        module_report["error_message"] = str(exc)
                    _logger.error(
                        "Module generation error: mode_id=%d, key=%s, draw=%s/%d, future=%s — %s",
                        mode_id, mechanism_key, draw.get("year"), draw.get("term"),
                        draw.get("_future", False), exc,
                    )

            module_reports.append(module_report)

        elapsed_s = round(time.perf_counter() - _t_start, 2)
        _logger.info(
            "Batch generation completed: modules=%d, draws=%d, inserted=%d, updated=%d, errors=%d, elapsed=%.1fs",
            len(module_reports), len(draws), total_inserted, total_updated, total_errors, elapsed_s,
        )
        if total_errors > 0:
            _logger.warning(
                "Batch generation had %d errors across %d modules",
                total_errors,
                sum(1 for m in module_reports if m.get("errors", 0) > 0),
            )

        return {
            "site_id": int(site_id),
            "site_name": str(site.get("name") or ""),
            "lottery_type": int(lottery_type),
            "start_issue": f"{start_issue[0]}{start_issue[1]}",
            "end_issue": f"{end_issue[0]}{end_issue[1]}",
            "web_id": 4,
            "future_periods": int(future_periods or 0),
            "future_only": bool(future_only),
            "total_modules": len(module_reports),
            "draw_count": len(draws),
            "inserted": total_inserted,
            "updated": total_updated,
            "errors": total_errors,
            "trigger": trigger,
            "modules": module_reports,
        }
