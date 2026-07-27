"""Compatibility facade for persisted scheduler task management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from domains.scheduler import service as _service
from domains.scheduler.service import (
    SCHEDULE_SCOPE_AUTO,
    SCHEDULE_SCOPE_MANUAL,
    TASK_RUN_TABLE_NAME,
    TASK_TABLE_NAME,
    TASK_TYPE_AUTO_PREDICTION,
    TASK_TYPE_DAILY_PREDICTION,
    TASK_TYPE_POSTGRES_BACKUP,
    TASK_TYPE_TAIWAN_PRECISE_OPEN,
    TASK_TYPE_TAIWAN_FUTURE_AUTOFILL,
    _json_dumps,
    _task_key,
    _task_lock_timeout_seconds,
    _task_poll_interval_seconds,
    _task_retry_delay_seconds,
)


def upsert_scheduler_task(
    db_path: str | Path,
    *,
    task_type: str,
    payload: dict[str, Any],
    run_at: str,
    max_attempts: int = 3,
    schedule_scope: str = SCHEDULE_SCOPE_AUTO,
    force_reschedule: bool = False,
    task_key_override: str | None = None,
    created_by: str | None = None,
) -> None:
    return _service.upsert_scheduler_task(
        db_path,
        task_type=task_type,
        payload=payload,
        run_at=run_at,
        max_attempts=max_attempts,
        schedule_scope=schedule_scope,
        force_reschedule=force_reschedule,
        task_key_override=task_key_override,
        created_by=created_by,
    )


def acquire_due_scheduler_tasks(
    db_path: str | Path,
    *,
    worker_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return _service.acquire_due_scheduler_tasks(db_path, worker_id=worker_id, limit=limit)


def run_due_scheduler_tasks(
    db_path: str | Path,
    *,
    worker_id: str,
    execute_task,
    on_task_acquired=None,
    on_task_failed=None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return _service.run_due_scheduler_tasks(
        db_path,
        worker_id=worker_id,
        execute_task=execute_task,
        on_task_acquired=on_task_acquired,
        on_task_failed=on_task_failed,
        limit=limit,
    )


def has_completed_daily_prediction_task(db_path: str | Path, schedule_date: str) -> bool:
    return _service.has_completed_daily_prediction_task(db_path, schedule_date)


def create_scheduler_task_run(
    db_path: str | Path,
    *,
    task: dict[str, Any],
    worker_id: str,
) -> int | None:
    return _service.create_scheduler_task_run(db_path, task=task, worker_id=worker_id)


def finish_scheduler_task_run(
    db_path: str | Path,
    *,
    run_id: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    return _service.finish_scheduler_task_run(
        db_path,
        run_id=run_id,
        status=status,
        error_message=error_message,
    )


def mark_scheduler_task_done(db_path: str | Path, task_id: int) -> None:
    return _service.mark_scheduler_task_done(db_path, task_id)


def mark_scheduler_task_failed(db_path: str | Path, task: dict[str, Any], exc: Exception) -> None:
    return _service.mark_scheduler_task_failed(db_path, task, exc)


def ensure_taiwan_precise_open_task(db_path: str | Path) -> None:
    return _service.ensure_taiwan_precise_open_task(db_path)


def ensure_daily_prediction_task(
    db_path: str | Path,
    *,
    schedule_date: str | None = None,
    run_at: str | None = None,
    force_reschedule: bool = False,
) -> None:
    return _service.ensure_daily_prediction_task(
        db_path,
        schedule_date=schedule_date,
        run_at=run_at,
        force_reschedule=force_reschedule,
    )


def ensure_postgres_backup_tasks(
    db_path: str | Path,
    *,
    force_reschedule: bool = False,
) -> None:
    return _service.ensure_postgres_backup_tasks(
        db_path,
        force_reschedule=force_reschedule,
    )


def ensure_taiwan_future_autofill_task(db_path: str | Path) -> None:
    return _service.ensure_taiwan_future_autofill_task(db_path)


def enqueue_manual_daily_prediction_task(
    db_path: str | Path,
    *,
    lottery_type_ids: list[int] | None = None,
    created_by: str = "unknown",
) -> dict[str, Any]:
    return _service.enqueue_manual_daily_prediction_task(
        db_path,
        lottery_type_ids=lottery_type_ids,
        created_by=created_by,
    )

__all__ = [
    "TASK_TABLE_NAME",
    "TASK_RUN_TABLE_NAME",
    "TASK_TYPE_AUTO_PREDICTION",
    "TASK_TYPE_TAIWAN_PRECISE_OPEN",
    "TASK_TYPE_DAILY_PREDICTION",
    "TASK_TYPE_POSTGRES_BACKUP",
    "TASK_TYPE_TAIWAN_FUTURE_AUTOFILL",
    "SCHEDULE_SCOPE_AUTO",
    "SCHEDULE_SCOPE_MANUAL",
    "_task_poll_interval_seconds",
    "_task_lock_timeout_seconds",
    "_task_retry_delay_seconds",
    "_json_dumps",
    "_task_key",
    "upsert_scheduler_task",
    "acquire_due_scheduler_tasks",
    "run_due_scheduler_tasks",
    "has_completed_daily_prediction_task",
    "create_scheduler_task_run",
    "finish_scheduler_task_run",
    "mark_scheduler_task_done",
    "mark_scheduler_task_failed",
    "ensure_taiwan_precise_open_task",
    "ensure_daily_prediction_task",
    "ensure_postgres_backup_tasks",
    "ensure_taiwan_future_autofill_task",
    "enqueue_manual_daily_prediction_task",
]
