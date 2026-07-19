"""Scheduler task service backed by persisted task tables."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from crawler.collectors import _cfg
from db import connect as db_connect
from security.redaction import redact_value

from . import repository

TASK_TABLE_NAME = repository.TASK_TABLE_NAME
TASK_RUN_TABLE_NAME = repository.TASK_RUN_TABLE_NAME
TASK_TYPE_AUTO_PREDICTION = "auto_prediction"
TASK_TYPE_TAIWAN_PRECISE_OPEN = "taiwan_precise_open"
TASK_TYPE_DAILY_PREDICTION = "daily_prediction"
TASK_TYPE_POSTGRES_BACKUP = "postgres_backup"
SCHEDULE_SCOPE_AUTO = "auto"
SCHEDULE_SCOPE_MANUAL = "manual"
TASK_TYPE_MANUAL_JOB = "manual_job"
MAX_MANUAL_JOB_RESULT_BYTES = 16 * 1024
SCHEDULER_WORKER_LEASE_NAME = "crawler_scheduler"


def _task_poll_interval_seconds(db_path: str | Path) -> int:
    return max(5, int(_cfg(db_path, "crawler.task_poll_interval_seconds", 30)))


def _task_lock_timeout_seconds(db_path: str | Path) -> int:
    return max(30, int(_cfg(db_path, "crawler.task_lock_timeout_seconds", 300)))


def _task_retry_delay_seconds(db_path: str | Path) -> int:
    return max(5, int(_cfg(db_path, "crawler.task_retry_delay_seconds", 60)))


def _worker_lease_seconds(db_path: str | Path) -> int:
    return max(30, int(_cfg(db_path, "crawler.worker_lease_seconds", 90)))


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _safe_manual_job_result(result: dict[str, Any]) -> dict[str, Any]:
    """Persist only a bounded, recursively redacted manual-job summary."""
    safe_result = redact_value(dict(result))
    serialized = _json_dumps(safe_result)
    if len(serialized.encode("utf-8")) <= MAX_MANUAL_JOB_RESULT_BYTES:
        return safe_result
    bounded: dict[str, Any] = {}
    for key, value in safe_result.items():
        if len(_json_dumps({key: value}).encode("utf-8")) <= 4096:
            bounded[key] = value
    bounded["truncated"] = True
    return bounded


def _lease_deadline(now: datetime, lease_seconds: int) -> str:
    return (now + timedelta(seconds=max(1, int(lease_seconds)))).isoformat()


def try_acquire_scheduler_worker_lease(
    db_path: str | Path,
    *,
    holder_id: str,
    now: datetime | None = None,
    lease_seconds: int | None = None,
) -> bool:
    current = now or datetime.now(timezone.utc)
    duration = lease_seconds if lease_seconds is not None else _worker_lease_seconds(db_path)
    with db_connect(db_path) as conn:
        return repository.try_acquire_worker_lease(
            conn,
            lease_name=SCHEDULER_WORKER_LEASE_NAME,
            holder_id=holder_id,
            now_text=current.isoformat(),
            expires_at=_lease_deadline(current, duration),
        )


def renew_scheduler_worker_lease(
    db_path: str | Path,
    *,
    holder_id: str,
    now: datetime | None = None,
    lease_seconds: int | None = None,
) -> bool:
    current = now or datetime.now(timezone.utc)
    duration = lease_seconds if lease_seconds is not None else _worker_lease_seconds(db_path)
    with db_connect(db_path) as conn:
        return repository.renew_worker_lease(
            conn,
            lease_name=SCHEDULER_WORKER_LEASE_NAME,
            holder_id=holder_id,
            now_text=current.isoformat(),
            expires_at=_lease_deadline(current, duration),
        )


def release_scheduler_worker_lease(db_path: str | Path, *, holder_id: str) -> None:
    with db_connect(db_path) as conn:
        repository.release_worker_lease(
            conn,
            lease_name=SCHEDULER_WORKER_LEASE_NAME,
            holder_id=holder_id,
        )


def _task_key(task_type: str, payload: dict[str, Any]) -> str:
    if task_type == TASK_TYPE_AUTO_PREDICTION:
        return f"{task_type}:{payload.get('lottery_type_id')}"
    if task_type == TASK_TYPE_TAIWAN_PRECISE_OPEN:
        return f"{task_type}:{payload.get('schedule_date')}"
    if task_type == TASK_TYPE_DAILY_PREDICTION:
        return f"{task_type}:{payload.get('schedule_date')}"
    if task_type == TASK_TYPE_POSTGRES_BACKUP:
        return f"{task_type}:{payload.get('schedule_date')}:{payload.get('schedule_time')}"
    return f"{task_type}:{_json_dumps(payload)}"


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
    now = datetime.now(timezone.utc).isoformat()
    task_key_str = task_key_override or _task_key(task_type, payload)
    payload_json = _json_dumps(payload)
    with db_connect(db_path) as conn:
        existing = repository.find_task_by_key(conn, task_key_str)
        if existing:
            existing_status = str(existing["status"] or "pending")
            if existing_status in {"done", "running"} and not force_reschedule:
                repository.update_completed_or_running_task_metadata(
                    conn,
                    task_key=task_key_str,
                    task_type=task_type,
                    payload_json=payload_json,
                    max_attempts=max_attempts,
                    schedule_scope=schedule_scope,
                    updated_at=now,
                )
                return
            repository.reschedule_existing_task(
                conn,
                task_key=task_key_str,
                task_type=task_type,
                payload_json=payload_json,
                run_at=run_at,
                max_attempts=max_attempts,
                schedule_scope=schedule_scope,
                created_by=created_by,
                updated_at=now,
            )
            return

        repository.insert_task(
            conn,
            task_key=task_key_str,
            task_type=task_type,
            payload_json=payload_json,
            schedule_scope=schedule_scope,
            run_at=run_at,
            max_attempts=max_attempts,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )


def acquire_due_scheduler_tasks(db_path: str | Path, *, worker_id: str, limit: int = 10) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    stale_before = (now - timedelta(seconds=_task_lock_timeout_seconds(db_path))).isoformat()
    tasks: list[dict[str, Any]] = []
    with db_connect(db_path) as conn:
        rows = repository.find_due_tasks(
            conn,
            now_text=now_text,
            stale_before=stale_before,
            limit=limit,
        )
        for row in rows:
            if repository.try_acquire_task(
                conn,
                task_id=int(row["id"]),
                worker_id=worker_id,
                now_text=now_text,
                stale_before=stale_before,
            ):
                task = dict(row)
                task["attempt_count"] = int(row["attempt_count"] or 0) + 1
                task["locked_at"] = now_text
                task["locked_by"] = worker_id
                tasks.append(task)
    return tasks


def has_completed_daily_prediction_task(db_path: str | Path, schedule_date: str) -> bool:
    with db_connect(db_path) as conn:
        return bool(
            repository.find_completed_task_by_payload_date(
                conn,
                task_type=TASK_TYPE_DAILY_PREDICTION,
                schedule_date=schedule_date,
            )
        )


def create_scheduler_task_run(
    db_path: str | Path,
    *,
    task: dict[str, Any],
    worker_id: str,
) -> int | None:
    now_text = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        return repository.insert_task_run(
            conn,
            task_id=int(task["id"]),
            task_key=str(task.get("task_key") or ""),
            task_type=str(task.get("task_type") or ""),
            schedule_scope=str(task.get("schedule_scope") or SCHEDULE_SCOPE_AUTO),
            worker_id=worker_id,
            attempt_no=int(task.get("attempt_count") or 0),
            scheduled_run_at=str(task.get("run_at") or ""),
            acquired_at=str(task.get("locked_at") or now_text),
            started_at=now_text,
            payload_json=str(task.get("payload_json") or "{}"),
            created_at=now_text,
            updated_at=now_text,
        )


def finish_scheduler_task_run(
    db_path: str | Path,
    *,
    run_id: int | None,
    status: str,
    error_message: str | None = None,
) -> None:
    if run_id is None:
        return
    now_text = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        repository.finish_task_run(
            conn,
            run_id=run_id,
            status=status,
            error_message=error_message,
            finished_at=now_text,
            updated_at=now_text,
        )


def mark_scheduler_task_done(db_path: str | Path, task_id: int) -> None:
    now_text = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        repository.mark_task_done(
            conn,
            task_id=task_id,
            finished_at=now_text,
            updated_at=now_text,
        )


def mark_scheduler_task_failed(db_path: str | Path, task: dict[str, Any], exc: Exception) -> None:
    now = datetime.now(timezone.utc)
    now_text = now.isoformat()
    attempt_count = int(task.get("attempt_count") or 0)
    max_attempts = int(task.get("max_attempts") or 3)
    final_status = "failed" if attempt_count >= max_attempts else "pending"
    retry_at = (now + timedelta(seconds=_task_retry_delay_seconds(db_path))).isoformat()
    with db_connect(db_path) as conn:
        repository.mark_task_failed(
            conn,
            task_id=int(task["id"]),
            status=final_status,
            run_at=retry_at if final_status == "pending" else now_text,
            last_error=f"{type(exc).__name__}: {exc}",
            updated_at=now_text,
        )


def run_due_scheduler_tasks(
    db_path: str | Path,
    *,
    worker_id: str,
    execute_task: Callable[[dict[str, Any]], None],
    on_task_acquired: Callable[[dict[str, Any]], None] | None = None,
    on_task_failed: Callable[[dict[str, Any], Exception], None] | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Acquire due tasks and own their persisted run lifecycle."""
    tasks = acquire_due_scheduler_tasks(db_path, worker_id=worker_id, limit=limit)
    for task in tasks:
        run_id: int | None = None
        try:
            if on_task_acquired:
                on_task_acquired(task)
            run_id = create_scheduler_task_run(db_path, task=task, worker_id=worker_id)
            execute_task(task)
            finish_scheduler_task_run(db_path, run_id=run_id, status="done")
            if str(task.get("task_type") or "") != TASK_TYPE_MANUAL_JOB:
                mark_scheduler_task_done(db_path, int(task["id"]))
        except Exception as exc:
            finish_scheduler_task_run(
                db_path,
                run_id=run_id,
                status="failed",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            if str(task.get("task_type") or "") != TASK_TYPE_MANUAL_JOB:
                mark_scheduler_task_failed(db_path, task, exc)
            if on_task_failed:
                on_task_failed(task, exc)
    return tasks


def ensure_taiwan_precise_open_task(db_path: str | Path) -> None:
    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    from crawler.collectors import _get_taiwan_draw_time_parts

    hour, minute = _get_taiwan_draw_time_parts(db_path)
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
        schedule_scope=SCHEDULE_SCOPE_AUTO,
    )


