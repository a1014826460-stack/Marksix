"""Unified crawler service for lottery data.

Runs HK/Macau crawlers and imports Taiwan JSON data,
saving all results to the lottery_draws table.
"""

import json
import logging
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from HK_history_crawler import fetch_hongkong_history_data, transform_standard_list
from Macau_history_crawler import fetch_macau_history_data

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect as db_connect
from helpers import (
    get_effective_next_draw_payload,
    sync_lottery_type_next_time_from_latest_draw,
)
from runtime_config import get_config, get_config_from_conn

_crawler_logger = logging.getLogger("crawler.scheduler")
_draw_mismatch_logger = logging.getLogger("draw.mismatch")
HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"
TASK_TABLE_NAME = "scheduler_tasks"
TASK_TYPE_AUTO_PREDICTION = "auto_prediction"
TASK_TYPE_TAIWAN_PRECISE_OPEN = "taiwan_precise_open"
TASK_TYPE_DAILY_PREDICTION = "daily_prediction"

# lottery_type_id → system_config 前缀映射
_LT_CFG_PREFIX: dict[int, str] = {1: "lottery.hk", 2: "lottery.macau", 3: "lottery.taiwan"}

# HK/Macau 的 collector URL（优先读 lottery_types.collect_url，回退到此默认值）
_PRECISE_DRAW_COLLECT_URLS: dict[int, str] = {
    1: "https://www.lnlllt.com/api.php",
    2: "https://www.lnlllt.com/api.php",
}


def _cfg(db_path: str | Path, key: str, fallback: Any) -> Any:
    try:
        return get_config(db_path, key, fallback)
    except Exception:
        return fallback


def _cfg_from_conn(conn: Any, key: str, fallback: Any) -> Any:
    try:
        return get_config_from_conn(conn, key, fallback)
    except Exception:
        return fallback


def _task_poll_interval_seconds(db_path: str | Path) -> int:
    return max(5, int(_cfg(db_path, "crawler.task_poll_interval_seconds", 30)))


def _task_lock_timeout_seconds(db_path: str | Path) -> int:
    return max(30, int(_cfg(db_path, "crawler.task_lock_timeout_seconds", 300)))


def _task_retry_delay_seconds(db_path: str | Path) -> int:
    return max(5, int(_cfg(db_path, "crawler.task_retry_delay_seconds", 60)))


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _task_key(task_type: str, payload: dict[str, Any]) -> str:
    if task_type == TASK_TYPE_AUTO_PREDICTION:
        return f"{task_type}:{payload.get('lottery_type_id')}"
    if task_type == TASK_TYPE_TAIWAN_PRECISE_OPEN:
        return f"{task_type}:{payload.get('schedule_date')}"
    if task_type == TASK_TYPE_DAILY_PREDICTION:
        return f"{task_type}:{payload.get('schedule_date')}"
    return f"{task_type}:{_json_dumps(payload)}"


def _upsert_scheduler_task(
    db_path: str | Path,
    *,
    task_type: str,
    payload: dict[str, Any],
    run_at: str,
    max_attempts: int = 3,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    task_key = _task_key(task_type, payload)
    payload_json = _json_dumps(payload)
    with db_connect(db_path) as conn:
        existing = conn.execute(
            f"SELECT id FROM {TASK_TABLE_NAME} WHERE task_key = ? LIMIT 1",
            (task_key,),
        ).fetchone()
        if existing:
            conn.execute(
                f"""
                UPDATE {TASK_TABLE_NAME}
                SET task_type = ?, payload_json = ?, status = 'pending', run_at = ?,
                    locked_at = NULL, locked_by = NULL, last_error = NULL,
                    max_attempts = ?, updated_at = ?
                WHERE task_key = ?
                """,
                (task_type, payload_json, run_at, max_attempts, now, task_key),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO {TASK_TABLE_NAME} (
                    task_key, task_type, payload_json, status, run_at,
                    attempt_count, max_attempts, created_at, updated_at
                )
                VALUES (?, ?, ?, 'pending', ?, 0, ?, ?, ?)
                """,
                (task_key, task_type, payload_json, run_at, max_attempts, now, now),
            )


def _acquire_due_scheduler_tasks(db_path: str | Path, *, worker_id: str, limit: int = 10) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    stale_before = (now - timedelta(seconds=_task_lock_timeout_seconds(db_path))).isoformat()
    tasks: list[dict[str, Any]] = []
    with db_connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT id, task_key, task_type, payload_json, run_at, attempt_count, max_attempts
            FROM {TASK_TABLE_NAME}
            WHERE run_at <= ?
              AND (
                    status = 'pending'
                    OR (status = 'running' AND locked_at IS NOT NULL AND locked_at < ?)
                  )
            ORDER BY run_at ASC, id ASC
            LIMIT ?
            """,
            (now_text, stale_before, limit),
        ).fetchall()
        for row in rows:
            updated = conn.execute(
                f"""
                UPDATE {TASK_TABLE_NAME}
                SET status = 'running',
                    locked_at = ?,
                    locked_by = ?,
                    attempt_count = COALESCE(attempt_count, 0) + 1,
                    updated_at = ?
                WHERE id = ?
                  AND (
                        status = 'pending'
                        OR (status = 'running' AND locked_at IS NOT NULL AND locked_at < ?)
                      )
                """,
                (now_text, worker_id, now_text, row["id"], stale_before),
            )
            if updated.rowcount:
                tasks.append(dict(row))
    return tasks


def _mark_scheduler_task_done(db_path: str | Path, task_id: int) -> None:
    now_text = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        conn.execute(
            f"""
            UPDATE {TASK_TABLE_NAME}
            SET status = 'done', locked_at = NULL, locked_by = NULL,
                last_error = NULL, last_finished_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now_text, now_text, task_id),
        )


def _mark_scheduler_task_failed(db_path: str | Path, task: dict[str, Any], exc: Exception) -> None:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    attempt_count = int(task.get("attempt_count") or 0) + 1
    max_attempts = int(task.get("max_attempts") or 3)
    final_status = "failed" if attempt_count >= max_attempts else "pending"
    retry_at = (now + timedelta(seconds=_task_retry_delay_seconds(db_path))).isoformat()
    with db_connect(db_path) as conn:
        conn.execute(
            f"""
            UPDATE {TASK_TABLE_NAME}
            SET status = ?,
                locked_at = NULL,
                locked_by = NULL,
                run_at = ?,
                last_error = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                final_status,
                retry_at if final_status == "pending" else now_text,
                f"{type(exc).__name__}: {exc}",
                now_text,
                int(task["id"]),
            ),
        )


