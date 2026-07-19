from __future__ import annotations

from datetime import datetime, timezone

from domains.scheduler import service
from tables import ensure_admin_tables


def test_manual_job_enqueue_is_restart_safe_and_returns_existing_job_shape(tmp_path):
    db_path = str(tmp_path / "durable-jobs.sqlite3")
    ensure_admin_tables(db_path)

    job_id = service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 1},
        metadata={"lottery_type_id": 1, "task_type": "crawl_and_generate"},
        created_by="admin",
        job_id="job-crawl-1",
        run_at=datetime.now(timezone.utc).isoformat(),
    )

    assert service.get_manual_job(db_path, job_id) == {
        "status": "pending",
        "started_at": None,
        "result": None,
        "metadata": {"lottery_type_id": 1, "task_type": "crawl_and_generate"},
    }


def test_manual_job_enqueue_is_idempotent_for_the_same_job_id(tmp_path):
    db_path = str(tmp_path / "durable-jobs-idempotent.sqlite3")
    ensure_admin_tables(db_path)
    run_at = datetime.now(timezone.utc).isoformat()

    first = service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 2},
        metadata={"lottery_type_id": 2},
        job_id="job-crawl-2",
        run_at=run_at,
    )
    second = service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 2},
        metadata={"lottery_type_id": 2},
        job_id="job-crawl-2",
        run_at=run_at,
    )

    assert first == second == "job-crawl-2"


def test_manual_job_worker_acquires_and_finishes_persisted_job(tmp_path):
    db_path = str(tmp_path / "durable-jobs-worker.sqlite3")
    ensure_admin_tables(db_path)
    service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 3},
        metadata={"lottery_type_id": 3},
        job_id="job-crawl-3",
        run_at="2000-01-01T00:00:00+00:00",
    )

    acquired = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=1)
    assert [task["task_key"] for task in acquired] == ["manual_job:job-crawl-3"]

    service.complete_manual_job(db_path, acquired[0], result={"ok": True, "items": 3})

    assert service.get_manual_job(db_path, "job-crawl-3") == {
        "status": "done",
        "started_at": acquired[0]["locked_at"],
        "result": {"ok": True, "items": 3},
        "metadata": {"lottery_type_id": 3},
    }


def test_manual_job_failure_uses_existing_error_job_shape(tmp_path):
    db_path = str(tmp_path / "durable-jobs-failure.sqlite3")
    ensure_admin_tables(db_path)
    service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 1},
        metadata={"lottery_type_id": 1},
        job_id="job-crawl-failure",
        run_at="2000-01-01T00:00:00+00:00",
    )
    task = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=1)[0]

    service.fail_manual_job(db_path, task, RuntimeError("upstream unavailable"))

    job = service.get_manual_job(db_path, "job-crawl-failure")
    assert job is not None
    assert job["status"] == "error"
    assert job["result"] is None
    assert job["metadata"] == {"lottery_type_id": 1}
    assert job["error"] == "RuntimeError: upstream unavailable"


def test_run_due_tasks_does_not_overwrite_manual_job_result(tmp_path):
    db_path = str(tmp_path / "durable-jobs-lifecycle.sqlite3")
    ensure_admin_tables(db_path)
    service.enqueue_manual_job(
        db_path,
        job_type="crawl_and_generate",
        payload={"lottery_type_id": 1},
        metadata={"lottery_type_id": 1},
        job_id="job-crawl-lifecycle",
        run_at="2000-01-01T00:00:00+00:00",
    )

    def execute(task):
        service.complete_manual_job(db_path, task, result={"ok": True})

    service.run_due_scheduler_tasks(db_path, worker_id="worker-a", execute_task=execute, limit=1)

    job = service.get_manual_job(db_path, "job-crawl-lifecycle")
    assert job is not None
    assert job["status"] == "done"
    assert job["started_at"]
    assert job["result"] == {"ok": True}
    assert job["metadata"] == {"lottery_type_id": 1}


def test_manual_job_result_is_bounded_and_redacts_future_truth_fields(tmp_path):
    db_path = str(tmp_path / "durable-jobs-result-redaction.sqlite3")
    ensure_admin_tables(db_path)
    service.enqueue_manual_job(
        db_path,
        job_type="site_prediction_generate_all",
        payload={"site_id": 3},
        metadata={"site_id": 3},
        job_id="job-safe-result",
        run_at="2000-01-01T00:00:00+00:00",
    )
    task = service.acquire_due_scheduler_tasks(db_path, worker_id="worker-a", limit=1)[0]

    service.complete_manual_job(
        db_path,
        task,
        result={
            "inserted": 1,
            "numbers": "01,02,03,04,05,06,07",
            "nested": {"res_code": "01,02,03,04,05,06,07"},
            "details": "x" * 20000,
        },
    )

    job = service.get_manual_job(db_path, "job-safe-result")
    assert job is not None
    assert job["result"]["numbers"] == "***REDACTED***"
    assert job["result"]["nested"]["res_code"] == "***REDACTED***"
    assert job["result"]["truncated"] is True
    assert "details" not in job["result"]
