"""Repository helpers for persisted scheduler tasks."""

from __future__ import annotations

from typing import Any

TASK_TABLE_NAME = "scheduler_tasks"
TASK_RUN_TABLE_NAME = "scheduler_task_runs"
WORKER_LEASE_TABLE_NAME = "scheduler_worker_leases"


def find_task_by_key(conn: Any, task_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"""
        SELECT id, status, attempt_count
        FROM {TASK_TABLE_NAME}
        WHERE task_key = ?
        LIMIT 1
        """,
        (task_key,),
    ).fetchone()
    return dict(row) if row else None


def update_completed_or_running_task_metadata(
    conn: Any,
    *,
    task_key: str,
    task_type: str,
    payload_json: str,
    max_attempts: int,
    schedule_scope: str,
    updated_at: str,
) -> None:
    conn.execute(
        f"""
        UPDATE {TASK_TABLE_NAME}
        SET task_type = ?, payload_json = ?, max_attempts = ?,
            schedule_scope = ?, updated_at = ?
        WHERE task_key = ?
        """,
        (task_type, payload_json, max_attempts, schedule_scope, updated_at, task_key),
    )


def reschedule_existing_task(
    conn: Any,
    *,
    task_key: str,
    task_type: str,
    payload_json: str,
    run_at: str,
    max_attempts: int,
    schedule_scope: str,
    created_by: str | None,
    updated_at: str,
) -> None:
    conn.execute(
        f"""
        UPDATE {TASK_TABLE_NAME}
        SET task_type = ?, payload_json = ?, status = 'pending', run_at = ?,
            locked_at = NULL, locked_by = NULL, last_error = NULL,
            max_attempts = ?, attempt_count = 0, schedule_scope = ?,
            created_by = COALESCE(?, created_by), updated_at = ?
        WHERE task_key = ?
        """,
        (
            task_type,
            payload_json,
            run_at,
            max_attempts,
            schedule_scope,
            created_by,
            updated_at,
            task_key,
        ),
    )


def insert_task(
    conn: Any,
    *,
    task_key: str,
    task_type: str,
    payload_json: str,
    schedule_scope: str,
    run_at: str,
    max_attempts: int,
    created_by: str | None,
    created_at: str,
    updated_at: str,
) -> None:
    conn.execute(
        f"""
        INSERT INTO {TASK_TABLE_NAME} (
            task_key, task_type, payload_json, schedule_scope, status, run_at,
            attempt_count, max_attempts, created_by, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 'pending', ?, 0, ?, ?, ?, ?)
        """,
        (
            task_key,
            task_type,
            payload_json,
            schedule_scope,
            run_at,
            max_attempts,
            created_by,
            created_at,
            updated_at,
        ),
    )


def find_due_tasks(
    conn: Any,
    *,
    now_text: str,
    stale_before: str,
    limit: int,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT id, task_key, task_type, payload_json, schedule_scope, run_at, attempt_count, max_attempts
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
    return [dict(row) for row in rows]


def find_completed_task_by_payload_date(
    conn: Any,
    *,
    task_type: str,
    schedule_date: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        f"""
        SELECT id, task_key, run_at
        FROM {TASK_TABLE_NAME}
        WHERE task_type = ?
          AND status = 'done'
          AND payload_json LIKE ?
        ORDER BY run_at DESC
        LIMIT 1
        """,
        (task_type, f"%{schedule_date}%"),
    ).fetchone()
    return dict(row) if row else None


def try_acquire_task(
    conn: Any,
    *,
    task_id: int,
    worker_id: str,
    now_text: str,
    stale_before: str,
) -> bool:
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
        (now_text, worker_id, now_text, task_id, stale_before),
    )
    return bool(updated.rowcount)


def insert_task_run(
    conn: Any,
    *,
    task_id: int,
    task_key: str,
    task_type: str,
    schedule_scope: str,
    worker_id: str,
    attempt_no: int,
    scheduled_run_at: str,
    acquired_at: str,
    started_at: str,
    payload_json: str,
    created_at: str,
    updated_at: str,
) -> int | None:
    row = conn.execute(
        f"""
        INSERT INTO {TASK_RUN_TABLE_NAME} (
            task_id, task_key, task_type, schedule_scope, worker_id,
            attempt_no, scheduled_run_at, acquired_at, started_at,
            status, error_message, payload_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', NULL, ?, ?, ?)
        RETURNING id
        """,
        (
            task_id,
            task_key,
            task_type,
            schedule_scope,
            worker_id,
            attempt_no,
            scheduled_run_at,
            acquired_at,
            started_at,
            payload_json,
            created_at,
            updated_at,
        ),
    ).fetchone()
    return int(row["id"]) if row else None