def _ensure_taiwan_precise_open_task(db_path: str | Path) -> None:
    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    hour = int(_cfg(db_path, "crawler.taiwan_precise_open_hour", 22))
    minute = int(_cfg(db_path, "crawler.taiwan_precise_open_minute", 30))
    target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if beijing_now >= target_beijing:
        target_beijing += timedelta(days=1)
    target_utc = target_beijing - timedelta(hours=8)
    _upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_TAIWAN_PRECISE_OPEN,
        payload={"schedule_date": target_beijing.strftime("%Y-%m-%d")},
        run_at=target_utc.isoformat(),
        max_attempts=max(1, int(_cfg(db_path, "crawler.taiwan_max_retries", 3))),
    )


def _ensure_daily_prediction_task(db_path: str | Path) -> None:
    """每日固定时间自动预测任务，默认北京时间 12:00。

    由 system_config 的 scheduler.auto_prediction_time 控制触发时间，
    支持运行时通过配置管理页面修改，下次调度自动生效。
    """
    time_str = str(_cfg(db_path, "scheduler.auto_prediction_time", "12:00")).strip()
    try:
        parts = time_str.split(":")
        target_hour = int(parts[0])
        target_minute = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        target_hour = 12
        target_minute = 0

    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    target_beijing = beijing_now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if beijing_now >= target_beijing:
        target_beijing += timedelta(days=1)
    target_utc = target_beijing - timedelta(hours=8)
    _upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": target_beijing.strftime("%Y-%m-%d")},
        run_at=target_utc.isoformat(),
        max_attempts=3,
    )


def _get_lottery_meta(db_path: str | Path) -> dict[str, dict[str, Any]]:
    """
    从数据库 lottery_types 表中读取所有彩种的配置信息。

    返回一个字典，key 为彩种名称（如 "香港彩"、"澳门彩"），
    value 为包含 id, collect_url, draw_time 等字段的字典。

    这样采集地址（collect_url）和开奖时间（draw_time）就完全由数据库管理，
    不再硬编码在爬虫脚本中。
    """
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
    # 只有 next_time 非空时才写入/更新，防止历史数据覆盖有效的下次开奖时间
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
    """
    执行香港彩历史数据采集任务。

    工作流程：
    1. 从数据库 lottery_types 表读取香港彩的配置（采集地址 collect_url）
    2. 调用 fetch_hongkong_history_data() 拉取原始数据
    3. 转换数据格式后存入 lottery_draws 表

    注意：采集地址不再写死在脚本中，而是由管理员在后台"彩种管理"页面配置，
    存储在 PostgreSQL 数据库的 lottery_types.collect_url 字段中。
    """
    # ── 从数据库获取香港彩的配置信息 ──
    meta_map = _get_lottery_meta(db_path)
    hk_meta = meta_map.get(HK_NAMES[0]) or meta_map.get(HK_NAMES[1])
    if hk_meta is None:
        raise ValueError("香港彩 lottery type not found - please ensure 香港彩 exists")

    # ── 使用数据库中的采集地址发起请求，
    #     如果数据库未配置采集地址则使用爬虫函数默认值（兼容旧数据） ──
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
                _crawler_logger.warning("SKIP: %s - %s", item.get('issue', '?'), e)
    return {"source": "hk", "fetched": len(records), "saved": saved}


def run_macau_crawler(db_path: str | Path) -> dict[str, Any]:
    """
    执行澳门彩历史数据采集任务。

    工作流程：
    1. 从数据库 lottery_types 表读取澳门彩的配置（采集地址 collect_url）
    2. 调用 fetch_macau_history_data() 拉取原始数据
    3. 转换数据格式后存入 lottery_draws 表

    注意：采集地址不再写死在脚本中，而是由管理员在后台"彩种管理"页面配置，
    存储在 PostgreSQL 数据库的 lottery_types.collect_url 字段中。
    """
    # ── 从数据库获取澳门彩的配置信息 ──
    meta_map = _get_lottery_meta(db_path)
    macau_meta = meta_map.get(MACAU_NAME)
    if macau_meta is None:
        raise ValueError("澳门彩 lottery type not found")

    # ── 使用数据库中的采集地址发起请求 ──
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
                _crawler_logger.warning("SKIP: %s - %s", item.get('issue', '?'), e)
    return {"source": "macau", "fetched": len(records), "saved": saved}


