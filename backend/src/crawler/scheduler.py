"""Unified crawler service for lottery data.

Runs HK/Macau crawlers and imports Taiwan JSON data,
saving all results to the lottery_draws table.
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crawler.HK_history_crawler import transform_standard_list
from crawler.collectors import (
    _cfg,
    _get_lottery_meta,
    _upsert_draw,
    crawl_and_generate_for_type,
    run_hk_crawler,
    run_macau_crawler,
)
from crawler.tasks import (  # noqa: F401 - 兼容导出
    TASK_TABLE_NAME,
    TASK_TYPE_AUTO_PREDICTION,
    TASK_TYPE_DAILY_PREDICTION,
    TASK_TYPE_POSTGRES_BACKUP,
    TASK_TYPE_TAIWAN_PRECISE_OPEN,
    _task_lock_timeout_seconds,
    _task_poll_interval_seconds,
    _task_retry_delay_seconds,
    acquire_due_scheduler_tasks,
    ensure_daily_prediction_task,
    ensure_postgres_backup_tasks,
    ensure_taiwan_precise_open_task,
    mark_scheduler_task_done,
    mark_scheduler_task_failed,
    upsert_scheduler_task,
)
from db import connect as db_connect
from helpers import (
    get_effective_next_draw_payload,
    sync_lottery_type_next_time_from_latest_draw,
)
from runtime_config import get_config, get_config_from_conn

from alerts.alert_service import (
    alert_crawler_failure,
    alert_draw_staleness,
    alert_prediction_gap,
    alert_precise_draw_mismatch,
    reset_crawler_fail_count,
)

_crawler_logger = logging.getLogger("crawler.scheduler")
_draw_mismatch_logger = logging.getLogger("draw.mismatch")
HK_NAMES = ("香港彩", "六肖彩")
MACAU_NAME = "澳门彩"
TAIWAN_NAME = "台湾彩"

# lottery_type_id → system_config 前缀映射
_LT_CFG_PREFIX: dict[int, str] = {1: "lottery.hk", 2: "lottery.macau", 3: "lottery.taiwan"}
_LT_NAME_MAP: dict[int, str] = {1: "香港彩", 2: "澳门彩", 3: "台湾彩"}


def _run_daily_prediction_subprocess(db_path: str | Path, lottery_type_id: int) -> None:
    """Run the heavy daily prediction work in a separate Python process."""
    script_path = Path(__file__).resolve().parent / "daily_prediction_worker.py"
    src_root = script_path.parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(src_root)
        if not existing_pythonpath
        else os.pathsep.join([str(src_root), existing_pythonpath])
    )
    command = [
        sys.executable,
        str(script_path),
        "--db-path",
        str(db_path),
        "--lottery-type-id",
        str(lottery_type_id),
    ]
    _crawler_logger.info("Daily prediction subprocess starting: %s", command)
    completed = subprocess.run(
        command,
        cwd=str(src_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        detail = stderr or stdout or f"exit code {completed.returncode}"
        raise RuntimeError(f"daily prediction subprocess failed: {detail}")
    if completed.stdout.strip():
        _crawler_logger.info("Daily prediction subprocess output: %s", completed.stdout.strip())


def _compute_taiwan_default_next_time_ms(db_path: str | Path) -> str:
    """当 system_config 中未配置 lottery.taiwan_next_time 时，回退到默认今天 22:30 北京时间。

    Returns:
        毫秒级 Unix 时间戳字符串
    """
    from calendar import timegm
    hour = int(_cfg(db_path, "crawler.taiwan_precise_open_hour", 22))
    minute = int(_cfg(db_path, "crawler.taiwan_precise_open_minute", 30))
    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if beijing_now >= target_beijing:
        target_beijing += timedelta(days=1)
    target_utc = target_beijing - timedelta(hours=8)
    return str(int(timegm(target_utc.timetuple()) * 1000))


def _compute_hk_macau_default_next_time_ms(db_path: str | Path, lottery_type_id: int) -> str:
    """当 system_config 中未配置 lottery.hk_next_time / lottery.macau_next_time 时，
    回退到 draw.hk_default_draw_time / draw.macau_default_draw_time 计算下一期开奖时间。

    Returns:
        毫秒级 Unix 时间戳字符串，无法计算时返回空字符串。
    """
    from calendar import timegm

    cfg_key = "draw.hk_default_draw_time" if lottery_type_id == 1 else "draw.macau_default_draw_time"
    time_str = str(_cfg(db_path, cfg_key, "21:30")).strip()
    try:
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        hour = 21
        minute = 30

    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if beijing_now >= target_beijing:
        target_beijing += timedelta(days=1)
    target_utc = target_beijing - timedelta(hours=8)
    return str(int(timegm(target_utc.timetuple()) * 1000))


def _get_lottery_next_time_from_config(db_path: str | Path, lottery_type_id: int) -> str:
    """从 system_config 表统一读取指定彩种的下一期开奖时间。

    台湾彩读 lottery.taiwan_next_time，香港彩读 lottery.hk_next_time，
    澳门彩读 lottery.macau_next_time。

    Returns:
        毫秒级 Unix 时间戳字符串，未配置时返回空字符串。
    """
    cfg_prefix = _LT_CFG_PREFIX.get(lottery_type_id)
    if not cfg_prefix:
        return ""
    return str(_cfg(db_path, f"{cfg_prefix}_next_time", ""))

# 向后兼容别名（crawler_service.py 内部和 CrawlerScheduler 使用旧名称）
_upsert_scheduler_task = upsert_scheduler_task
_acquire_due_scheduler_tasks = acquire_due_scheduler_tasks
_mark_scheduler_task_done = mark_scheduler_task_done
_mark_scheduler_task_failed = mark_scheduler_task_failed
_ensure_taiwan_precise_open_task = ensure_taiwan_precise_open_task
_ensure_daily_prediction_task = ensure_daily_prediction_task
_ensure_postgres_backup_tasks = ensure_postgres_backup_tasks

# HK/Macau 的 collector URL（优先读 lottery_types.collect_url，回退到此默认值）
_PRECISE_DRAW_COLLECT_URLS: dict[int, str] = {
    1: "https://www.lnlllt.com/api.php",
    2: "https://www.lnlllt.com/api.php",
}


def _get_effective_collect_url(db_path: str | Path, lottery_type_id: int) -> tuple[str, str]:
    """返回 (主 URL, 备用 URL)，根据失败次数可能将备用提升为主。

    当连续失败次数达到 crawler.backup_fail_count_threshold 且备用 URL 已配置时，
    将备用 URL 返回为主 URL，原主 URL 不再使用。
    """
    from alerts.alert_service import _crawler_fail_count_key

    meta_map = _get_lottery_meta(db_path)
    lt_name = {1: "香港彩", 2: "澳门彩"}.get(lottery_type_id, "")
    lt_meta = meta_map.get(lt_name or "")
    primary = str(lt_meta.get("collect_url", "") or "") if lt_meta else ""
    if not primary:
        primary = _PRECISE_DRAW_COLLECT_URLS.get(lottery_type_id, "")

    backup_cfg_key = "draw.hk_backup_collect_url" if lottery_type_id == 1 else "draw.macau_backup_collect_url"
    backup = str(_cfg(db_path, backup_cfg_key, "")).strip()

    fail_count = int(_cfg(db_path, _crawler_fail_count_key(lottery_type_id), 0))
    threshold = int(_cfg(db_path, "crawler.backup_fail_count_threshold", 2))

    if fail_count >= threshold and backup:
        _crawler_logger.warning(
            "Switching to backup URL for lt=%s (fail_count=%d >= threshold=%d)",
            lottery_type_id, fail_count, threshold,
        )
        return backup, ""

    return primary, backup


def _cfg_from_conn(conn: Any, key: str, fallback: Any) -> Any:
    try:
        return get_config_from_conn(conn, key, fallback)
    except Exception:
        return fallback


# 任务管理函数已迁移至 crawler.tasks 模块，通过顶部的 import 和别名可用


# run_hk_crawler, run_macau_crawler, crawl_and_generate_for_type
# 已迁移至 crawler.collectors 模块，在本文件顶部导入


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
        from crawler.result_crawler import fetch_current_term_data, transform_standard_list

        collect_url, backup_url = _get_effective_collect_url(db_path, lottery_type_id)
        crawler_type = 1 if lottery_type_id == 1 else 2
        raw, status_code = fetch_current_term_data(
            type=crawler_type, collect_url=collect_url, backup_url=backup_url,
        )

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
    final_actual = final_period or f"error: {final_error}"
    _trigger_draw_mismatch_alert(
        db_path, lottery_type_id, expected_period,
        final_actual, 4,
    )
    # 同时发送邮件报警
    try:
        alert_precise_draw_mismatch(
            db_path, lottery_type_id, expected_period,
            final_actual, 4,
        )
    except Exception:
        pass
    _crawler_logger.error(
        "Precise check lt=%s: ALL ATTEMPTS FAILED expected=%s final_actual=%s",
        lottery_type_id, expected_period, final_actual,
    )


def _fetch_current_draw_records(db_path: str | Path, lottery_type_id: int) -> list[dict[str, Any]]:
    """调用当前开奖 API，返回标准化后的开奖记录列表。"""
    from crawler.result_crawler import fetch_current_term_data, transform_standard_list

    collect_url, backup_url = _get_effective_collect_url(db_path, lottery_type_id)
    crawler_type = 1 if lottery_type_id == 1 else 2
    raw, status_code = fetch_current_term_data(
        type=crawler_type, collect_url=collect_url, backup_url=backup_url,
    )

    if status_code != 200:
        raise RuntimeError(f"HTTP {status_code}")

    import json as _json
    parsed = _json.loads(raw) if isinstance(raw, str) else raw
    if isinstance(parsed, dict):
        parsed = [parsed]
    return transform_standard_list(parsed, crawler_type=crawler_type)


def _get_existing_draw(conn: Any, lottery_type_id: int, year: int, term: int) -> dict[str, Any] | None:
    """查询本地是否已有指定彩种、年份、期号的开奖记录。"""
    row = conn.execute(
        "SELECT * FROM lottery_draws WHERE lottery_type_id = ? AND year = ? AND term = ?",
        (lottery_type_id, year, term),
    ).fetchone()
    return dict(row) if row else None


def _draw_needs_upsert(existing: dict[str, Any] | None, record: dict[str, Any]) -> bool:
    """判断该 record 是否需要插入或更新。"""
    if existing is None:
        return True
    if str(existing.get("numbers") or "") != str(record.get("result") or ""):
        return True
    if str(existing.get("draw_time") or "") != str(record.get("open_time") or ""):
        return True
    if str(existing.get("next_time") or "") != str(record.get("next_time") or ""):
        return True
    return False


def _upsert_current_draw_records(
    db_path: str | Path, lottery_type_id: int, records: list[dict[str, Any]]
) -> dict[str, Any]:
    """对当前开奖 API 返回的数据做业务级 upsert。

    Returns:
        {"inserted": int, "updated": int, "skipped": int, "latest_draw": dict | None}
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0
    skipped = 0
    latest_draw: dict[str, Any] | None = None

    with db_connect(db_path) as conn:
        for record in records:
            open_time = str(record.get("open_time") or "")
            if not open_time or len(open_time) < 4:
                _crawler_logger.warning("Auto-crawl upsert skip: invalid open_time=%s", open_time)
                continue

            year = int(open_time[:4])
            issue = str(record.get("issue") or "")
            try:
                term = int(issue)
            except ValueError:
                _crawler_logger.warning("Auto-crawl upsert skip: cannot parse term from issue=%s", issue)
                continue

            existing = _get_existing_draw(conn, lottery_type_id, year, term)

            if not _draw_needs_upsert(existing, record):
                skipped += 1
                if latest_draw is None or (year, term) > (latest_draw["year"], latest_draw["term"]):
                    latest_draw = {"year": year, "term": term, "issue": issue, "open_time": open_time}
                continue

            _upsert_draw(
                conn, lottery_type_id, year, term,
                str(record.get("result") or ""), open_time, 1, now,
                next_time=str(record.get("next_time") or ""),
            )

            if existing is None:
                inserted += 1
            else:
                updated += 1

            if latest_draw is None or (year, term) > (latest_draw["year"], latest_draw["term"]):
                latest_draw = {"year": year, "term": term, "issue": issue, "open_time": open_time}

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "latest_draw": latest_draw,
    }