def finish_task_run(
    conn: Any,
    *,
    run_id: int,
    status: str,
    error_message: str | None,
    finished_at: str,
    updated_at: str,
) -> None:
    conn.execute(
        f"""
        UPDATE {TASK_RUN_TABLE_NAME}
        SET status = ?, error_message = ?, finished_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, error_message, finished_at, updated_at, run_id),
    )


def mark_task_done(conn: Any, *, task_id: int, finished_at: str, updated_at: str) -> None:
    conn.execute(
        f"""
        UPDATE {TASK_TABLE_NAME}
        SET status = 'done', locked_at = NULL, locked_by = NULL,
            last_error = NULL, last_finished_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (finished_at, updated_at, task_id),
    )


def mark_manual_job_done(
    conn: Any,
    *,
    task_id: int,
    started_at: str,
    finished_at: str,
    updated_at: str,
) -> None:
    conn.execute(
        f"""
        UPDATE {TASK_TABLE_NAME}
        SET status = 'done', locked_at = ?, locked_by = NULL,
            last_error = NULL, last_finished_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (started_at, finished_at, updated_at, task_id),
    )


def mark_task_failed(
    conn: Any,
    *,
    task_id: int,
    status: str,
    run_at: str,
    last_error: str,
    updated_at: str,
) -> None:
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
        (status, run_at, last_error, updated_at, task_id),
    )


def find_manual_job_by_id(conn: Any, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        f"""
        SELECT task_key, status, payload_json, locked_at, last_finished_at, last_error
        FROM {TASK_TABLE_NAME}
        WHERE task_key = ?
        LIMIT 1
        """,
        (f"manual_job:{job_id}",),
    ).fetchone()
    return dict(row) if row else None


def update_manual_job_payload(
    conn: Any,
    *,
    task_id: int,
    payload_json: str,
    updated_at: str,
) -> None:
    conn.execute(
        f"UPDATE {TASK_TABLE_NAME} SET payload_json = ?, updated_at = ? WHERE id = ?",
        (payload_json, updated_at, task_id),
    )


def try_acquire_worker_lease(
    conn: Any,
    *,
    lease_name: str,
    holder_id: str,
    now_text: str,
    expires_at: str,
) -> bool:
    """Atomically acquire an expired lease or renew one held by this worker."""
    row = conn.execute(
        f"""
        INSERT INTO {WORKER_LEASE_TABLE_NAME} (
            lease_name, holder_id, lease_expires_at, updated_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(lease_name) DO UPDATE SET
            holder_id = excluded.holder_id,
            lease_expires_at = excluded.lease_expires_at,
            updated_at = excluded.updated_at
        WHERE {WORKER_LEASE_TABLE_NAME}.lease_expires_at <= ?
           OR {WORKER_LEASE_TABLE_NAME}.holder_id = ?
        RETURNING holder_id
        """,
        (lease_name, holder_id, expires_at, now_text, now_text, holder_id),
    ).fetchone()
    return bool(row and str(row["holder_id"] or "") == holder_id)


def renew_worker_lease(
    conn: Any,
    *,
    lease_name: str,
    holder_id: str,
    now_text: str,
    expires_at: str,
) -> bool:
    updated = conn.execute(
        f"""
        UPDATE {WORKER_LEASE_TABLE_NAME}
        SET lease_expires_at = ?, updated_at = ?
        WHERE lease_name = ?
          AND holder_id = ?
          AND lease_expires_at > ?
        """,
        (expires_at, now_text, lease_name, holder_id, now_text),
    )
    return bool(updated.rowcount)


def release_worker_lease(conn: Any, *, lease_name: str, holder_id: str) -> None:
    conn.execute(
        f"DELETE FROM {WORKER_LEASE_TABLE_NAME} WHERE lease_name = ? AND holder_id = ?",
        (lease_name, holder_id),
    )