def crawl_and_generate_for_type(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    """爬取指定彩种的开奖数据，然后自动生成所有启用站点的预测资料。

    供 HTTP API（app.py 的 _crawl_and_generate）和定时调度器
    （CrawlerScheduler._run_once）共同使用，避免逻辑重复。

    :param db_path: 数据库连接字符串
    :param lottery_type_id: 彩种 ID（1=香港, 2=澳门, 3=台湾）
    :return: 包含 lottery_name、crawl、generation 三部分的字典
    """
    from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
    from db import connect as _connect

    # ── 1. 确定彩种名称 ──
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, name FROM lottery_types WHERE id = ?", (lottery_type_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"lottery_type_id={lottery_type_id} 不存在")
        lottery_name = str(row["name"])

    # ── 2. 执行爬虫 ──
    crawl_result: dict[str, Any] = {"status": "skipped", "message": ""}
    if lottery_name in HK_NAMES:
        crawl_result = run_hk_crawler(db_path)
    elif lottery_name == MACAU_NAME:
        crawl_result = run_macau_crawler(db_path)
    else:
        crawl_result["message"] = str(
            _cfg(db_path, "crawler.message.taiwan_import_only", "Taiwan data must be imported from JSON.")
        )

    # ── 3. 自动生成预测资料 ──
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


def _trigger_draw_mismatch_alert(
    db_path: str | Path,
    lottery_type_id: int,
    expected_period: str,
    actual_period: str,
    attempt_count: int,
) -> None:
    """开奖期号不匹配告警：写入日志和 error_logs 表，供管理后台查看。

    当精确调度检查发现实际返回的期号与预期不匹配（经过全部重试后仍失败），
    触发此告警通知管理员。
    """
    lt_name = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}.get(lottery_type_id, str(lottery_type_id))
    ts = datetime.now(timezone.utc).isoformat()
    alert_msg = (
        f"[期号不匹配告警] 彩种={lt_name} 预期期号={expected_period} "
        f"实际期号={actual_period} 重试次数={attempt_count} 时间戳={ts}"
    )
    _draw_mismatch_logger.warning(alert_msg)
    # 写入 error_logs 表，日志管理页面可查看
    try:
        with db_connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO error_logs (
                    created_at, level, logger_name, module, func_name,
                    file_path, line_number, message, lottery_type_id, task_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts, "WARNING", "draw.mismatch", "crawler.precise_draw",
                    "_trigger_draw_mismatch_alert", __file__, 0, alert_msg,
                    lottery_type_id, "precise_draw_check",
                ),
            )
    except Exception:
        pass


def _fetch_current_draw_period(lottery_type_id: int, db_path: str | Path) -> tuple[str | None, str | None]:
    """向开奖号码查询接口发送 HTTP 请求，获取当前期号。

    :return: (period, error_message)，成功时 error_message 为 None
    """
    try:
        from result_crawler import fetch_current_term_data, transform_standard_list

        # 获取该彩种的采集地址
        meta_map = _get_lottery_meta(db_path)
        lt_name = {1: "香港彩", 2: "澳门彩"}.get(lottery_type_id, "")
        lt_meta = meta_map.get(lt_name or "")
        collect_url = str(lt_meta.get("collect_url", "") or "") if lt_meta else ""
        if not collect_url:
            collect_url = _PRECISE_DRAW_COLLECT_URLS.get(lottery_type_id, "")

        crawler_type = 1 if lottery_type_id == 1 else 2
        raw, status_code = fetch_current_term_data(type=crawler_type, collect_url=collect_url)

        if status_code != 200:
            return None, f"HTTP {status_code}"

        import json as _json
        parsed = _json.loads(raw) if isinstance(raw, str) else raw
        records = transform_standard_list(parsed, crawler_type=crawler_type)
        if not records:
            return None, "no records returned"

        # 从第一条记录提取期号
        issue = str(records[0].get("issue", "")).strip()
        if not issue:
            return None, "empty issue in record"

        # issue 格式可能是 "2026001" 或 "001"，统一转为完整期号
        year_val = records[0].get("open_time", "")[:4]
        try:
            term_num = int(issue)
            if term_num < 1000 and year_val:
                period = f"{year_val}{term_num:03d}"
            else:
                period = str(term_num)
        except ValueError:
            period = issue

        return period, None
    except Exception as e:
        return None, str(e)


def _compute_next_period(current_period: str) -> str:
    """根据当前期号计算下一期期号。

    例如 current_period="2026001" → "2026002"，
    current_period="2026365" → "2027001"。
    """
    if not current_period or len(current_period) < 4:
        return ""
    try:
        year = int(current_period[:4])
        term = int(current_period[4:])
        max_terms = 365
        if term >= max_terms:
            return f"{year + 1}001"
        return f"{year}{term + 1:03d}"
    except (ValueError, IndexError):
        return ""


def _do_precise_draw_check(lottery_type_id: int, db_path: str) -> None:
    """精确开奖期号检查：发送 HTTP 请求获取最新期号，与预期下一期比对。

    如果期号不匹配，每 2 秒重试一次（最多 3 次，共 4 次请求），
    每次重试前重新读取 system_config 中的 next_time 以应对时间变动。
    全部重试失败后触发告警通知管理员。
    """
    cfg_prefix = _LT_CFG_PREFIX.get(lottery_type_id)
    if not cfg_prefix:
        return

    lt_name = {1: "香港彩", 2: "澳门彩"}.get(lottery_type_id, str(lottery_type_id))
    current_period = str(_cfg(db_path, f"{cfg_prefix}_current_period", ""))
    expected_period = _compute_next_period(current_period)

    if not expected_period:
        _crawler_logger.warning("Precise check lt=%s: cannot compute next period from current=%s", lottery_type_id, current_period)
        return

    for attempt in range(4):  # 首次 + 3 次重试
        if attempt > 0:
            time.sleep(2)
            # 每次重试前重新读取 next_time，适应时间变动
            _next = str(_cfg(db_path, f"{cfg_prefix}_next_time", ""))
            if _next:
                try:
                    _next_dt = datetime.fromtimestamp(int(_next) / 1000, tz=timezone.utc)
                    _now_dt = datetime.now(timezone.utc)
                    if _next_dt > _now_dt + timedelta(seconds=10):
                        _crawler_logger.info(
                            "Precise check lt=%s: next_time updated to %s, deferring check",
                            lottery_type_id, _next_dt.isoformat(),
                        )
                        # next_time 已被更新（可能是另一轮爬虫已更新），停止本次检查
                        return
                except (ValueError, OSError):
                    pass

        period, error = _fetch_current_draw_period(lottery_type_id, db_path)

        if period and period == expected_period:
            _crawler_logger.info(
                "Precise check lt=%s: period matched expected=%s actual=%s (attempt=%d)",
                lottery_type_id, expected_period, period, attempt + 1,
            )
            return

        _crawler_logger.warning(
            "Precise check lt=%s: MISMATCH expected=%s actual=%s error=%s (attempt=%d/%d)",
            lottery_type_id, expected_period, period or "N/A", error or "N/A",
            attempt + 1, 4,
        )

    # 全部重试失败，触发告警
    final_period, final_error = _fetch_current_draw_period(lottery_type_id, db_path)
    _trigger_draw_mismatch_alert(
        db_path, lottery_type_id, expected_period,
        final_period or f"error: {final_error}", 4,
    )
    _crawler_logger.error(
        "Precise check lt=%s: ALL ATTEMPTS FAILED expected=%s final_actual=%s",
        lottery_type_id, expected_period, final_period or f"error: {final_error}",
    )