def ensure_daily_prediction_task(
    db_path: str | Path,
    *,
    schedule_date: str | None = None,
    run_at: str | None = None,
    force_reschedule: bool = False,
) -> None:
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
    effective_schedule_date = schedule_date or target_beijing.strftime("%Y-%m-%d")
    effective_run_at = run_at or target_utc.isoformat()
    upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": effective_schedule_date},
        run_at=effective_run_at,
        max_attempts=3,
        schedule_scope=SCHEDULE_SCOPE_AUTO,
        force_reschedule=force_reschedule,
    )


def ensure_postgres_backup_tasks(
    db_path: str | Path,
    *,
    force_reschedule: bool = False,
) -> None:
    from crawler.postgres_backup import backup_enabled, configured_backup_times

    if not backup_enabled(db_path):
        return

    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    for schedule_time in configured_backup_times(db_path):
        hour, minute = [int(part) for part in schedule_time.split(":", 1)]
        target_beijing = beijing_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if beijing_now >= target_beijing:
            target_beijing += timedelta(days=1)
        target_utc = target_beijing - timedelta(hours=8)
        schedule_date = target_beijing.strftime("%Y-%m-%d")
        upsert_scheduler_task(
            db_path,
            task_type=TASK_TYPE_POSTGRES_BACKUP,
            payload={
                "schedule_date": schedule_date,
                "schedule_time": schedule_time,
            },
            run_at=target_utc.isoformat(),
            max_attempts=2,
            schedule_scope=SCHEDULE_SCOPE_AUTO,
            force_reschedule=force_reschedule,
        )