def _log_draw_audit(
    db_path: str | Path,
    lottery_type_id: int,
    period: str,
    *,
    event: str,
    status: str = "success",
    detail: str = "",
    duration_ms: int = 0,
    operator: str = "scheduler",
) -> None:
    """写入开奖审计日志到 draw_audit_log 表。

    Args:
        db_path: 数据库路径
        lottery_type_id: 彩种 ID
        period: 期号（如 "2026133"）
        event: 事件类型（precise_fetch / precise_upsert / precise_open / precise_complete / auto_crawl_fetch 等）
        status: success / failed / timeout
        detail: 可读详情
        duration_ms: 事件耗时毫秒数
        operator: scheduler 或管理员用户名
    """
    ts = datetime.now(timezone.utc).isoformat()
    try:
        year = int(period[:4]) if len(period) >= 7 else 0
        term = int(period[4:]) if len(period) >= 7 else 0
    except (ValueError, IndexError):
        year = 0
        term = 0

    try:
        with db_connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO draw_audit_log (
                    lottery_type_id, year, term, event, event_time,
                    duration_ms, status, detail, operator, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lottery_type_id, year, term, event, ts,
                    duration_ms, status, detail, operator, ts,
                ),
            )
    except Exception:
        _crawler_logger.debug("Failed to write draw audit log: period=%s event=%s", period, event)


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

    # ── 改进方法：精确开奖完整管线（期号验证 + 数据抓取 + 开盘 + 回填） ──

    def _set_lottery_chase_mode(self, lottery_type_id: int, chase: bool) -> None:
        """启用或禁用指定彩种的加速追赶模式。"""
        if not hasattr(self, "_chase_modes"):
            self._chase_modes: dict[int, bool] = {}
        self._chase_modes[lottery_type_id] = chase
        if chase:
            _crawler_logger.warning("Chase mode enabled for lt=%s", lottery_type_id)

    def _open_specific_records(self, lottery_type_id: int, latest_draw: dict[str, Any] | None = None) -> int:
        """立即对刚 upsert 的记录执行开盘（is_opened=1），延迟 ≤ 1 秒。

        若传入 latest_draw，仅开盘匹配的 year+term 记录；
        否则回退为开盘该彩种所有未开奖且 draw_time 已过的记录。

        Returns:
            开盘的记录数。
        """
        now_utc_dt = datetime.now(timezone.utc)
        now_beijing = (now_utc_dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        now_utc = now_utc_dt.strftime("%Y-%m-%d %H:%M:%S")

        with db_connect(self.db_path) as conn:
            if latest_draw and latest_draw.get("year") and latest_draw.get("term"):
                year = int(latest_draw["year"])
                term = int(latest_draw["term"])
                cur = conn.execute(
                    """UPDATE lottery_draws SET is_opened = 1, updated_at = ?
                       WHERE lottery_type_id = ? AND year = ? AND term = ?
                       AND is_opened = 0""",
                    (now_utc, int(lottery_type_id), year, term),
                )
            else:
                cur = conn.execute(
                    """UPDATE lottery_draws SET is_opened = 1, updated_at = ?
                       WHERE lottery_type_id = ? AND is_opened = 0
                       AND draw_time IS NOT NULL AND draw_time != ''
                       AND draw_time <= ?""",
                    (now_utc, int(lottery_type_id), now_beijing),
                )
            return cur.rowcount

    def _do_precise_draw_fetch_and_open(self, lottery_type_id: int) -> dict[str, Any]:
        """精确开奖完整管线：验证期号 → 拉取数据 → 入库 → 开盘 → 回填 → 同步。

        当期号匹配时，立即执行完整数据获取管线；期号不匹配时保留原有 4 次重试+告警逻辑；
        期号匹配但数据拉取失败时降级为告警+加速轮询。

        Returns:
            {"status": "ok"|"mismatch"|"fetch_failed"|"deferred"|"error", "detail": str, "upsert_result": dict|None}
        """
        cfg_prefix = _LT_CFG_PREFIX.get(lottery_type_id)
        if not cfg_prefix:
            return {"status": "error", "detail": "no cfg_prefix", "upsert_result": None}

        lt_name = _LT_NAME_MAP.get(lottery_type_id, str(lottery_type_id))
        current_period = str(_cfg(self.db_path, f"{cfg_prefix}_current_period", ""))
        expected_period = _compute_next_period(current_period)

        if not expected_period:
            _crawler_logger.warning(
                "Precise fetch lt=%s: cannot compute next period from current=%s",
                lottery_type_id, current_period,
            )
            return {"status": "error", "detail": "cannot compute next period", "upsert_result": None}

        # ── Phase 1: 验证期号匹配（最多 4 次重试） ──
        period_matched = False
        for attempt in range(4):
            if attempt > 0:
                time.sleep(2)
                _next = str(_cfg(self.db_path, f"{cfg_prefix}_next_time", ""))
                if _next:
                    try:
                        _next_dt = datetime.fromtimestamp(int(_next) / 1000, tz=timezone.utc)
                        _now_dt = datetime.now(timezone.utc)
                        if _next_dt > _now_dt + timedelta(seconds=10):
                            _crawler_logger.info(
                                "Precise fetch lt=%s: next_time updated to %s, deferring",
                                lottery_type_id, _next_dt.isoformat(),
                            )
                            return {"status": "deferred", "detail": "next_time updated", "upsert_result": None}
                    except (ValueError, OSError):
                        pass

            period, error = _fetch_current_draw_period(lottery_type_id, self.db_path)

            if period and period == expected_period:
                period_matched = True
                _crawler_logger.info(
                    "Precise fetch lt=%s: period matched expected=%s (attempt=%d)",
                    lottery_type_id, expected_period, attempt + 1,
                )
                break

            _crawler_logger.warning(
                "Precise fetch lt=%s: MISMATCH expected=%s actual=%s error=%s (attempt=%d/4)",
                lottery_type_id, expected_period, period or "N/A", error or "N/A",
                attempt + 1,
            )

        if not period_matched:
            final_period, final_error = _fetch_current_draw_period(lottery_type_id, self.db_path)
            final_actual = final_period or f"error: {final_error}"
            _trigger_draw_mismatch_alert(
                self.db_path, lottery_type_id, expected_period, final_actual, 4,
            )
            try:
                alert_precise_draw_mismatch(
                    self.db_path, lottery_type_id, expected_period, final_actual, 4,
                )
            except Exception:
                pass
            _crawler_logger.error(
                "Precise fetch lt=%s: ALL ATTEMPTS FAILED expected=%s final_actual=%s",
                lottery_type_id, expected_period, final_actual,
            )
            self._set_lottery_chase_mode(lottery_type_id, True)
            return {"status": "mismatch", "detail": f"expected={expected_period} actual={final_actual}", "upsert_result": None}

        # ── Phase 2: 拉取完整开奖记录 ──
        t0 = datetime.now(timezone.utc)
        records: list[dict[str, Any]] = []
        fetch_error: str | None = None
        try:
            records = _fetch_current_draw_records(self.db_path, lottery_type_id)
        except Exception as exc:
            fetch_error = str(exc)
            _crawler_logger.error("Precise fetch lt=%s: full record fetch failed: %s", lottery_type_id, exc)

        if not records:
            _crawler_logger.warning(
                "Precise fetch lt=%s: period matched but no records returned (error=%s)",
                lottery_type_id, fetch_error or "empty response",
            )
            _log_draw_audit(
                self.db_path, lottery_type_id, expected_period,
                event="precise_fetch", status="failed",
                detail=f"period matched but no records; error={fetch_error or 'empty_response'}",
                duration_ms=int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
            )
            self._set_lottery_chase_mode(lottery_type_id, True)
            return {"status": "fetch_failed", "detail": fetch_error or "empty records", "upsert_result": None}

        # ── Phase 3: Upsert 到 lottery_draws ──
        t_upsert = datetime.now(timezone.utc)
        upsert_result = _upsert_current_draw_records(self.db_path, lottery_type_id, records)
        inserted = upsert_result.get("inserted", 0)
        updated = upsert_result.get("updated", 0)
        upsert_duration_ms = int((datetime.now(timezone.utc) - t_upsert).total_seconds() * 1000)

        _crawler_logger.info(
            "Precise fetch lt=%s: upserted inserted=%d updated=%d period=%s",
            lottery_type_id, inserted, updated, expected_period,
        )
        _log_draw_audit(
            self.db_path, lottery_type_id, expected_period,
            event="precise_upsert", status="success",
            detail=f"inserted={inserted} updated={updated}",
            duration_ms=upsert_duration_ms,
        )

        if inserted > 0 or updated > 0:
            reset_crawler_fail_count(self.db_path, lottery_type_id)
            self._set_lottery_chase_mode(lottery_type_id, False)

            # ── Phase 4: 立即开盘 ──
            t_open = datetime.now(timezone.utc)
            try:
                opened = self._open_specific_records(lottery_type_id, upsert_result.get("latest_draw"))
                open_duration_ms = int((datetime.now(timezone.utc) - t_open).total_seconds() * 1000)
                _crawler_logger.info("Precise fetch lt=%s: opened %d record(s)", lottery_type_id, opened)
                _log_draw_audit(
                    self.db_path, lottery_type_id, expected_period,
                    event="precise_open", status="success",
                    detail=f"opened={opened}",
                    duration_ms=open_duration_ms,
                )
            except Exception as exc:
                _crawler_logger.error("Precise fetch lt=%s: open failed: %s", lottery_type_id, exc)

            # ── Phase 5: 延迟回填开奖结果（预测由 daily_prediction 统一生成） ──
            try:
                _schedule_backfill_after_draw(self.db_path, lottery_type_id)
            except Exception as exc:
                _crawler_logger.error("Precise fetch lt=%s: backfill schedule failed: %s", lottery_type_id, exc)

        total_duration_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
        _log_draw_audit(
            self.db_path, lottery_type_id, expected_period,
            event="precise_complete", status="success",
            detail=f"inserted={inserted} updated={updated}",
            duration_ms=total_duration_ms,
        )

        return {
            "status": "ok",
            "detail": f"period={expected_period} inserted={inserted} updated={updated}",
            "upsert_result": upsert_result,
        }

    # ── 动态轮询 + 分级告警 ──

    def _compute_dynamic_crawl_interval(self) -> int:
        """根据距离最近开奖时间窗口计算 auto_crawl 的动态轮询间隔。

        - 追赶模式 → crawl_interval_chase（默认 5s）
        - 开奖窗口（±5 分钟）→ crawl_interval_near_draw（默认 10s）
        - 平时 → crawl_interval_far_draw（默认 300s）
        """
        if hasattr(self, "_chase_modes") and any(self._chase_modes.values()):
            return max(5, int(_cfg(self.db_path, "crawler.crawl_interval_chase", 5)))

        near_interval = max(5, int(_cfg(self.db_path, "crawler.crawl_interval_near_draw", 10)))
        far_interval = max(30, int(_cfg(self.db_path, "crawler.crawl_interval_far_draw", 300)))
        window = timedelta(minutes=5)
        now_dt = datetime.now(timezone.utc)

        for lt_id in [1, 2, 3]:
            cfg_prefix = _LT_CFG_PREFIX.get(lt_id)
            if not cfg_prefix:
                continue
            next_time_str = str(_cfg(self.db_path, f"{cfg_prefix}_next_time", ""))
            if not next_time_str:
                continue
            try:
                next_ms = int(next_time_str)
                if next_ms <= 0:
                    continue
                target_dt = datetime.fromtimestamp(next_ms / 1000, tz=timezone.utc)
                if abs(now_dt - target_dt) <= window:
                    return near_interval
            except (ValueError, OSError):
                continue
        return far_interval

    def _check_staged_timeout_alerts(self) -> None:
        """分级超时告警：检查各彩种开奖时间已过是否数据仍未入库。

        - 黄色 30s：日志 WARNING + 加速轮询
        - 橙色 120s：邮件告警 + 尝试备用 URL
        - 红色 300s：邮件告警 + 标记延迟
        """
        yellow_s = int(_cfg(self.db_path, "alert.draw_yellow_timeout_seconds", 30))
        orange_s = int(_cfg(self.db_path, "alert.draw_orange_timeout_seconds", 120))
        red_s = int(_cfg(self.db_path, "alert.draw_red_timeout_seconds", 300))
        now_dt = datetime.now(timezone.utc)

        for lt_id in [1, 2, 3]:
            cfg_prefix = _LT_CFG_PREFIX.get(lt_id)
            if not cfg_prefix:
                continue
            next_time_str = str(_cfg(self.db_path, f"{cfg_prefix}_next_time", ""))
            if not next_time_str:
                continue
            try:
                next_ms = int(next_time_str)
                if next_ms <= 0:
                    continue
                target_dt = datetime.fromtimestamp(next_ms / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                continue

            if target_dt > now_dt:
                self._set_lottery_chase_mode(lt_id, False)
                continue

            seconds_past = int((now_dt - target_dt).total_seconds())
            lt_name = _LT_NAME_MAP.get(lt_id, str(lt_id))

            # 检查数据是否已到达
            current_period = str(_cfg(self.db_path, f"{cfg_prefix}_current_period", ""))
            expected_period = _compute_next_period(current_period) if current_period else ""
            actual_period, _ = _fetch_current_draw_period(lt_id, self.db_path)

            if actual_period and expected_period and actual_period == expected_period:
                self._set_lottery_chase_mode(lt_id, False)
                continue

            if seconds_past >= red_s:
                _crawler_logger.error(
                    "RED ALERT: %s draw overdue by %ds (target=%s)",
                    lt_name, seconds_past, target_dt.isoformat(),
                )
                alert_crawler_failure(
                    self.db_path, lt_id,
                    f"开奖后 {seconds_past}s 数据未入库（红色告警，需人工介入）",
                )
                self._set_lottery_chase_mode(lt_id, True)
            elif seconds_past >= orange_s:
                _crawler_logger.warning(
                    "ORANGE ALERT: %s draw overdue by %ds (target=%s)",
                    lt_name, seconds_past, target_dt.isoformat(),
                )
                alert_crawler_failure(
                    self.db_path, lt_id,
                    f"开奖后 {seconds_past}s 数据未入库（橙色告警）",
                )
                self._set_lottery_chase_mode(lt_id, True)
            elif seconds_past >= yellow_s:
                _crawler_logger.warning(
                    "YELLOW ALERT: %s draw overdue by %ds, accelerating polling",
                    lt_name, seconds_past,
                )
                self._set_lottery_chase_mode(lt_id, True)

    def _reschedule_precise_checks(self) -> None:
        """为 HK(1)、Macau(2)、Taiwan(3) 分别安排精确开奖检查。

        从 system_config 读取 lottery.{hk,macau,taiwan}_next_time（毫秒时间戳），
        计算在距离该时间点前 1 秒触发。管理员通过后台修改 lottery.{type}_next_time
        后，下一次轮询（最多 60 秒）会自动按新时间重新调度。

        - HK/Macau (1,2): 触发 _do_precise_draw_check（HTTP 请求验证期号）
        - Taiwan (3):     触发开奖 + 更新 next_time + 延迟回填
        """
        for lt_id in [1, 2, 3]:
            # 取消旧的定时器
            if lt_id in self._precise_timers:
                self._precise_timers[lt_id].cancel()
                del self._precise_timers[lt_id]

            cfg_prefix = _LT_CFG_PREFIX.get(lt_id)
            if not cfg_prefix:
                continue

            next_time_ms_str = str(_cfg(self.db_path, f"{cfg_prefix}_next_time", ""))
            if not next_time_ms_str:
                # 未配置时使用默认开奖时间回退计算
                if lt_id == 3:
                    next_time_ms_str = _compute_taiwan_default_next_time_ms(self.db_path)
                    if not next_time_ms_str:
                        continue
                elif lt_id in (1, 2):
                    next_time_ms_str = _compute_hk_macau_default_next_time_ms(self.db_path, lt_id)
                    if not next_time_ms_str:
                        _crawler_logger.warning(
                            "Precise check lt=%s: cannot compute default next_time, skipping",
                            lt_id,
                        )
                        continue
                else:
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
                        "Precise check lt=%s: target %s already passed, rescheduling for next cycle",
                        lt_id, fire_at.isoformat(),
                    )
                    # 时间已过，立即触发一次同步以刷新 next_time
                    if self._running:
                        _crawler_logger.info(
                            "Precise check lt=%s: fire time passed, triggering immediate sync",
                            lt_id,
                        )
                        try:
                            if lt_id == 3:
                                self._open_taiwan_draws_and_update_next_time()
                                _schedule_backfill_after_draw(self.db_path, 3)
                            else:
                                self._do_precise_draw_fetch_and_open(lt_id)
                        except Exception as exc:
                            _crawler_logger.error(
                                "Precise check lt=%s immediate fire error: %s", lt_id, exc
                            )
                        # 触发后重新同步 next_time 并调度下一次
                        sync_all_lottery_type_next_times(self.db_path, source="crawler.precise_passed")
                        self._reschedule_precise_checks()
                    continue

                def _fire(_lt_id=lt_id, _db=self.db_path):
                    try:
                        if _lt_id == 3:
                            self._open_taiwan_draws_and_update_next_time()
                            _schedule_backfill_after_draw(_db, 3)
                        else:
                            self._do_precise_draw_fetch_and_open(_lt_id)
                    except Exception as exc:
                        _crawler_logger.error("Precise check lt=%s unhandled error: %s", _lt_id, exc)
                    finally:
                        # 检查完毕后同步 next_time 并重新调度
                        try:
                            sync_all_lottery_type_next_times(_db, source="crawler.precise_fire")
                        except Exception:
                            pass
                        if self._running:
                            self._reschedule_precise_checks()

                timer = threading.Timer(delay, _fire)
                timer.daemon = True
                timer.start()
                self._precise_timers[lt_id] = timer

                lt_name = _LT_NAME_MAP.get(lt_id, str(lt_id))
                _crawler_logger.info(
                    "Precise check %s lt=%s scheduled at %s (delay=%.0fs)",
                    lt_name, lt_id, fire_at.isoformat(), delay,
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
        # 每日固定时间自动预测任务
        _ensure_daily_prediction_task(self.db_path)
        _ensure_postgres_backup_tasks(self.db_path)
        # 如果今天配置的时间已过且今天尚未执行过预测，立即补跑一次
        self._run_daily_prediction_if_missed()
        # 精确开奖检查（HK/Macau/Taiwan 均基于 system_config 中 lottery.{type}_next_time 调度）
        # Taiwan 不再使用独立的 22:30 硬编码任务，统一由此处调度
        self._reschedule_precise_checks()

    def _run_daily_prediction_if_missed(self) -> None:
        """检查今天是否已错过 daily_prediction_cron_time 且尚未执行，若是则立即补跑。"""
        try:
            time_str = str(_cfg(self.db_path, "daily_prediction_cron_time", "12:00")).strip()
            parts = time_str.split(":")
            target_hour = int(parts[0])
            target_minute = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            target_hour = 12
            target_minute = 0

        now_utc = datetime.now(timezone.utc)
        beijing_now = now_utc + timedelta(hours=8)
        target_beijing = beijing_now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # 今天配置的时间还没到，不用补跑
        if beijing_now < target_beijing:
            return

        # 检查今天是否已经执行过
        today_str = beijing_now.strftime("%Y-%m-%d")
        try:
            with db_connect(self.db_path) as conn:
                existing = conn.execute(
                    f"SELECT 1 FROM {TASK_TABLE_NAME} "
                    "WHERE task_type = ? AND status = 'done' AND payload_json LIKE ? "
                    "ORDER BY run_at DESC LIMIT 1",
                    (TASK_TYPE_DAILY_PREDICTION, f"%{today_str}%"),
                ).fetchone()
                if existing:
                    _crawler_logger.info(
                        "Daily prediction already completed for %s, skipping catch-up run",
                        today_str,
                    )
                    return
        except Exception:
            pass

        _crawler_logger.info(
            "Daily prediction missed for %s (scheduled %02d:%02d Beijing), running now",
            today_str, target_hour, target_minute,
        )
        for lt_id in [1, 2, 3]:
            try:
                _run_auto_prediction(self.db_path, lt_id)
            except Exception as exc:
                _crawler_logger.error(
                    "Catch-up prediction lt=%s failed: %s", lt_id, exc,
                )
        # 补跑后检查预测数据是否覆盖到目标期号
        try:
            alert_prediction_gap(self.db_path)
        except Exception:
            pass
        # 补跑后重新调度明天的任务
        _ensure_daily_prediction_task(self.db_path)

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

            # 如果有任何彩种开奖，刷新 next_time 同步并重新调度精确检查
            if pending:
                try:
                    sync_all_lottery_type_next_times(
                        self.db_path, source="crawler.auto_open",
                    )
                    self._reschedule_precise_checks()
                except Exception:
                    pass
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
        """动态间隔自动爬取：根据开奖窗口距离动态调整轮询频率。

        - 追赶模式：5s
        - 开奖窗口（±5min）：10s
        - 平时：300s
        """
        if not self._running:
            return
        self._auto_crawl()
        interval = self._compute_dynamic_crawl_interval()
        _crawler_logger.debug("Auto-crawl next in %ds", interval)
        self._auto_crawl_timer = threading.Timer(interval, self._schedule_auto_crawl)
        self._auto_crawl_timer.daemon = True
        self._auto_crawl_timer.start()

    def _auto_crawl(self) -> None:
        """自动爬取：按外部 API 当前期号与本地期号比对，决定是否爬取。

        遍历启用的香港彩/澳门彩，调用当前开奖 API 获取 actual issue/open_time/result/next_time，
        解析为标准 records 后逐条与本地 lottery_draws 比对：
        - 不存在 → 插入
        - 存在但 numbers/draw_time/next_time 不一致 → 更新
        - 完全一致 → 跳过

        只有确实新增或更新了开奖记录，才触发自动预测任务 + 立即开盘。
        单个彩种失败不影响另一个彩种。
        """
        try:
            with db_connect(self.db_path) as conn:
                lt_rows = conn.execute(
                    "SELECT id, name FROM lottery_types WHERE status = 1 AND id IN (1, 2)"
                ).fetchall()
        except Exception as e:
            _crawler_logger.error("Auto-crawl: failed to query lottery_types: %s", e)
            lt_rows = []

        for lt_row in lt_rows:
            lt_id = int(lt_row["id"])
            lt_name = str(lt_row["name"])

            try:
                records = _fetch_current_draw_records(self.db_path, lt_id)

                if not records:
                    _crawler_logger.warning(
                        "Auto-crawl %s: API returned no records", lt_name
                    )
                    alert_crawler_failure(self.db_path, lt_id, "API returned no records")
                    continue

                result = _upsert_current_draw_records(self.db_path, lt_id, records)
                inserted = result.get("inserted", 0)
                updated = result.get("updated", 0)
                skipped = result.get("skipped", 0)

                if inserted > 0 or updated > 0:
                    _crawler_logger.info(
                        "Auto-crawl %s: inserted=%d updated=%d skipped=%d",
                        lt_name, inserted, updated, skipped,
                    )
                    reset_crawler_fail_count(self.db_path, lt_id)
                    self._set_lottery_chase_mode(lt_id, False)
                    # 立即开盘（不再等待 auto_open 轮询）
                    opened_count = self._open_specific_records(lt_id, result.get("latest_draw"))
                    if opened_count > 0:
                        _crawler_logger.info(
                            "Auto-crawl %s: auto-opened %d record(s)", lt_name, opened_count,
                        )
                    # 延迟回填（预测由 daily_prediction 统一生成）
                    try:
                        _schedule_backfill_after_draw(self.db_path, lt_id)
                    except Exception as exc:
                        _crawler_logger.error(
                            "Auto-crawl %s backfill schedule failed: %s", lt_name, exc
                        )
                else:
                    _crawler_logger.info(
                        "Auto-crawl %s: all %d record(s) already up-to-date, skipped",
                        lt_name, skipped,
                    )
                    reset_crawler_fail_count(self.db_path, lt_id)
            except Exception as exc:
                _crawler_logger.warning("Auto-crawl %s failed: %s", lt_name, exc)
                alert_crawler_failure(self.db_path, lt_id, str(exc))

        # 分级超时告警
        try:
            self._check_staged_timeout_alerts()
        except Exception as exc:
            _crawler_logger.warning("Staged timeout check failed: %s", exc)

        try:
            sync_all_lottery_type_next_times(
                self.db_path,
                source="crawler.periodic_sync",
            )
            self._reschedule_precise_checks()
        except Exception as exc:
            _crawler_logger.warning("Periodic next_time sync failed: %s", exc)
        try:
            alert_draw_staleness(self.db_path)
        except Exception:
            pass

    def _schedule_task_loop(self) -> None:
        if not self._running:
            return
        try:
            self._run_due_tasks()
        except Exception as exc:
            _crawler_logger.error("Task loop iteration failed: %s", exc)
        self._task_timer = threading.Timer(_task_poll_interval_seconds(self.db_path), self._schedule_task_loop)
        self._task_timer.daemon = True
        self._task_timer.start()

    def _run_due_tasks(self) -> None:
        try:
            tasks = _acquire_due_scheduler_tasks(self.db_path, worker_id=self._worker_id, limit=10)
        except Exception as exc:
            _crawler_logger.error("Failed to acquire scheduler tasks: %s", exc)
            return
        for task in tasks:
            try:
                _crawler_logger.info(
                    "Task acquired: type=%s key=%s run_at=%s",
                    task.get("task_type"), task.get("task_key"), task.get("run_at"),
                )
                self._execute_task(task)
                _mark_scheduler_task_done(self.db_path, int(task["id"]))
            except Exception as exc:
                _mark_scheduler_task_failed(self.db_path, task, exc)
                if str(task.get("task_type") or "") == TASK_TYPE_POSTGRES_BACKUP:
                    try:
                        from crawler.postgres_backup import send_backup_failure_alert

                        attempt_no = int(task.get("attempt_count") or 0)
                        max_attempts = int(task.get("max_attempts") or 2)
                        send_backup_failure_alert(
                            self.db_path,
                            error_message=str(exc),
                            attempt_no=attempt_no,
                            final=attempt_no >= max_attempts,
                        )
                    except Exception as alert_exc:
                        _crawler_logger.error("PostgresBackup alert failed: %s", alert_exc)
                _crawler_logger.exception("Scheduler task failed: %s", task.get("task_key"))

    def _execute_task(self, task: dict[str, Any]) -> None:
        task_type = str(task.get("task_type") or "")
        payload = json.loads(str(task.get("payload_json") or "{}"))
        # TASK_TYPE_AUTO_PREDICTION 已废弃——预测生成严格限定为 daily_prediction 和管理后台手动触发。
        # 该 task_type 不再被创建（_schedule_auto_prediction 已注释），此处理器保留日志用于审计。
        if task_type == TASK_TYPE_AUTO_PREDICTION:
            _crawler_logger.warning(
                "Rejected deprecated auto_prediction task (lottery_type_id=%s). "
                "Prediction generation is restricted to daily_prediction task and admin manual triggers.",
                payload.get("lottery_type_id"),
            )
            return
        if task_type == TASK_TYPE_TAIWAN_PRECISE_OPEN:
            self._open_taiwan_draws_and_update_next_time()
            sync_all_lottery_type_next_times(self.db_path, source="crawler.taiwan_open")
            _ensure_taiwan_precise_open_task(self.db_path)
            _schedule_backfill_after_draw(self.db_path, 3)
            self._reschedule_precise_checks()
            return
        if task_type == TASK_TYPE_DAILY_PREDICTION:
            # 对所有活跃彩种执行预测生成，然后调度次日任务
            for lt_id in [1, 2, 3]:
                try:
                    _run_auto_prediction(self.db_path, lt_id)
                except Exception as exc:
                    _crawler_logger.error("DailyPrediction lt=%s failed: %s", lt_id, exc)
                    # 预测生成失败也触发爬虫失败报警
                    alert_crawler_failure(self.db_path, lt_id, str(exc))
            _ensure_daily_prediction_task(self.db_path)
            # 每日预测完成后，检查预测数据是否覆盖到目标期号
            try:
                alert_prediction_gap(self.db_path)
            except Exception:
                pass
            return
        if task_type == TASK_TYPE_POSTGRES_BACKUP:
            from crawler.postgres_backup import run_postgres_backup

            result = run_postgres_backup(self.db_path, payload)
            _crawler_logger.info("PostgresBackup done: %s", result)
            _ensure_postgres_backup_tasks(self.db_path)
            return
        if task_type == "backfill_after_draw":
            _backfill_latest_opened_prediction_results(
                self.db_path,
                int(payload["lottery_type_id"]),
            )
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


def _schedule_backfill_after_draw(db_path: str | Path, lottery_type_id: int) -> None:
    """开奖后延迟执行历史回填任务。

    延迟分钟数由 system_config 表 history_backfill_delay_after_draw 控制（默认 5 分钟）。
    管理员可在后台实时修改此延迟时间。
    """
    delay_minutes = float(_cfg(db_path, "history_backfill_delay_after_draw", 5))
    if delay_minutes <= 0:
        # 延迟为 0 或负数时立即执行回填
        _backfill_latest_opened_prediction_results(db_path, lottery_type_id)
        return

    target_dt = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    _upsert_scheduler_task(
        db_path,
        task_type="backfill_after_draw",
        payload={"lottery_type_id": int(lottery_type_id)},
        run_at=target_dt.isoformat(),
        max_attempts=1,
    )
    _crawler_logger.info(
        "Backfill scheduled for lt=%s in %.1f minutes (at %s)",
        lottery_type_id, delay_minutes, target_dt.isoformat(),
    )


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

        result = _backfill_draw_to_predictions(
            db_path,
            int(lottery_type_id),
            year,
            term,
            numbers_str,
        )
        backfilled = result.get("total_updated", 0)
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
) -> dict[str, Any]:
    """将开奖结果回填到 created schema 的预测记录中。

    遍历所有 mode_payload 表，找到同 year+term+type 的 created 记录，
    回填 res_code（开奖号码）、res_sx（生肖）、res_color（波色）。

    匹配条件：res_code / res_sx / res_color 任意一个为空或纯逗号即回填。

    :return: {total_updated, per_table: [{table, updated}]}
    """
    from helpers import load_fixed_data_maps
    from domains.prediction.regeneration_service import compute_res_fields as _compute_res_fields
    from utils.created_prediction_store import (
        CREATED_SCHEMA_NAME, quote_qualified_identifier, schema_table_exists,
    )

    total_updated = 0
    per_table: dict[str, int] = {}
    try:
        with db_connect(db_path) as conn:
            zodiac_map, color_map = load_fixed_data_maps(conn)
            res_sx, res_color = _compute_res_fields(numbers_str, zodiac_map, color_map)

            tables = conn.list_tables("mode_payload_")
            for table_name in tables:
                if not schema_table_exists(conn, CREATED_SCHEMA_NAME, table_name):
                    continue
                qualified = quote_qualified_identifier(CREATED_SCHEMA_NAME, table_name)
                try:
                    cur = conn.execute(
                        f"UPDATE {qualified} SET res_code = ?, res_sx = ?, res_color = ? "
                        "WHERE type = ? AND year = ? AND term = ? "
                        "AND ("
                        "  res_code IS NULL OR res_code = '' OR REPLACE(res_code, ',', '') = '' "
                        "  OR res_sx IS NULL OR res_sx = '' OR REPLACE(res_sx, ',', '') = '' "
                        "  OR res_color IS NULL OR res_color = '' OR REPLACE(res_color, ',', '') = '' "
                        ")",
                        (numbers_str, res_sx, res_color,
                         str(lottery_type_id), str(year), str(term)),
                    )
                    if cur.rowcount > 0:
                        total_updated += cur.rowcount
                        per_table[table_name] = cur.rowcount
                except Exception:
                    continue
            conn.commit()

        if per_table:
            tables_log = ", ".join(
                f"{t}={c}" for t, c in sorted(per_table.items())
            )
            _crawler_logger.info(
                "AutoPred backfill lt=%s period=%s/%s: total=%d 按表: %s",
                lottery_type_id, year, term, total_updated, tables_log,
            )
    except Exception as e:
        _crawler_logger.error("AutoPred backfill error: %s", e)
    return {"total_updated": total_updated, "per_table": per_table}


def _run_auto_prediction(db_path: str | Path, lottery_type_id: int, *, trigger: str = "auto") -> None:
    """自动执行：回填开奖 + 生成下一期预测。

    回填（_backfill_draw_to_predictions）不受覆盖保护限制——每次开奖后必须更新 res_sx/res_color。
    预测生成受覆盖保护：当 trigger="auto" 时，若目标期数已存在非空预测数据，跳过并记录警告。
    手动触发（trigger="manual"）不限制覆盖。
    """
    if trigger == "auto" and not getattr(_run_auto_prediction, "_worker_mode", False):
        _run_daily_prediction_subprocess(db_path, lottery_type_id)
        return
    _crawler_logger.info("AutoPred starting for lt=%s trigger=%s...", lottery_type_id, trigger)
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

        # 2. 回填开奖结果到预测记录（始终执行，不受覆盖保护限制）
        result = _backfill_draw_to_predictions(db_path, lottery_type_id, year, term, numbers_str)
        backfilled = result.get("total_updated", 0)

        # 3. 计算目标未来期号
        max_terms = int(_cfg(db_path, "prediction.max_terms_per_year", 365))
        next_year, next_term = _compute_next_issue(year, term, 1)
        issue_str = f"{next_year}{next_term:03d}"

        # 3.5 检查并回补近期缺失的预测数据（向前追溯 N 期）
        try:
            recent_report = _ensure_recent_periods_have_predictions(
                db_path, lottery_type_id, year, term,
            )
            _crawler_logger.info(
                "AutoPred recent backfill lt=%s: checked=%d missing=%d generated=%d errors=%d",
                lottery_type_id,
                recent_report["checked"], recent_report["missing"],
                recent_report["generated"], recent_report["errors"],
            )
        except Exception as exc:
            _crawler_logger.error("AutoPred recent backfill lt=%s failed: %s", lottery_type_id, exc)

        # 4. 覆盖保护：自动触发时检查是否已存在预测数据
        if trigger == "auto" and _future_issue_has_predictions(db_path, lottery_type_id, next_year, next_term):
            _crawler_logger.warning(
                "AutoPred SKIP lt=%s: future issue %s/%s already has prediction data. "
                "Use manual trigger to overwrite.",
                lottery_type_id, next_year, next_term,
            )
            _update_auto_task_status(db_path, lottery_type_id, "skipped",
                                     f"future issue {next_year}/{next_term} already has predictions")
            return

        # 5. 生成未来下一期预测（遍历所有启用站点）
        from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
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
                            "trigger": "daily_prediction",
                            "allow_overwrite": False,
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


def _log_backfill_event(
    db_path: str | Path,
    lottery_type_id: int,
    period: str,
    action: str,
    detail: str = "",
) -> None:
    """将回补检查/生成事件写入 error_logs 表（INFO 级别），供管理后台查询。"""
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with db_connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO error_logs (
                    created_at, level, logger_name, module, func_name,
                    file_path, line_number, message, lottery_type_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts, "INFO", "prediction.backfill", "scheduler",
                    "_ensure_recent_periods", __file__, 0,
                    f"[回补] 期号={period} 动作={action} {detail}".strip(),
                    lottery_type_id,
                ),
            )
    except Exception:
        pass


