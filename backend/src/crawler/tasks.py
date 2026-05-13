"""调度器任务管理 —— 任务的 upsert、获取、标记完成/失败。

从 crawler_service.py 提取，供 CrawlerScheduler 和 auto_prediction 模块共用。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from crawler.collectors import _cfg
from db import connect as db_connect

TASK_TABLE_NAME = "scheduler_tasks"
TASK_TYPE_AUTO_PREDICTION = "auto_prediction"
TASK_TYPE_TAIWAN_PRECISE_OPEN = "taiwan_precise_open"
TASK_TYPE_DAILY_PREDICTION = "daily_prediction"


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


def upsert_scheduler_task(
    db_path: str | Path,
    *,
    task_type: str,
    payload: dict[str, Any],
    run_at: str,
    max_attempts: int = 3,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    task_key_str = _task_key(task_type, payload)
    payload_json = _json_dumps(payload)
    with db_connect(db_path) as conn:
        existing = conn.execute(
            f"SELECT id FROM {TASK_TABLE_NAME} WHERE task_key = ? LIMIT 1",
            (task_key_str,),
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
                (task_type, payload_json, run_at, max_attempts, now, task_key_str),
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
                (task_key_str, task_type, payload_json, run_at, max_attempts, now, now),
            )


def acquire_due_scheduler_tasks(db_path: str | Path, *, worker_id: str, limit: int = 10) -> list[dict[str, Any]]:
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


def mark_scheduler_task_done(db_path: str | Path, task_id: int) -> None:
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


def mark_scheduler_task_failed(db_path: str | Path, task: dict[str, Any], exc: Exception) -> None:
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


def ensure_taiwan_precise_open_task(db_path: str | Path) -> None:
    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    hour = int(_cfg(db_path, "crawler.taiwan_precise_open_hour", 22))
    minute = int(_cfg(db_path, "crawler.taiwan_precise_open_minute", 30))
    target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if beijing_now >= target_beijing:
        target_beijing += timedelta(days=1)
    target_utc = target_beijing - timedelta(hours=8)
    upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_TAIWAN_PRECISE_OPEN,
        payload={"schedule_date": target_beijing.strftime("%Y-%m-%d")},
        run_at=target_utc.isoformat(),
        max_attempts=max(1, int(_cfg(db_path, "crawler.taiwan_max_retries", 3))),
    )


def ensure_daily_prediction_task(db_path: str | Path) -> None:
    """每日固定时间自动预测任务。

    触发时间由 system_config 表 daily_prediction_cron_time 控制（默认 12:00 北京时间）。
    管理员可通过后台配置管理页面实时修改，下次调度自动生效。
    """
    time_str = str(_cfg(db_path, "daily_prediction_cron_time", "12:00")).strip()
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
    upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": target_beijing.strftime("%Y-%m-%d")},
        run_at=target_utc.isoformat(),
        max_attempts=3,
    )