def enqueue_manual_daily_prediction_task(
    db_path: str | Path,
    *,
    lottery_type_ids: list[int] | None = None,
    created_by: str = "unknown",
) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    beijing_now = now_utc + timedelta(hours=8)
    schedule_date = beijing_now.strftime("%Y-%m-%d")
    run_at = now_utc.isoformat()
    task_key = f"{TASK_TYPE_DAILY_PREDICTION}:manual:{schedule_date}:{now_utc.strftime('%H%M%S%f')}"
    payload: dict[str, Any] = {
        "schedule_date": schedule_date,
        "trigger": "manual",
        "requested_at": run_at,
        "requested_by": created_by,
    }
    if lottery_type_ids:
        payload["lottery_type_ids"] = [int(item) for item in lottery_type_ids]
    upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_DAILY_PREDICTION,
        payload=payload,
        run_at=run_at,
        max_attempts=1,
        schedule_scope=SCHEDULE_SCOPE_MANUAL,
        force_reschedule=True,
        task_key_override=task_key,
        created_by=created_by,
    )
    return {"task_key": task_key, "run_at": run_at, "schedule_date": schedule_date}


def enqueue_manual_job(
    db_path: str | Path,
    *,
    job_type: str,
    payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    created_by: str = "unknown",
    job_id: str,
    run_at: str,
) -> str:
    """Persist a manually-requested job without retaining a callable in process memory."""
    task_payload = {
        "job_id": job_id,
        "job_type": str(job_type),
        "payload": dict(payload),
        "metadata": dict(metadata or {}),
        "result": None,
    }
    upsert_scheduler_task(
        db_path,
        task_type=TASK_TYPE_MANUAL_JOB,
        payload=task_payload,
        run_at=run_at,
        max_attempts=1,
        schedule_scope=SCHEDULE_SCOPE_MANUAL,
        force_reschedule=False,
        task_key_override=f"manual_job:{job_id}",
        created_by=created_by,
    )
    return job_id