class CrawlerScheduler:
    """后台定时任务调度器。

    职责：
    - 每 60 秒检查到达开奖时间的记录并自动标记 is_opened=1
    - 每日北京时间 22:30:00 精准执行台湾彩开奖 + next_time 更新
    - 管理 run_crawl_only 触发的延迟自动预测定时器
    - 精确调度 HK/Macau 开奖前 1 秒期号检查

    注意：历史开奖数据爬取不再由调度器自动执行，
    应由管理员通过后台"更新开奖"按钮手动触发。

    台湾彩数据由管理后台手工录入，不再通过爬虫自动导入。
    """

    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        self._running = False
        self._auto_open_timer: threading.Timer | None = None
        self._auto_crawl_timer: threading.Timer | None = None
        self._task_timer: threading.Timer | None = None
        self._precise_timers: dict[int, threading.Timer] = {}  # lottery_type_id → Timer
        self._worker_id = f"crawler:{id(self)}"

    def _auto_open_interval_seconds(self) -> int:
        return max(5, int(_cfg(self.db_path, "crawler.auto_open_interval_seconds", 60)))

    def _auto_crawl_interval_seconds(self) -> int:
        return max(30, int(_cfg(self.db_path, "crawler.auto_crawl_interval_seconds", 600)))

    def _auto_crawl_recent_minutes(self) -> int:
        return max(1, int(_cfg(self.db_path, "crawler.auto_crawl_recent_minutes", 30)))

    def _taiwan_retry_delays(self) -> list[int]:
        raw = _cfg(self.db_path, "crawler.taiwan_retry_delays_seconds", [60, 300, 900])
        if isinstance(raw, list):
            delays: list[int] = []
            for item in raw:
                try:
                    delays.append(max(1, int(item)))
                except (TypeError, ValueError):
                    continue
            if delays:
                return delays
        return [60, 300, 900]

    def _taiwan_max_retries(self) -> int:
        return max(1, int(_cfg(self.db_path, "crawler.taiwan_max_retries", 3)))

    def _reschedule_precise_checks(self) -> None:
        """为 HK(1) 和 Macau(2) 分别安排精确开奖期号检查任务。

        从 system_config 读取 lottery.{hk,macau}_next_time（毫秒时间戳），
        计算在距离该时间点前 1 秒触发检查。
        如果该时间点已过，跳过（由自动爬虫兜底）。
        """
        for lt_id in [1, 2]:
            # 取消旧的定时器
            if lt_id in self._precise_timers:
                self._precise_timers[lt_id].cancel()
                del self._precise_timers[lt_id]

            cfg_prefix = _LT_CFG_PREFIX.get(lt_id)
            if not cfg_prefix:
                continue

            next_time_ms_str = str(_cfg(self.db_path, f"{cfg_prefix}_next_time", ""))
            if not next_time_ms_str:
                continue

            try:
                next_ms = int(next_time_ms_str)
                if next_ms <= 0:
                    continue
                target_dt = datetime.fromtimestamp(next_ms / 1000, tz=timezone.utc)
                fire_at = target_dt - timedelta(seconds=1)
                now_dt = datetime.now(timezone.utc)
                delay = (fire_at - now_dt).total_seconds()

                if delay <= 0:
                    _crawler_logger.debug(
                        "Precise check lt=%s: target %s already passed, skipping",
                        lt_id, fire_at.isoformat(),
                    )
                    continue

                def _fire(_lt_id=lt_id, _db=self.db_path):
                    try:
                        _do_precise_draw_check(_lt_id, _db)
                    except Exception as exc:
                        _crawler_logger.error("Precise check lt=%s unhandled error: %s", _lt_id, exc)
                    finally:
                        # 检查完毕后，重新调度下一次检查
                        if self._running:
                            self._reschedule_precise_checks()

                timer = threading.Timer(delay, _fire)
                timer.daemon = True
                timer.start()
                self._precise_timers[lt_id] = timer

                _crawler_logger.info(
                    "Precise check lt=%s scheduled at %s (delay=%.0fs)",
                    lt_id, fire_at.isoformat(), delay,
                )
            except (ValueError, OSError) as e:
                _crawler_logger.warning("Precise check lt=%s scheduling failed: %s", lt_id, e)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            sync_result = sync_all_lottery_type_next_times(
                self.db_path,
                source="crawler.startup_sync",
            )
            _crawler_logger.info(
                "Startup next_time sync completed (checked=%s, updated=%s)",
                sync_result["checked"],
                sync_result["updated"],
            )
        except Exception as exc:
            _crawler_logger.warning("Startup next_time sync failed: %s", exc)
        _crawler_logger.info(
            "Scheduler started (auto-open every %ss, auto-crawl every %ss)",
            self._auto_open_interval_seconds(),
            self._auto_crawl_interval_seconds(),
        )
        self._schedule_auto_open()
        self._schedule_auto_crawl()
        self._schedule_task_loop()
        _ensure_taiwan_precise_open_task(self.db_path)
        # 每日固定时间自动预测任务
        _ensure_daily_prediction_task(self.db_path)
        # 精确开奖期号检查（HK/Macau 开奖前 1 秒触发）
        self._reschedule_precise_checks()

    def stop(self) -> None:
        _crawler_logger.info("Scheduler stopping")
        self._running = False
        if hasattr(self, "_auto_open_timer") and self._auto_open_timer:
            self._auto_open_timer.cancel()
            self._auto_open_timer = None
        if hasattr(self, "_auto_crawl_timer") and self._auto_crawl_timer:
            self._auto_crawl_timer.cancel()
            self._auto_crawl_timer = None
        if self._task_timer:
            self._task_timer.cancel()
            self._task_timer = None
        for lt_id, timer in list(self._precise_timers.items()):
            timer.cancel()
        self._precise_timers.clear()

    def _auto_open_draws(self) -> None:
        """检查所有未开奖记录，若开奖时间已过则自动标记 is_opened=1。
        同时为 type=3 记录补充 next_time（作为精准调度器的兜底）。

        注意：draw_time 字段存储的是北京时间字符串，比较时也必须使用北京时间。"""
        try:
            now_utc_dt = datetime.now(timezone.utc)
            now_utc = now_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
            now_beijing = (now_utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            with db_connect(self.db_path) as conn:
                # 先查出即将被打开的记录，再执行 UPDATE，避免依赖脆弱的 updated_at 精确匹配
                pending = conn.execute(
                    """SELECT id, year, term, draw_time, lottery_type_id FROM lottery_draws
                       WHERE is_opened = 0 AND draw_time IS NOT NULL AND draw_time != ''
                       AND draw_time <= ?""",
                    (now_beijing,),
                ).fetchall()

                if pending:
                    ids = [row["id"] for row in pending]
                    placeholders = ",".join("?" for _ in ids)
                    conn.execute(
                        f"UPDATE lottery_draws SET is_opened = 1, updated_at = ? "
                        f"WHERE id IN ({placeholders})",
                        [now_utc] + ids,
                    )
                    _crawler_logger.info("AutoOpen: Set is_opened=1 for %d draw(s)", len(pending))

                    # 为刚打开的 type=3 记录更新 next_time
                    taiwan_opened = [r for r in pending if r["lottery_type_id"] == 3]
                    for row in taiwan_opened:
                        self._calc_and_update_next_time(conn, row, now_utc)
                    if taiwan_opened:
                        conn.commit()
        except Exception as e:
            _crawler_logger.error("AutoOpen error: %s", e)

    def _schedule_auto_open(self) -> None:
        """每 60 秒检查一次是否有到达开奖时间的记录。"""
        if not self._running:
            return
        self._auto_open_draws()
        self._auto_open_timer = threading.Timer(self._auto_open_interval_seconds(), self._schedule_auto_open)
        self._auto_open_timer.daemon = True
        self._auto_open_timer.start()

    def _schedule_auto_crawl(self) -> None:
        """每 10 分钟自动尝试爬取香港/澳门当前期开奖数据。"""
        if not self._running:
            return
        self._auto_crawl()
        self._auto_crawl_timer = threading.Timer(self._auto_crawl_interval_seconds(), self._schedule_auto_crawl)
        self._auto_crawl_timer.daemon = True
        self._auto_crawl_timer.start()

    def _auto_crawl(self) -> None:
        """自动爬取：检查是否有到达开奖时间但未获取数据的记录，尝试爬取。

        设计思路：
        - 遍历所有启用的 HK/Macau 彩种
        - 如果该彩种最近 30 分钟内没有已开奖记录（is_opened=1），则触发爬取
        - 爬取成功后自动标记 is_opened 并安排 6h 延迟预测任务
        """
        try:
            with db_connect(self.db_path) as conn:
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=self._auto_crawl_recent_minutes())
                lt_rows = conn.execute(
                    "SELECT id, name FROM lottery_types WHERE status = 1 AND id IN (1, 2)"
                ).fetchall()
                for lt_row in lt_rows:
                    lt_id = int(lt_row["id"])
                    lt_name = str(lt_row["name"])
                    recent_rows = conn.execute(
                        """
                        SELECT updated_at FROM lottery_draws
                        WHERE lottery_type_id = ? AND is_opened = 1
                        ORDER BY updated_at DESC, id DESC
                        LIMIT 10
                        """,
                        (lt_id,),
                    ).fetchall()
                    recent = False
                    for recent_row in recent_rows:
                        updated_text = str(recent_row["updated_at"] or "").strip()
                        if not updated_text:
                            continue
                        try:
                            updated_dt = datetime.fromisoformat(updated_text.replace("Z", "+00:00"))
                        except ValueError:
                            continue
                        if updated_dt > cutoff:
                            recent = True
                            break
                    if recent:
                        continue  # 最近已有开奖，跳过
                    # 触发爬取
                    try:
                        result = run_crawl_only(self.db_path, lt_id)
                        saved = result.get("saved", 0)
                        if saved > 0:
                            _crawler_logger.info(
                                "Auto-crawl %s: saved %d draws", lt_name, saved
                            )
                    except Exception as exc:
                        _crawler_logger.warning(
                            "Auto-crawl %s failed: %s", lt_name, exc
                        )
        except Exception as e:
            _crawler_logger.error("Auto-crawl scheduler error: %s", e)
        finally:
            try:
                sync_all_lottery_type_next_times(
                    self.db_path,
                    source="crawler.periodic_sync",
                )
                # 同步完成后，刷新精确开奖检查定时器
                self._reschedule_precise_checks()
            except Exception as exc:
                _crawler_logger.warning("Periodic next_time sync failed: %s", exc)

    def _schedule_task_loop(self) -> None:
        if not self._running:
            return
        self._run_due_tasks()
        self._task_timer = threading.Timer(_task_poll_interval_seconds(self.db_path), self._schedule_task_loop)
        self._task_timer.daemon = True
        self._task_timer.start()

    def _run_due_tasks(self) -> None:
        tasks = _acquire_due_scheduler_tasks(self.db_path, worker_id=self._worker_id, limit=10)
        for task in tasks:
            try:
                self._execute_task(task)
                _mark_scheduler_task_done(self.db_path, int(task["id"]))
            except Exception as exc:
                _mark_scheduler_task_failed(self.db_path, task, exc)
                _crawler_logger.exception("Scheduler task failed: %s", task.get("task_key"))

    def _execute_task(self, task: dict[str, Any]) -> None:
        task_type = str(task.get("task_type") or "")
        payload = json.loads(str(task.get("payload_json") or "{}"))
        if task_type == TASK_TYPE_AUTO_PREDICTION:
            _run_auto_prediction(self.db_path, int(payload["lottery_type_id"]))
            return
        if task_type == TASK_TYPE_TAIWAN_PRECISE_OPEN:
            self._open_taiwan_draws_and_update_next_time()
            _ensure_taiwan_precise_open_task(self.db_path)
            _backfill_latest_opened_prediction_results(self.db_path, 3)
            return
        if task_type == TASK_TYPE_DAILY_PREDICTION:
            # 对所有活跃彩种执行预测生成，然后调度次日任务
            for lt_id in [1, 2, 3]:
                try:
                    _run_auto_prediction(self.db_path, lt_id)
                except Exception as exc:
                    _crawler_logger.error("DailyPrediction lt=%s failed: %s", lt_id, exc)
            _ensure_daily_prediction_task(self.db_path)
            return
        raise ValueError(f"Unsupported scheduler task type: {task_type}")

    def _open_taiwan_draws_and_update_next_time(self) -> None:
        """北京时间 22:30 精准开奖：将 type=3 且 draw_time 已过的未开奖记录置为 is_opened=1，
        并立即计算下一期 draw_time 更新 next_time 为 Unix 秒级时间戳。

        注意：draw_time 字段存储的是北京时间字符串，比较时必须使用北京时间。"""
        from calendar import timegm

        now_utc_dt = datetime.now(timezone.utc)
        now_utc = now_utc_dt.strftime("%Y-%m-%d %H:%M:%S")
        now_beijing = (now_utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                """UPDATE lottery_draws SET is_opened = 1, updated_at = ?
                   WHERE lottery_type_id = 3 AND is_opened = 0
                   AND draw_time IS NOT NULL AND draw_time != ''
                   AND draw_time <= ?""",
                (now_utc, now_beijing),
            )
            opened_count = cur.rowcount
            if opened_count > 0:
                _crawler_logger.info("TaiwanOpen 22:30 Beijing — opened %d Taiwan draw(s)", opened_count)
            else:
                _crawler_logger.debug("TaiwanOpen 22:30 Beijing — no Taiwan draws to open")

            rows = conn.execute(
                """SELECT id, year, term, draw_time FROM lottery_draws
                   WHERE lottery_type_id = 3 AND updated_at = ?""",
                (now_utc,),
            ).fetchall()

            for row in rows:
                self._calc_and_update_next_time(conn, row, now_utc)

            if rows:
                conn.commit()

    def _calc_and_update_next_time(self, conn, row, now_str: str) -> None:
        """根据当期 draw_time + 1 天计算下一期 draw_time，将 next_time 更新为毫秒级时间戳。"""
        from calendar import timegm

        draw_time_str = row["draw_time"]
        draw_dt = datetime.strptime(draw_time_str, "%Y-%m-%d %H:%M:%S")
        next_dt = draw_dt + timedelta(days=1)
        # draw_time 存储的是北京时间，转为 UTC 后计算毫秒时间戳
        utc_dt = next_dt - timedelta(hours=8)
        unix_ms = int(timegm(utc_dt.timetuple()) * 1000)
        next_time_str = str(unix_ms)

        conn.execute(
            "UPDATE lottery_draws SET next_time = ?, updated_at = ? WHERE id = ?",
            (next_time_str, now_str, row["id"]),
        )
        payload = get_effective_next_draw_payload(conn, 3)
        conn.execute(
            "UPDATE lottery_types SET next_time = ?, updated_at = ? WHERE id = 3",
            (payload.get("next_time") or "", now_str),
        )
        _crawler_logger.info("TaiwanOpen Term %s: next_time=%s (%s Beijing)", row['term'], unix_ms, next_dt.strftime('%Y-%m-%d %H:%M:%S'))


