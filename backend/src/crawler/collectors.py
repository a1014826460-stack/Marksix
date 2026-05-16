"""数据采集模块 —— HK/Macau 爬虫执行和数据采集编排。

从 crawler_service.py 中提取，供 routes、scheduler 等层复用。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crawler.HK_history_crawler import fetch_hongkong_history_data, transform_standard_list
from crawler.Macau_history_crawler import fetch_macau_history_data
from db import connect as db_connect
from helpers import sync_lottery_type_next_time_from_latest_draw
from runtime_config import get_config

_collector_logger = logging.getLogger("crawler.collector")
HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _get_taiwan_draw_time_parts(db_path: str | Path) -> tuple[int, int]:
    """返回台湾彩北京时间开奖 (小时, 分钟)。

    主路径：解析 ``draw.taiwan_default_draw_time``（格式 "HH:MM"）。
    向后兼容：若旧 key ``crawler.taiwan_precise_open_hour`` / ``_minute``
    已被显式覆盖（不等于出厂默认 22/30），优先使用旧值。
    """
    # ── 主路径：统一 key ──
    time_str = str(_cfg(db_path, "draw.taiwan_default_draw_time", "")).strip()
    if time_str:
        try:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            hour, minute = 22, 30
    else:
        hour, minute = 22, 30

    # ── 向后兼容：旧 split key ──
    try:
        legacy_h = int(_cfg(db_path, "crawler.taiwan_precise_open_hour", 22))
        legacy_m = int(_cfg(db_path, "crawler.taiwan_precise_open_minute", 30))
        if legacy_h != 22 or legacy_m != 30:
            return (legacy_h, legacy_m)
    except (ValueError, TypeError):
        pass

    return (hour, minute)


def _get_lottery_meta(db_path: str | Path) -> dict[str, dict[str, Any]]:
    """从数据库 lottery_types 表中读取所有彩种的配置信息。"""
    with db_connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, name, collect_url, draw_time FROM lottery_types"
        ).fetchall()
        return {
            row["name"]: {
                "id": row["id"],
                "collect_url": row["collect_url"] or "",
                "draw_time": row["draw_time"] or "",
            }
            for row in rows
        }


def _upsert_draw(
    conn: Any,
    lottery_type_id: int,
    year: int,
    term: int,
    numbers: str,
    draw_time: str,
    is_opened: int,
    now: str,
    next_time: str = "",
) -> None:
    if next_time:
        conn.execute(
            """
            INSERT INTO lottery_draws
                (lottery_type_id, year, term, numbers, draw_time,
                 status, is_opened, next_term, next_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
            ON CONFLICT(lottery_type_id, year, term) DO UPDATE SET
                numbers = excluded.numbers,
                draw_time = excluded.draw_time,
                is_opened = excluded.is_opened,
                next_time = excluded.next_time,
                updated_at = excluded.updated_at
            """,
            (lottery_type_id, year, term, numbers, draw_time,
             is_opened, term + 1, next_time, now, now),
        )
    else:
        conn.execute(
            """
            INSERT INTO lottery_draws
                (lottery_type_id, year, term, numbers, draw_time,
                 status, is_opened, next_term, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(lottery_type_id, year, term) DO UPDATE SET
                numbers = excluded.numbers,
                draw_time = excluded.draw_time,
                is_opened = excluded.is_opened,
                updated_at = excluded.updated_at
            """,
            (lottery_type_id, year, term, numbers, draw_time,
             is_opened, term + 1, now, now),
        )
    sync_lottery_type_next_time_from_latest_draw(
        conn,
        lottery_type_id,
        updated_at=now,
        source="crawler.upsert_draw",
    )


def run_hk_crawler(db_path: str | Path) -> dict[str, Any]:
    """执行香港彩历史数据采集任务。"""
    meta_map = _get_lottery_meta(db_path)
    hk_meta = meta_map.get(HK_NAMES[0]) or meta_map.get(HK_NAMES[1])
    if hk_meta is None:
        raise ValueError("香港彩 lottery type not found - please ensure 香港彩 exists")

    collect_url = hk_meta["collect_url"]
    if collect_url:
        raw, status_code = fetch_hongkong_history_data(collect_url=collect_url)
    else:
        raw, status_code = fetch_hongkong_history_data()

    if status_code != 200:
        raise RuntimeError(f"HK crawler returned status {status_code}")

    records = transform_standard_list(raw)
    if not records:
        return {
            "source": "hk",
            "fetched": 0,
            "saved": 0,
            "message": str(_cfg(db_path, "crawler.message.hk_empty_data", "API returned no Hong Kong draw data.")),
        }
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                term_num = int(item["issue"])
                _upsert_draw(conn, hk_meta["id"], year, term_num,
                             item["result"], open_time, 1, now,
                             next_time=str(item.get("next_time") or ""))
                saved += 1
            except (ValueError, KeyError) as e:
                _collector_logger.warning("SKIP: %s - %s", item.get('issue', '?'), e)
    return {"source": "hk", "fetched": len(records), "saved": saved}


def run_macau_crawler(db_path: str | Path) -> dict[str, Any]:
    """执行澳门彩历史数据采集任务。"""
    meta_map = _get_lottery_meta(db_path)
    macau_meta = meta_map.get(MACAU_NAME)
    if macau_meta is None:
        raise ValueError("澳门彩 lottery type not found")

    collect_url = macau_meta["collect_url"]
    if collect_url:
        raw, status_code = fetch_macau_history_data(collect_url=collect_url)
    else:
        raw, status_code = fetch_macau_history_data()

    if status_code != 200:
        raise RuntimeError(f"Macau crawler returned status {status_code}")

    records = transform_standard_list(raw)
    if not records:
        return {
            "source": "macau",
            "fetched": 0,
            "saved": 0,
            "message": str(_cfg(db_path, "crawler.message.macau_empty_data", "API returned no Macau draw data.")),
        }
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    with db_connect(db_path) as conn:
        for item in records:
            try:
                expect = item["issue"]
                year = int(expect[:4])
                term_num = int(expect[4:])
                _upsert_draw(conn, macau_meta["id"], year, term_num,
                             item["result"], item["open_time"], 1, now,
                             next_time=str(item.get("next_time") or ""))
                saved += 1
            except (ValueError, KeyError) as e:
                _collector_logger.warning("SKIP: %s - %s", item.get('issue', '?'), e)
    return {"source": "macau", "fetched": len(records), "saved": saved}


def crawl_and_generate_for_type(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    """爬取指定彩种的开奖数据，然后自动生成所有启用站点的预测资料。

    供 HTTP API 和定时调度器共同使用，避免逻辑重复。
    """
    from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
    from db import connect as _connect

    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM lottery_types WHERE id = ?", (lottery_type_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"lottery_type_id={lottery_type_id} 不存在")
        lottery_name = str(row["name"])

    crawl_result: dict[str, Any] = {"status": "skipped", "message": ""}
    if lottery_name in HK_NAMES:
        crawl_result = run_hk_crawler(db_path)
    elif lottery_name == MACAU_NAME:
        crawl_result = run_macau_crawler(db_path)
    else:
        crawl_result["message"] = str(
            _cfg(db_path, "crawler.message.taiwan_import_only", "Taiwan data must be imported from JSON.")
        )

    generation_results: list[dict[str, Any]] = []
    with _connect(db_path) as conn:
        sites = conn.execute(
            "SELECT id, name, lottery_type_id FROM managed_sites WHERE enabled = 1"
        ).fetchall()

        for site in sites:
            site_id = int(site["id"])
            modules = conn.execute(
                """
                SELECT id, mechanism_key, mode_id
                FROM site_prediction_modules
                WHERE site_id = ? AND status = 1
                ORDER BY sort_order, id
                """,
                (site_id,),
            ).fetchall()

            if not modules:
                continue

            latest_draw = conn.execute(
                """
                SELECT year, term FROM lottery_draws
                WHERE lottery_type_id = ? AND is_opened = 1
                ORDER BY year DESC, term DESC LIMIT 1
                """,
                (lottery_type_id,),
            ).fetchone()

            if not latest_draw:
                continue

            latest_term = int(latest_draw["term"])
            latest_year = int(latest_draw["year"])

            try:
                gen_result = _bulk_gen(
                    db_path,
                    site_id,
                    {
                        "lottery_type": lottery_type_id,
                        "start_issue": f"{latest_year}{max(1, latest_term):03d}",
                        "end_issue": f"{latest_year}{latest_term:03d}",
                        "mechanism_keys": [str(m["mechanism_key"]) for m in modules],
                    },
                )
                generation_results.append({
                    "site_id": site_id,
                    "site_name": str(site["name"]),
                    "inserted": gen_result.get("inserted", 0),
                    "updated": gen_result.get("updated", 0),
                    "errors": gen_result.get("errors", 0),
                })
            except Exception as exc:
                generation_results.append({
                    "site_id": site_id,
                    "site_name": str(site["name"]),
                    "error": str(exc),
                })

    return {
        "lottery_name": lottery_name,
        "crawl": crawl_result,
        "generation": generation_results,
    }
