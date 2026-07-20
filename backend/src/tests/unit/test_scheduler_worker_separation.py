from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone


def test_http_server_does_not_start_scheduler_timers():
    from app_http.server import run_server

    source = inspect.getsource(run_server)
    assert "CrawlerScheduler" not in source
    assert ".start()" not in source


def test_dedicated_scheduler_worker_owns_scheduler_startup():
    import scheduler_worker

    source = inspect.getsource(scheduler_worker.main)
    assert "CrawlerScheduler" in source
    assert "scheduler.start()" in source
    assert "scheduler.stop()" in source
    assert "scheduler.run_due_tasks_once()" not in source


def test_local_restart_script_manages_exactly_one_scheduler_worker_console():
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts" / "restart-backend.ps1"
    source = script.read_text(encoding="utf-8")

    assert "LIUHECAI_SCHEDULER_WORKER_CONSOLE" in source
    assert "scheduler_worker.py" in source
    assert "Stop-SchedulerWorkerProcesses" in source
    assert "Test-SchedulerWorkerHealthy" in source


def test_local_restart_script_checks_postgres_before_stopping_healthy_processes():
    from pathlib import Path

    script = Path(__file__).resolve().parents[3] / "scripts" / "restart-backend.ps1"
    source = script.read_text(encoding="utf-8")

    assert "function Test-DatabaseReachable" in source
    assert "Test-NetConnection" in source
    assert source.rindex("Test-DatabaseReachable") < source.rindex("Stop-ManagedConsoleProcesses")


def test_dedicated_worker_cleans_up_a_partially_started_scheduler(monkeypatch):
    import scheduler_worker

    scheduler = __import__("unittest.mock").mock.MagicMock()
    scheduler.start.side_effect = RuntimeError("startup failed")
    monkeypatch.setattr(scheduler_worker, "CrawlerScheduler", lambda _db_path: scheduler)
    monkeypatch.setattr(scheduler_worker, "ensure_prediction_configs_loaded", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "ensure_admin_tables", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "init_logging", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "log_startup_risk_warnings", lambda: None)
    monkeypatch.setattr(scheduler_worker, "detect_database_engine", lambda _db_path: "postgres")
    monkeypatch.setattr(scheduler_worker, "try_acquire_scheduler_worker_lease", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(scheduler_worker, "release_scheduler_worker_lease", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler_worker, "_worker_lease_seconds", lambda _db_path: 30)
    monkeypatch.setattr(scheduler_worker, "build_parser", lambda: type("P", (), {"parse_args": lambda _self: type("A", (), {"db_path": "postgresql://test"})()})())

    try:
        scheduler_worker.main()
    except RuntimeError as error:
        assert str(error) == "startup failed"

    scheduler.stop.assert_called_once_with()


def test_worker_does_not_schedule_duplicate_taiwan_durable_open_task():
    import scheduler_worker

    source = inspect.getsource(scheduler_worker)
    assert "ensure_taiwan_precise_open_task" not in source
    assert "ensure_daily_prediction_task" not in source
    assert "ensure_postgres_backup_tasks" not in source


def test_scheduler_uses_taiwan_durable_task_instead_of_a_precise_timer():
    from crawler import scheduler

    source = inspect.getsource(scheduler.CrawlerScheduler._reschedule_precise_checks_once)
    assert "for lt_id in [1, 2]:" in source
    assert "taiwan_precise_open" in source


def test_rescheduling_precise_checks_does_not_run_taiwan_open_from_an_in_memory_timer(monkeypatch):
    from crawler import scheduler

    runner = scheduler.CrawlerScheduler("postgresql://scheduler-test")
    runner._running = True
    monkeypatch.setattr(scheduler, "_cfg", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(scheduler, "_compute_hk_macau_default_next_time_ms", lambda *_args, **_kwargs: "")

    def taiwan_open_must_not_run():
        raise AssertionError("Taiwan open must use the durable taiwan_precise_open task")

    monkeypatch.setattr(runner, "_open_taiwan_draws_and_update_next_time", taiwan_open_must_not_run)

    runner._reschedule_precise_checks_once()

    assert 3 not in runner._precise_timers


def test_scheduler_start_enqueues_taiwan_durable_open_task(monkeypatch):
    from crawler import scheduler

    enqueued: list[str] = []
    monkeypatch.setattr(scheduler, "sync_all_lottery_type_next_times", lambda *_args, **_kwargs: {"checked": 0, "updated": 0})
    monkeypatch.setattr(scheduler, "_ensure_daily_prediction_task", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_ensure_postgres_backup_tasks", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler, "_ensure_taiwan_precise_open_task", lambda db_path: enqueued.append(db_path))
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_schedule_auto_open", lambda _self: None)
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_schedule_auto_crawl", lambda _self: None)
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_schedule_task_loop", lambda _self: None)
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_run_daily_prediction_if_missed", lambda _self: None)
    monkeypatch.setattr(scheduler.CrawlerScheduler, "_reschedule_precise_checks", lambda _self: None)

    runner = scheduler.CrawlerScheduler("postgresql://scheduler-test")
    runner.start()

    assert enqueued == ["postgresql://scheduler-test"]


def test_worker_leader_lease_allows_one_holder_and_takeover_after_expiry(tmp_path):
    from domains.scheduler import service
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "scheduler-worker-lease.sqlite3")
    ensure_admin_tables(db_path)
    now = datetime.now(timezone.utc)

    assert service.try_acquire_scheduler_worker_lease(
        db_path,
        holder_id="worker-a",
        now=now,
        lease_seconds=30,
    ) is True
    assert service.try_acquire_scheduler_worker_lease(
        db_path,
        holder_id="worker-b",
        now=now + timedelta(seconds=1),
        lease_seconds=30,
    ) is False
    assert service.try_acquire_scheduler_worker_lease(
        db_path,
        holder_id="worker-b",
        now=now + timedelta(seconds=31),
        lease_seconds=30,
    ) is True


def test_scheduler_worker_health_reports_missing_active_and_expired_leases(tmp_path):
    from domains.scheduler import service
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "scheduler-worker-health.sqlite3")
    ensure_admin_tables(db_path)
    now = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)

    assert service.get_scheduler_worker_health(db_path, now=now) == {
        "status": "missing",
        "active": False,
        "holder_id": "",
    }

    assert service.try_acquire_scheduler_worker_lease(
        db_path,
        holder_id="worker-a",
        now=now,
        lease_seconds=30,
    ) is True
    assert service.get_scheduler_worker_health(db_path, now=now + timedelta(seconds=1)) == {
        "status": "healthy",
        "active": True,
        "holder_id": "worker-a",
    }
    assert service.get_scheduler_worker_health(db_path, now=now + timedelta(seconds=31)) == {
        "status": "expired",
        "active": False,
        "holder_id": "worker-a",
    }