def _ensure_recent_periods_have_predictions(
    db_path: str | Path,
    lottery_type_id: int,
    current_year: int,
    current_term: int,
) -> dict[str, Any]:
    """检查并回补近期缺失的预测数据。

    从当前期号向前追溯 prediction.recent_period_count 期，
    检查每期是否已有预测数据，若缺失则自动生成。

    :return: 回补报告 {checked, missing, generated, errors, periods}
    """
    recent_count = int(_cfg(db_path, "prediction.recent_period_count", 10))
    if recent_count <= 0:
        return {"checked": 0, "missing": 0, "generated": 0, "errors": 0, "periods": []}

    max_terms = int(_cfg(db_path, "prediction.max_terms_per_year", 365))

    # 计算追溯起始期号
    start_year, start_term = current_year, current_term
    for _ in range(recent_count - 1):
        if start_term > 1:
            start_term -= 1
        else:
            start_year -= 1
            start_term = max_terms

    _crawler_logger.info(
        "Recent-period check: lt=%s range=%s/%s-%s/%s (count=%d)",
        lottery_type_id, start_year, start_term, current_year, current_term, recent_count,
    )

    # 获取范围内所有已开奖记录、站点和模块配置
    opened_map: dict[tuple[int, int], dict[str, Any]] = {}
    enabled_sites: list[int] = []
    site_web_ids: dict[int, int] = {}
    site_modules: dict[int, list[dict[str, Any]]] = {}
    try:
        with db_connect(db_path) as conn:
            rows = conn.execute(
                """SELECT year, term, numbers FROM lottery_draws
                   WHERE lottery_type_id = ? AND is_opened = 1
                     AND numbers IS NOT NULL AND numbers != ''
                   ORDER BY year ASC, term ASC""",
                (lottery_type_id,),
            ).fetchall()
            for row in rows:
                y, t = int(row["year"] or 0), int(row["term"] or 0)
                if (start_year, start_term) <= (y, t) <= (current_year, current_term):
                    opened_map[(y, t)] = dict(row)

            enabled_site_rows = conn.execute(
                """
                SELECT id, web_id
                FROM managed_sites
                WHERE enabled = 1
                """
            ).fetchall()
            enabled_sites = []
            for site_row in enabled_site_rows:
                site_id = int(site_row["id"] or 0)
                web_id = int(site_row["web_id"] or 0)
                if site_id <= 0 or web_id <= 0:
                    continue
                enabled_sites.append(site_id)
                site_web_ids[site_id] = web_id

            for site_id in enabled_sites:
                module_rows = conn.execute(
                    """
                    SELECT mechanism_key, mode_id
                    FROM site_prediction_modules
                    WHERE site_id = ? AND status = 1
                    ORDER BY sort_order, id
                    """,
                    (site_id,),
                ).fetchall()
                normalized_modules: list[dict[str, Any]] = []
                for row in module_rows:
                    try:
                        mechanism_key = str(row["mechanism_key"] or "").strip()
                        mode_id = int(row["mode_id"] or 0)
                    except (TypeError, ValueError):
                        continue
                    if not mechanism_key or mode_id <= 0:
                        continue
                    normalized_modules.append({
                        "mechanism_key": mechanism_key,
                        "mode_id": mode_id,
                        "table_name": f"mode_payload_{mode_id}",
                    })
                site_modules[site_id] = normalized_modules
    except Exception:
        pass

    report: dict[str, Any] = {
        "checked": 0, "missing": 0, "generated": 0, "errors": 0, "periods": [],
    }

    # 遍历范围内每一期，检查预测数据是否存在
    yr, tm = start_year, start_term
    while (yr, tm) <= (current_year, current_term):
        report["checked"] += 1
        period_str = f"{yr}{tm:03d}"
        period_info: dict[str, Any] = {
            "period": period_str, "year": yr, "term": tm,
            "action": "skipped", "detail": "",
        }

        missing_modules_by_site: dict[int, list[str]] = {}
        try:
            from utils.created_prediction_store import created_prediction_issue_exists

            with db_connect(db_path) as conn:
                for site_id in enabled_sites:
                    modules = site_modules.get(site_id) or []
                    web_id = site_web_ids.get(site_id)
                    if web_id is None or not modules:
                        continue
                    for module in modules:
                        if not created_prediction_issue_exists(
                            conn,
                            module["table_name"],
                            lottery_type_id,
                            yr,
                            tm,
                            web_id,
                        ):
                            missing_modules_by_site.setdefault(site_id, []).append(
                                module["mechanism_key"]
                            )
        except Exception as exc:
            report["errors"] += 1
            period_info["action"] = "error"
            period_info["detail"] = f"检查是否缺失预测失败: {exc}"
            _log_backfill_event(db_path, lottery_type_id, period_str, "error", str(exc))
            report["periods"].append(period_info)
            tm += 1
            if tm > max_terms:
                tm = 1
                yr += 1
            continue

        if not missing_modules_by_site:
            period_info["action"] = "skipped_existing"
            period_info["detail"] = "所有启用站点模块均已有预测资料，跳过自动补生成"
            _log_backfill_event(db_path, lottery_type_id, period_str, "skipped_existing", period_info["detail"])
            report["periods"].append(period_info)
            tm += 1
            if tm > max_terms:
                tm = 1
                yr += 1
            continue

        missing_count = sum(len(keys) for keys in missing_modules_by_site.values())
        report["missing"] += missing_count
        missing_sites = sorted(missing_modules_by_site.keys())
        draw = opened_map.get((yr, tm))
        if draw:
            # 历史已开奖期 → 使用真实 res_code 生成
            period_info["detail"] = (
                f"存在缺失模块={missing_modules_by_site}，使用已开奖数据生成 (numbers={draw['numbers']})"
            )
            _crawler_logger.info(
                "Recent-period gap: lt=%s period=%s missing_modules=%s — generating with opened draw",
                lottery_type_id, period_str, missing_modules_by_site,
            )
            _log_backfill_event(db_path, lottery_type_id, period_str,
                                "generating", f"missing_modules={missing_modules_by_site} numbers={draw['numbers']}")
        else:
            # 未开奖或未来期 → 不注入 res_code
            period_info["detail"] = f"存在缺失模块={missing_modules_by_site}，无已开奖数据，按未来期生成"
            _crawler_logger.info(
                "Recent-period gap: lt=%s period=%s missing_modules=%s — generating without res_code",
                lottery_type_id, period_str, missing_modules_by_site,
            )
            _log_backfill_event(db_path, lottery_type_id, period_str,
                                "generating", f"missing_modules={missing_modules_by_site} future period, no res_code")

        # 调用批量生成
        try:
            from admin.prediction import bulk_generate_site_prediction_data as _bulk_gen
            last_gen: dict[str, Any] = {}
            for site_id, mechanism_keys in sorted(missing_modules_by_site.items()):
                gen = _bulk_gen(
                    db_path, int(site_id),
                    {
                        "lottery_type": lottery_type_id,
                        "start_issue": period_str,
                        "end_issue": period_str,
                        "mechanism_keys": mechanism_keys,
                        "future_periods": 0,
                        "future_only": False,
                        "trigger": "daily_prediction_recent_backfill",
                        "allow_overwrite": False,
                    },
                )
                last_gen = gen
                report["generated"] += gen.get("inserted", 0)
                report["errors"] += gen.get("errors", 0)
            period_info["action"] = "generated"
            _log_backfill_event(db_path, lottery_type_id, period_str,
                                "generated", f"sites={missing_sites} inserted={last_gen.get('inserted',0)} skipped={last_gen.get('skipped_existing',0)}")
        except Exception as exc:
            report["errors"] += 1
            period_info["action"] = "error"
            period_info["detail"] += f"; 生成失败: {exc}"
            _log_backfill_event(db_path, lottery_type_id, period_str, "error", str(exc))

        report["periods"].append(period_info)

        # 推进到下一期
        tm += 1
        if tm > max_terms:
            tm = 1
            yr += 1

    _crawler_logger.info(
        "Recent-period check done: lt=%s checked=%d missing=%d generated=%d errors=%d",
        lottery_type_id, report["checked"], report["missing"],
        report["generated"], report["errors"],
    )
    return report


