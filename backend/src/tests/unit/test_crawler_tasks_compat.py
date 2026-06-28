from __future__ import annotations

from pathlib import Path


def test_crawler_tasks_reexports_scheduler_domain_service(monkeypatch):
    from crawler import tasks

    calls: list[tuple[str, tuple[object, ...]]] = []

    def fake_upsert(*args, **kwargs):
        calls.append(("upsert", args + (kwargs,)))

    def fake_acquire(*args, **kwargs):
        calls.append(("acquire", args + (kwargs,)))
        return [{"id": 1}]

    def fake_completed(*args, **kwargs):
        calls.append(("completed", args + (kwargs,)))
        return True

    def fake_run_due(*args, **kwargs):
        calls.append(("run_due", args + (kwargs,)))
        return [{"id": 2}]

    def fake_create_run(*args, **kwargs):
        calls.append(("create_run", args + (kwargs,)))
        return 99

    def fake_finish_run(*args, **kwargs):
        calls.append(("finish_run", args + (kwargs,)))

    def fake_mark_done(*args, **kwargs):
        calls.append(("done", args + (kwargs,)))

    monkeypatch.setattr("domains.scheduler.service.upsert_scheduler_task", fake_upsert)
    monkeypatch.setattr("domains.scheduler.service.acquire_due_scheduler_tasks", fake_acquire)
    monkeypatch.setattr("domains.scheduler.service.run_due_scheduler_tasks", fake_run_due)
    monkeypatch.setattr("domains.scheduler.service.has_completed_daily_prediction_task", fake_completed)
    monkeypatch.setattr("domains.scheduler.service.create_scheduler_task_run", fake_create_run)
    monkeypatch.setattr("domains.scheduler.service.finish_scheduler_task_run", fake_finish_run)
    monkeypatch.setattr("domains.scheduler.service.mark_scheduler_task_done", fake_mark_done)

    db_path = Path("scheduler-compat.sqlite3")
    execute_task = lambda task: None

    tasks.upsert_scheduler_task(
        db_path,
        task_type=tasks.TASK_TYPE_DAILY_PREDICTION,
        payload={"schedule_date": "2026-06-27"},
        run_at="2026-06-27T04:00:00+00:00",
    )
    assert tasks.acquire_due_scheduler_tasks(db_path, worker_id="worker-a") == [{"id": 1}]
    assert tasks.run_due_scheduler_tasks(
        db_path,
        worker_id="worker-a",
        execute_task=execute_task,
    ) == [{"id": 2}]
    assert tasks.has_completed_daily_prediction_task(db_path, "2026-06-27")
    assert tasks.create_scheduler_task_run(db_path, task={"id": 1}, worker_id="worker-a") == 99
    tasks.finish_scheduler_task_run(db_path, run_id=99, status="done")
    tasks.mark_scheduler_task_done(db_path, 1)

    assert calls == [
        (
            "upsert",
            (
                db_path,
                {
                    "task_type": "daily_prediction",
                    "payload": {"schedule_date": "2026-06-27"},
                    "run_at": "2026-06-27T04:00:00+00:00",
                    "max_attempts": 3,
                    "schedule_scope": "auto",
                    "force_reschedule": False,
                    "task_key_override": None,
                    "created_by": None,
                },
            ),
        ),
        ("acquire", (db_path, {"worker_id": "worker-a", "limit": 10})),
        (
            "run_due",
            (
                db_path,
                {
                    "worker_id": "worker-a",
                    "execute_task": execute_task,
                    "on_task_acquired": None,
                    "on_task_failed": None,
                    "limit": 10,
                },
            ),
        ),
        ("completed", (db_path, "2026-06-27", {})),
        ("create_run", (db_path, {"task": {"id": 1}, "worker_id": "worker-a"})),
        ("finish_run", (db_path, {"run_id": 99, "status": "done", "error_message": None})),
        ("done", (db_path, 1, {})),
    ]