# ─────────────────────────────────────────────────────────
# 独立爬取（不生成预测）+ 6 小时延迟自动预测任务
# ─────────────────────────────────────────────────────────

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
ERROR_LOG_PATH = _BACKEND_ROOT / "data" / "error.log"


def _log_auto_task_error(message: str) -> None:
    """将自动预测任务错误追加写入 error.log。"""
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] AUTO_PREDICT_FAIL {message}\n")


def _log_taiwan_task_error(message: str) -> None:
    """将台湾彩每日定时开奖任务错误追加写入 error.log。"""
    ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] TAIWAN_OPEN_FAIL {message}\n")


def _backfill_latest_opened_prediction_results(
    db_path: str | Path,
    lottery_type_id: int,
) -> None:
    """开奖后只回填最近一期已开奖结果，不立即生成下一期预测。"""
    try:
        with db_connect(db_path) as conn:
            row = conn.execute(
                """
                SELECT year, term, numbers
                FROM lottery_draws
                WHERE lottery_type_id = ? AND is_opened = 1
                ORDER BY year DESC, term DESC, id DESC
                LIMIT 1
                """,
                (int(lottery_type_id),),
            ).fetchone()
            if not row:
                _crawler_logger.warning(
                    "TaiwanOpen backfill skipped: no opened draw found for lt=%s",
                    lottery_type_id,
                )
                return
            year = int(row["year"] or 0)
            term = int(row["term"] or 0)
            numbers_str = str(row["numbers"] or "")

        backfilled = _backfill_draw_to_predictions(
            db_path,
            int(lottery_type_id),
            year,
            term,
            numbers_str,
        )
        _crawler_logger.info(
            "TaiwanOpen backfilled latest opened draw only: lt=%s year=%s term=%s updated=%s",
            lottery_type_id,
            year,
            term,
            backfilled,
        )
    except Exception as exc:
        _crawler_logger.error("TaiwanOpen backfill failed: %s", exc)
        _log_taiwan_task_error(f"Backfill latest opened draw failed: {exc}")

