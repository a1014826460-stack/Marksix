from __future__ import annotations

from crawler import scheduler


def test_run_due_tasks_delegates_lifecycle_to_scheduler_domain(monkeypatch):
    calls: list[tuple[str, object]] = []
    task = {
        "id": 7,
        "task_key": "daily_prediction:2026-06-27",
        "task_type": scheduler.TASK_TYPE_DAILY_PREDICTION,
        "payload_json": "{}",
        "run_at": "2026-06-27T04:00:00+00:00",
        "attempt_count": 1,
        "max_attempts": 3,
    }

    def fake_run_due(db_path, *, worker_id, execute_task, on_task_acquired, on_task_failed, limit):
        calls.append(("run_due", (db_path, worker_id, limit)))
        on_task_acquired(task)
        execute_task(task)
        return [task]

    monkeypatch.setattr(scheduler, "_run_due_scheduler_tasks", fake_run_due)
    monkeypatch.setattr(
        scheduler.CrawlerScheduler,
        "_execute_task",
        lambda self, acquired_task: calls.append(("execute", acquired_task["id"])),
    )

    runner = scheduler.CrawlerScheduler("scheduler-task-loop.sqlite3")
    runner._run_due_tasks()

    assert calls == [
        ("run_due", ("scheduler-task-loop.sqlite3", runner._worker_id, 10)),
        ("execute", 7),
    ]


def test_run_due_tasks_keeps_postgres_backup_failure_alert_callback(monkeypatch):
    calls: list[tuple[str, object]] = []
    task = {
        "id": 8,
        "task_key": "postgres_backup:2026-06-28:03:00",
        "task_type": scheduler.TASK_TYPE_POSTGRES_BACKUP,
        "payload_json": "{}",
        "run_at": "2026-06-28T04:00:00+00:00",
        "attempt_count": 2,
        "max_attempts": 2,
    }

    def fake_send_backup_failure_alert(db_path, *, error_message, attempt_no, final):
        calls.append(("backup_alert", (db_path, error_message, attempt_no, final)))

    monkeypatch.setattr(
        "crawler.postgres_backup.send_backup_failure_alert",
        fake_send_backup_failure_alert,
    )

    def fake_run_due(db_path, *, worker_id, execute_task, on_task_acquired, on_task_failed, limit):
        on_task_failed(task, RuntimeError("boom"))
        return [task]

    monkeypatch.setattr(scheduler, "_run_due_scheduler_tasks", fake_run_due)

    runner = scheduler.CrawlerScheduler("scheduler-task-loop.sqlite3")
    runner._run_due_tasks()

    assert calls == [
        ("backup_alert", ("scheduler-task-loop.sqlite3", "boom", 2, True)),
    ]