def test_scheduler_worker_stops_timers_when_leader_lease_renewal_fails(monkeypatch):
    import scheduler_worker

    scheduler = __import__("unittest.mock").mock.MagicMock()
    monkeypatch.setattr(scheduler_worker, "CrawlerScheduler", lambda _db_path: scheduler)
    monkeypatch.setattr(scheduler_worker, "ensure_prediction_configs_loaded", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "ensure_admin_tables", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "init_logging", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "log_startup_risk_warnings", lambda: None)
    monkeypatch.setattr(scheduler_worker, "detect_database_engine", lambda _db_path: "postgres")
    monkeypatch.setattr(scheduler_worker, "try_acquire_scheduler_worker_lease", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(scheduler_worker, "renew_scheduler_worker_lease", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(scheduler_worker, "release_scheduler_worker_lease", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(scheduler_worker, "_task_poll_interval_seconds", lambda _db_path: 0)
    monkeypatch.setattr(scheduler_worker, "_worker_lease_seconds", lambda _db_path: 30)
    monkeypatch.setattr(scheduler_worker, "build_parser", lambda: type("P", (), {"parse_args": lambda _self: type("A", (), {"db_path": "postgresql://test"})()})())

    monkeypatch.setattr(scheduler_worker.time, "sleep", lambda _seconds: None)

    assert scheduler_worker.main() == 0

    scheduler.start.assert_called_once_with()
    scheduler.stop.assert_called_once_with()


def test_durable_scheduler_service_preserves_manual_job_completion():
    from domains.scheduler import service

    source = inspect.getsource(service.run_due_scheduler_tasks)
    assert "TASK_TYPE_MANUAL_JOB" in source
    assert "mark_scheduler_task_done" in source