def _update_auto_task_status(
    db_path: str | Path, lottery_type_id: int, status: str, message: str
) -> None:
    """更新 lottery_types.last_auto_task_status 字段。"""
    ts = datetime.now(timezone.utc).isoformat()
    value = f"{status}|{message}|{ts}"
    try:
        with db_connect(db_path) as conn:
            conn.execute(
                "UPDATE lottery_types SET last_auto_task_status = ?, updated_at = ? WHERE id = ?",
                (value, ts, lottery_type_id),
            )
    except Exception as e:
        _crawler_logger.warning("AutoPred failed to update status for lt=%s: %s", lottery_type_id, e)


def sync_all_lottery_type_next_times(
    db_path: str | Path,
    *,
    source: str = "crawler.sync_all",
) -> dict[str, int]:
    """Align lottery_types.next_time from latest opened draws for all active types."""
    updated = 0
    checked = 0
    now = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        rows = conn.execute("SELECT id, next_time FROM lottery_types WHERE id IN (1, 2, 3)").fetchall()
        for row in rows:
            checked += 1
            current_value = str(row["next_time"] or "")
            next_value = sync_lottery_type_next_time_from_latest_draw(
                conn,
                int(row["id"]),
                updated_at=now,
                source=source,
            )
            if next_value != current_value:
                updated += 1
        conn.commit()
    return {"checked": checked, "updated": updated}