def _future_issue_has_predictions(
    db_path: str | Path, lottery_type_id: int, next_year: int, next_term: int
) -> bool:
    # Only skip when the target issue is complete across all enabled modules.
    # Automatic generation uses allow_overwrite=False, so partial future issues
    # should be retried to fill gaps rather than skipped forever.
    """检查未来期号是否已在 created schema 中存在非空预测数据。

    遍历所有 enabled 站点的所有启用模块，只要任一 created 预测正文已存在，
    自动未来期生成就应跳过，避免部分模块被重生成覆盖。
    """
    from utils.created_prediction_store import created_prediction_issue_exists
    try:
        with db_connect(db_path) as conn:
            module_rows = conn.execute(
                """
                SELECT ms.web_id, spm.mode_id
                FROM site_prediction_modules spm
                JOIN managed_sites ms ON ms.id = spm.site_id
                WHERE ms.enabled = 1 AND spm.status = 1
                """
            ).fetchall()
            if not module_rows:
                return False
            for module_row in module_rows:
                mode_id = int(module_row["mode_id"] or 0)
                web_id = int(module_row["web_id"] or 0)
                if mode_id <= 0 or web_id <= 0:
                    continue
                table_name = f"mode_payload_{mode_id}"
                if not created_prediction_issue_exists(
                    conn,
                    table_name,
                    lottery_type_id,
                    next_year,
                    next_term,
                    web_id,
                ):
                    return False
            return True
    except Exception:
        return False