def get_manual_job(db_path: str | Path, job_id: str) -> dict[str, Any] | None:
    with db_connect(db_path) as conn:
        row = repository.find_manual_job_by_id(conn, job_id)
    if not row:
        return None
    try:
        payload = json.loads(str(row.get("payload_json") or "{}"))
    except json.JSONDecodeError:
        payload = {}
    status = str(row.get("status") or "pending")
    return {
        "status": "error" if status == "failed" else status,
        "started_at": row.get("locked_at") or row.get("last_finished_at"),
        "result": payload.get("result"),
        "metadata": dict(payload.get("metadata") or {}),
        **({"error": str(row.get("last_error") or "")} if status == "failed" else {}),
    }


def complete_manual_job(db_path: str | Path, task: dict[str, Any], *, result: dict[str, Any]) -> None:
    """Store a safe job result and mark an acquired manual job done."""
    try:
        payload = json.loads(str(task.get("payload_json") or "{}"))
    except json.JSONDecodeError:
        payload = {}
    payload["result"] = _safe_manual_job_result(result)
    now_text = datetime.now(timezone.utc).isoformat()
    with db_connect(db_path) as conn:
        repository.update_manual_job_payload(
            conn,
            task_id=int(task["id"]),
            payload_json=_json_dumps(payload),
            updated_at=now_text,
        )
        repository.mark_manual_job_done(
            conn,
            task_id=int(task["id"]),
            started_at=str(task.get("locked_at") or now_text),
            finished_at=now_text,
            updated_at=now_text,
        )


def fail_manual_job(db_path: str | Path, task: dict[str, Any], exc: Exception) -> None:
    """Expose the persisted manual-job error without storing a traceback."""
    now_text = datetime.now(timezone.utc).isoformat()
    message = f"{type(exc).__name__}: {exc}"
    with db_connect(db_path) as conn:
        repository.mark_task_failed(
            conn,
            task_id=int(task["id"]),
            status="failed",
            run_at=now_text,
            last_error=message,
            updated_at=now_text,
        )
