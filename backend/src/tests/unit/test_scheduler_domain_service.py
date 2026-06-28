from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db import connect
from tables import ensure_admin_tables


def test_scheduler_service_upserts_and_acquires_due_tasks_with_lock(tmp_path, monkeypatch):
    from domains.scheduler import service

    db_path = tmp_path / "scheduler.sqlite3"
    ensure_admin_tables(db_path)

    monkeypatch.setattr(service, "_task_lock_timeout_seconds", lambda _db_path: 300)

    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    service.upsert_scheduler_task(
        db_path,
        task_type=service.TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": "2026-06-27"},
        run_at=past,
        max_attempts=3,
    )

    acquired = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=10)

    assert len(acquired) == 1
    assert acquired[0]["task_key"] == "daily_prediction:2026-06-27"
    assert acquired[0]["task_type"] == service.TASK_TYPE_DAILY_PREDICTION
    assert acquired[0]["attempt_count"] == 1
    assert acquired[0]["locked_by"] == "worker-a"

    assert service.acquire_due_scheduler_tasks(db_path, worker_id="worker-b", limit=10) == []

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, attempt_count, locked_by FROM scheduler_tasks WHERE task_key = ?",
            ("daily_prediction:2026-06-27",),
        ).fetchone()

    assert dict(row) == {
        "status": "running",
        "attempt_count": 1,
        "locked_by": "worker-a",
    }


def test_scheduler_service_records_runs_and_finishes_task(tmp_path):
    from domains.scheduler import service

    db_path = tmp_path / "scheduler_runs.sqlite3"
    ensure_admin_tables(db_path)

    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    service.upsert_scheduler_task(
        db_path,
        task_type=service.TASK_TYPE_POSTGRES_BACKUP,
        payload={"schedule_date": "2026-06-27", "schedule_time": "03:00"},
        run_at=past,
        max_attempts=2,
    )
    task = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=1)[0]

    run_id = service.create_scheduler_task_run(db_path, task=task, worker_id="worker-a")
    service.finish_scheduler_task_run(db_path, run_id=run_id, status="done")
    service.mark_scheduler_task_done(db_path, int(task["id"]))

    with connect(db_path) as conn:
        task_row = conn.execute(
            "SELECT status, locked_at, locked_by, last_error, last_finished_at FROM scheduler_tasks WHERE id = ?",
            (task["id"],),
        ).fetchone()
        run_row = conn.execute(
            "SELECT status, task_key, worker_id, finished_at FROM scheduler_task_runs WHERE id = ?",
            (run_id,),
        ).fetchone()

    assert task_row["status"] == "done"
    assert task_row["locked_at"] is None
    assert task_row["locked_by"] is None
    assert task_row["last_error"] is None
    assert task_row["last_finished_at"]
    assert run_row["status"] == "done"
    assert run_row["task_key"] == "postgres_backup:2026-06-27:03:00"
    assert run_row["worker_id"] == "worker-a"
    assert run_row["finished_at"]


def test_scheduler_service_failed_task_retries_until_max_attempts(tmp_path, monkeypatch):
    from domains.scheduler import service

    db_path = tmp_path / "scheduler_failed.sqlite3"
    ensure_admin_tables(db_path)

    monkeypatch.setattr(service, "_task_retry_delay_seconds", lambda _db_path: 5)

    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    service.upsert_scheduler_task(
        db_path,
        task_type="custom",
        payload={"value": 1},
        run_at=past,
        max_attempts=2,
    )

    first = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=1)[0]
    service.mark_scheduler_task_failed(db_path, first, RuntimeError("boom"))

    with connect(db_path) as conn:
        retry_row = conn.execute(
            "SELECT status, locked_at, locked_by, attempt_count, last_error FROM scheduler_tasks WHERE id = ?",
            (first["id"],),
        ).fetchone()

    assert retry_row["status"] == "pending"
    assert retry_row["locked_at"] is None
    assert retry_row["locked_by"] is None
    assert retry_row["attempt_count"] == 1
    assert "RuntimeError: boom" in retry_row["last_error"]

    with connect(db_path) as conn:
        conn.execute(
            "UPDATE scheduler_tasks SET run_at = ? WHERE id = ?",
            (past, first["id"]),
        )

    second = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-b", limit=1)[0]
    service.mark_scheduler_task_failed(db_path, second, ValueError("again"))

    with connect(db_path) as conn:
        failed_row = conn.execute(
            "SELECT status, locked_at, locked_by, attempt_count, last_error FROM scheduler_tasks WHERE id = ?",
            (first["id"],),
        ).fetchone()

    assert failed_row["status"] == "failed"
    assert failed_row["locked_at"] is None
    assert failed_row["locked_by"] is None
    assert failed_row["attempt_count"] == 2
    assert "ValueError: again" in failed_row["last_error"]