def _compute_next_issue(year: int, term: int, offset: int) -> tuple[int, int]:
    """计算未来第 offset 期的期号 (year, term)。"""
    max_terms = 365
    new_term = term + offset
    new_year = year
    while new_term > max_terms:
        new_term -= max_terms
        new_year += 1
    return new_year, new_term
def _schedule_auto_prediction(
    db_path: str | Path, lottery_type_id: int, draw_time_str: str
) -> float:
    """安排一次 6 小时后的自动预测任务（已废弃）。

    此功能已暂停，由每日定时预测任务 TASK_TYPE_DAILY_PREDICTION 替代。
    保留此函数仅为向后兼容，调用方应迁移至 _ensure_daily_prediction_task。

    :param draw_time_str: 开奖时间字符串，格式 \"2026-05-10 21:32:59\"
    :return: 延迟秒数
    """
    _crawler_logger.warning(
        "_schedule_auto_prediction is deprecated for lt=%s. Use daily_prediction_cron_time instead.",
        lottery_type_id,
    )
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

    # 调用 result_crawler 获取当前期数据（传入数据库配置的采集地址 + 备用 URL）
    from crawler.result_crawler import fetch_current_term_data, transform_standard_list

    collect_url, backup_url = _get_effective_collect_url(db_path, lottery_type_id)
    crawler_type = 1 if lottery_type_id == 1 else 2
    raw, status_code = fetch_current_term_data(
        type=crawler_type,
        collect_url=collect_url,
        backup_url=backup_url,
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

    # 开奖后 6 小时自动预测已暂停（由每日定时预测任务 TASK_TYPE_DAILY_PREDICTION 覆盖）
    # 如需恢复，请取消下方注释并确保与每日定时任务无重复
    # auto_delay = 0.0
    # if saved > 0 and draw_info.get("open_time"):
    #     auto_delay = _schedule_auto_prediction(db_path, lottery_type_id, draw_info["open_time"])

    return {
        "ok": True,
        "draw": draw_info,
        "saved": saved,
        "fetched": len(records),
        "auto_task_scheduled_seconds": None,
    }