def _backfill_draw_to_predictions(
    db_path: str | Path, lottery_type_id: int, year: int, term: int, numbers_str: str
) -> int:
    """将开奖结果的生肖和波色回填到 created schema 的预测记录中。

    遍历所有 mode_payload 表，找到同 year+term+type 的 created 记录，
    用 fixed_data 映射计算 res_sx / res_color 并 UPDATE。

    :return: 回填影响的记录总数
    """
    from helpers import load_fixed_data_maps
    from admin.prediction import _compute_res_fields
    from utils.created_prediction_store import (
        CREATED_SCHEMA_NAME, quote_qualified_identifier, schema_table_exists,
    )

    total_updated = 0
    try:
        with db_connect(db_path) as conn:
            zodiac_map, color_map = load_fixed_data_maps(conn)
            res_sx, res_color = _compute_res_fields(numbers_str, zodiac_map, color_map)

            # 获取所有 mode_payload 表名
            tables = conn.list_tables("mode_payload_")
            for table_name in tables:
                if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
                    continue
                qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
                try:
                    cur = conn.execute(
                        f"UPDATE {qualified} SET res_sx = ?, res_color = ? "
                        "WHERE type = ? AND year = ? AND term = ? AND (res_sx IS NULL OR res_sx = '')",
                        (res_sx, res_color, str(lottery_type_id), str(year), str(term)),
                    )
                    total_updated += cur.rowcount
                except Exception:
                    continue  # 表可能缺少列，跳过
            conn.commit()
    except Exception as e:
        _crawler_logger.error("AutoPred backfill error: %s", e)
    return total_updated


def _run_auto_prediction(db_path: str | Path, lottery_type_id: int) -> None:
    """6 小时延迟后自动执行：回填开奖 + 生成下一期预测。"""
    _crawler_logger.info("AutoPred starting for lt=%s...", lottery_type_id)
    try:
        # 1. 读取最新开奖结果
        with db_connect(db_path) as conn:
            row = conn.execute(
                """SELECT year, term, numbers FROM lottery_draws
                   WHERE lottery_type_id = ? AND is_opened = 1
                   ORDER BY year DESC, term DESC LIMIT 1""",
                (lottery_type_id,),
            ).fetchone()
            if not row:
                raise ValueError("no opened draw found")
            year = int(row["year"])
            term = int(row["term"])
            numbers_str = str(row["numbers"] or "")

        # 2. 回填开奖结果到预测记录
        backfilled = _backfill_draw_to_predictions(db_path, lottery_type_id, year, term, numbers_str)
        _crawler_logger.info("AutoPred backfilled %d prediction records for lt=%s year=%s term=%s", backfilled, lottery_type_id, year, term)

        # 3. 生成未来下一期预测（遍历所有启用站点）
        from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
        issue_str = f"{year}{term:03d}"
        total_inserted = 0
        total_pred_errors = 0
        with db_connect(db_path) as conn:
            sites = conn.execute(
                "SELECT id FROM managed_sites WHERE enabled = 1"
            ).fetchall()
            for site in sites:
                site_id = int(site["id"])
                try:
                    gen = _bulk_gen(
                        db_path, site_id,
                        {
                            "lottery_type": lottery_type_id,
                            "start_issue": issue_str,
                            "end_issue": issue_str,
                            "future_periods": 1,
                            "future_only": True,
                        },
                    )
                    total_inserted += gen.get("inserted", 0)
                    total_pred_errors += gen.get("errors", 0)
                except Exception as e:
                    total_pred_errors += 1
                    _crawler_logger.error("AutoPred site=%s error: %s", site_id, e)

        _update_auto_task_status(db_path, lottery_type_id, "ok",
                                 f"backfilled={backfilled} inserted={total_inserted} errors={total_pred_errors}")
        _crawler_logger.info("AutoPred done lt=%s: backfilled=%d inserted=%d errors=%d", lottery_type_id, backfilled, total_inserted, total_pred_errors)

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        _log_auto_task_error(f"lt_id={lottery_type_id} {err_msg}")
        _update_auto_task_status(db_path, lottery_type_id, "error", err_msg)
        _crawler_logger.error("AutoPred FAILED lt=%s: %s", lottery_type_id, err_msg)