def test_scheduler_service_detects_completed_daily_prediction_for_schedule_date(tmp_path):
    from domains.scheduler import service

    db_path = tmp_path / "scheduler_completed_daily.sqlite3"
    ensure_admin_tables(db_path)

    service.upsert_scheduler_task(
        db_path,
        task_type=service.TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": "2026-06-27"},
        run_at="2026-06-27T04:00:00+00:00",
    )

    assert not service.has_completed_daily_prediction_task(db_path, "2026-06-27")

    with connect(db_path) as conn:
        conn.execute(
            "UPDATE scheduler_tasks SET status = 'done' WHERE task_key = ?",
            ("daily_prediction:2026-06-27",),
        )

    assert service.has_completed_daily_prediction_task(db_path, "2026-06-27")
    assert not service.has_completed_daily_prediction_task(db_path, "2026-06-28")


def test_scheduler_service_runs_due_tasks_and_owns_lifecycle(tmp_path, monkeypatch):
    from domains.scheduler import service

    db_path = tmp_path / "scheduler_lifecycle.sqlite3"
    ensure_admin_tables(db_path)

    monkeypatch.setattr(service, "_task_retry_delay_seconds", lambda _db_path: 5)

    past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    service.upsert_scheduler_task(
        db_path,
        task_type="custom_success",
        payload={"value": "ok"},
        run_at=past,
        max_attempts=1,
    )
    service.upsert_scheduler_task(
        db_path,
        task_type="custom_failure",
        payload={"value": "boom"},
        run_at=past,
        max_attempts=1,
    )

    executed: list[str] = []
    failures: list[tuple[str, str]] = []

    def execute_task(task):
        executed.append(task["task_type"])
        if task["task_type"] == "custom_failure":
            raise RuntimeError("boom")

    service.run_due_scheduler_tasks(
        db_path,
        worker_id="worker-a",
        execute_task=execute_task,
        on_task_failed=lambda task, exc: failures.append((task["task_type"], str(exc))),
        limit=10,
    )

    assert executed == ["custom_success", "custom_failure"]
    assert failures == [("custom_failure", "boom")]

    with connect(db_path) as conn:
        task_rows = {
            row["task_type"]: dict(row)
            for row in conn.execute(
                "SELECT task_type, status, locked_at, locked_by, last_error "
                "FROM scheduler_tasks ORDER BY id"
            ).fetchall()
        }
        run_rows = [
            dict(row)
            for row in conn.execute(
                "SELECT task_type, status, error_message FROM scheduler_task_runs ORDER BY id"
            ).fetchall()
        ]

    assert task_rows["custom_success"]["status"] == "done"
    assert task_rows["custom_success"]["locked_at"] is None
    assert task_rows["custom_success"]["locked_by"] is None
    assert task_rows["custom_success"]["last_error"] is None

    assert task_rows["custom_failure"]["status"] == "failed"
    assert task_rows["custom_failure"]["locked_at"] is None
    assert task_rows["custom_failure"]["locked_by"] is None
    assert "RuntimeError: boom" in task_rows["custom_failure"]["last_error"]

    assert run_rows == [
        {"task_type": "custom_success", "status": "done", "error_message": None},
        {"task_type": "custom_failure", "status": "failed", "error_message": "RuntimeError: boom"},
    ]
