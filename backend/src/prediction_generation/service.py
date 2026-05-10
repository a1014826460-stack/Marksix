from __future__ import annotations

from pathlib import Path
from typing import Any

from common import DEFAULT_TARGET_HIT_RATE, predict
from db import connect
from helpers import load_fixed_data_maps
from mechanisms import get_prediction_config
from prediction_generation.diversity import enforce_prediction_diversity
from utils.created_prediction_store import upsert_created_prediction_row


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


def compute_next_issue(year: int, term: int, offset: int) -> tuple[int, int]:
    max_terms_per_year = 365
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


def generate_prediction_batch(
    db_path: str | Path,
    *,
    site_id: int,
    lottery_type: int,
    start_issue: tuple[int, int],
    end_issue: tuple[int, int],
    mechanism_keys: list[str] | None,
    future_periods: int,
    trigger: str,
    sync_site_modules: Any,
    resolve_prediction_table_for_mode: Any,
    build_generated_prediction_row_data: Any,
) -> dict[str, Any]:
    """Shared batch generation service.

    This is the canonical orchestration point for admin, automation, and CLI wrappers.
    """
    from admin.crud import get_site as _get_site

    site = _get_site(db_path, site_id)
    requested_keys = list(mechanism_keys or [])

    with connect(db_path) as conn:
        sync_site_modules(conn, site_id)
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

        future_draws: list[dict[str, Any]] = []
        if int(future_periods or 0) > 0:
            latest = draws[-1]
            for offset in range(1, int(future_periods) + 1):
                next_year, next_term = compute_next_issue(latest["year"], latest["term"], offset)
                future_draws.append(
                    {
                        "year": next_year,
                        "term": next_term,
                        "numbers_str": "",
                        "_future": True,
                    }
                )

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
                created_table = f"created.{table_name}"
                existing = conn.execute(
                    f"SELECT content FROM {created_table} "
                    f"WHERE type = ? AND web = ? AND modes_id = ? "
                    f"ORDER BY year DESC, term DESC LIMIT 10",
                    (str(lottery_type), "4", mode_id),
                ).fetchall()
                recent_rows = [{"content": row["content"]} for row in existing]
            except Exception:
                recent_rows = []

            all_target_draws = list(draws) + list(future_draws)
            for draw in all_target_draws:
                try:
                    is_future = bool(draw.get("_future"))
                    if mode_id == 65 and is_future:
                        continue

                    draw_key = (draw["year"], draw["term"])
                    safe_res_code: str | None = draw["numbers_str"]
                    if draw_key in safety_draw_map:
                        safe_res_code = None

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
                    else:
                        result = predict(
                            config=config,
                            res_code=None if is_future else safe_res_code,
                            source_table=table_name,
                            db_path=db_path,
                            target_hit_rate=DEFAULT_TARGET_HIT_RATE,
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

            module_reports.append(module_report)

        return {
            "site_id": int(site_id),
            "site_name": str(site.get("name") or ""),
            "lottery_type": int(lottery_type),
            "start_issue": f"{start_issue[0]}{start_issue[1]}",
            "end_issue": f"{end_issue[0]}{end_issue[1]}",
            "web_id": 4,
            "future_periods": int(future_periods or 0),
            "total_modules": len(module_reports),
            "draw_count": len(draws),
            "inserted": total_inserted,
            "updated": total_updated,
            "errors": total_errors,
            "trigger": trigger,
            "modules": module_reports,
        }