def _schedule_auto_prediction(
    db_path: str | Path, lottery_type_id: int, draw_time_str: str
) -> float:
    """安排一次 6 小时后的自动预测任务。

    :param draw_time_str: 开奖时间字符串，格式 \"2026-05-10 21:32:59\"
    :return: 延迟秒数
    """
    from datetime import timedelta

    # 解析开奖时间
    try:
        draw_dt = datetime.strptime(draw_time_str.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        # 回退：30 分钟后
        draw_dt = datetime.now(timezone.utc) + timedelta(minutes=30)

    delay_hours = float(_cfg(db_path, "crawler.auto_prediction_delay_hours", 6))
    target_dt = draw_dt + timedelta(hours=delay_hours)
    now_dt = datetime.now(timezone.utc)
    delay = max(60.0, (target_dt - now_dt).total_seconds())

    target_iso = target_dt.isoformat()
    _upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_AUTO_PREDICTION,
        payload={"lottery_type_id": int(lottery_type_id)},
        run_at=target_iso,
        max_attempts=max(1, int(_cfg(db_path, "crawler.taiwan_max_retries", 3))),
    )
    _crawler_logger.info("AutoPred scheduled for lt=%s at %s (delay=%.0fs)", lottery_type_id, target_iso, delay)
    return delay


def run_crawl_only(db_path: str | Path, lottery_type_id: int) -> dict[str, Any]:
    """仅执行爬取并存储到 lottery_draws，不生成预测资料。

    使用 result_crawler.fetch_current_term_data 获取当前期开奖数据，
    写入 lottery_draws 后安排 6 小时后的自动预测任务。

    :param db_path: 数据库连接字符串
    :param lottery_type_id: 彩种 ID（1=香港, 2=澳门, 3=台湾）
    :return: 包含 draw 信息和 auto_task 调度信息的字典
    """
    meta_map = _get_lottery_meta(db_path)
    lt_name_map = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}
    lt_name = lt_name_map.get(lottery_type_id, str(lottery_type_id))
    lt_meta = meta_map.get(lt_name)
    if lt_meta is None:
        raise ValueError(f"彩种 {lt_name} 不存在")

    # 台湾彩无在线爬虫
    if lottery_type_id == 3:
        return {
            "ok": True,
            "draw": None,
            "message": str(
                _cfg(db_path, "crawler.message.taiwan_import_only", "Taiwan data must be imported from JSON.")
            ),
        }

    # 调用 result_crawler 获取当前期数据（传入数据库配置的采集地址）
    from result_crawler import fetch_current_term_data, transform_standard_list

    crawler_type = 1 if lottery_type_id == 1 else 2
    raw, status_code = fetch_current_term_data(
        type=crawler_type,
        collect_url=lt_meta.get("collect_url", ""),
    )

    if status_code != 200:
        raise RuntimeError(f"爬虫返回 HTTP {status_code}")

    # result_crawler 返回单个 JSON 对象（非数组），包装为列表
    import json as _json
    parsed = _json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(parsed, dict):
        parsed = [parsed]
    records = transform_standard_list(parsed, crawler_type=crawler_type)
    if not records:
        raise ValueError("爬虫未返回任何开奖记录")

    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    draw_info: dict[str, Any] = {}
    with db_connect(db_path) as conn:
        for item in records:
            try:
                open_time = item["open_time"]
                year = int(open_time[:4])
                issue = item["issue"]
                try:
                    term_num = int(issue)
                except ValueError:
                    # issue 可能是 "2026128" 格式
                    term_num = int(str(issue)[4:]) if len(str(issue)) > 4 else int(issue)
                _upsert_draw(conn, lt_meta["id"], year, term_num,
                             item["result"], open_time, 1, now,
                             next_time=str(item.get("next_time") or ""))
                saved += 1
                if saved == 1:
                    draw_info = {"year": year, "term": term_num, "issue": issue, "open_time": open_time}
            except (ValueError, KeyError) as e:
                _crawler_logger.warning("CrawlOnly SKIP: %s - %s", item.get('issue', '?'), e)

    # 爬取成功后安排 6 小时后自动预测
    auto_delay = 0.0
    if saved > 0 and draw_info.get("open_time"):
        auto_delay = _schedule_auto_prediction(db_path, lottery_type_id, draw_info["open_time"])

    return {
        "ok": True,
        "draw": draw_info,
        "saved": saved,
        "fetched": len(records),
        "auto_task_scheduled_seconds": round(auto_delay, 0) if auto_delay > 0 else None,
    }
