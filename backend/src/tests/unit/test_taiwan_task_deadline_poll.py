"""The durable Taiwan opener must not inherit the coarse task-loop phase."""

from datetime import datetime, timedelta, timezone

import pytest

DEADLINE = datetime(2026, 10, 8, 14, 32, tzinfo=timezone.utc)


@pytest.fixture
def deadline_loop(tmp_path, monkeypatch):
    from database.bootstrap import ensure_admin_tables
    from crawler import scheduler
    from domains.scheduler import service

    db_path = tmp_path / "taiwan-deadline.sqlite3"
    ensure_admin_tables(db_path)
    state = {"now": DEADLINE - timedelta(seconds=7.25), "timers": [], "executed": []}

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = state["now"]
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    class Timer:
        def __init__(self, interval, callback):
            self.interval = interval
            self.callback = callback
            self.daemon = False
            state["timers"].append(self)

        def start(self):
            pass

        def cancel(self):
            pass

    monkeypatch.setattr(scheduler, "datetime", Clock)
    monkeypatch.setattr(service, "datetime", Clock)
    monkeypatch.setattr(scheduler.threading, "Timer", Timer)
    monkeypatch.setattr(scheduler, "_task_poll_interval_seconds", lambda _path: 30)
    monkeypatch.setattr(scheduler, "_ensure_taiwan_future_autofill_task", lambda _path: None)
    worker = scheduler.CrawlerScheduler(db_path)
    worker._running = True
    monkeypatch.setattr(worker, "_execute_task", lambda task: state["executed"].append(task))
    service.upsert_scheduler_task(
        db_path,
        task_type=service.TASK_TYPE_TAIWAN_PRECISE_OPEN,
        payload={"schedule_date": "2026-10-08"},
        run_at=DEADLINE.isoformat(),
    )
    return worker, state, db_path


@pytest.mark.parametrize("remaining", [29.9, 7.25, 0.75, 0.0001])
def test_restart_before_taiwan_deadline_does_not_wait_past_it(deadline_loop, remaining):
    worker, state, _db_path = deadline_loop
    state["now"] = DEADLINE - timedelta(seconds=remaining)
    worker._schedule_task_loop()

    assert state["executed"] == []
    assert state["timers"][-1].interval == pytest.approx(remaining)
    state["now"] += timedelta(seconds=state["timers"][-1].interval)
    state["timers"][-1].callback()
    assert len(state["executed"]) == 1
    assert state["now"] == DEADLINE
    assert state["timers"][-1].interval == 30


@pytest.mark.parametrize("keep_completed_yesterday", [False, True])
def test_startup_creates_missing_taiwan_task_before_arming_its_first_timer(
    deadline_loop, monkeypatch, keep_completed_yesterday
):
    from crawler import collectors, scheduler
    from db import connect

    worker, state, db_path = deadline_loop
    worker._running = False
    with connect(db_path) as conn:
        if keep_completed_yesterday:
            conn.execute(
                "UPDATE scheduler_tasks SET status = 'done', task_key = ?, run_at = ?",
                ("taiwan_precise_open:2026-10-07", (DEADLINE - timedelta(days=1)).isoformat()),
            )
        else:
            conn.execute("DELETE FROM scheduler_tasks")
    monkeypatch.setattr(collectors, "_get_taiwan_draw_time_parts", lambda _path: (22, 32))
    monkeypatch.setattr(
        scheduler, "sync_all_lottery_type_next_times", lambda *_args, **_kw: {"checked": 0, "updated": 0}
    )
    monkeypatch.setattr(scheduler, "_ensure_daily_prediction_task", lambda _path: None)
    monkeypatch.setattr(scheduler, "_ensure_postgres_backup_tasks", lambda _path: None)
    for method in (
        "_schedule_auto_open",
        "_schedule_auto_crawl",
        "_schedule_staged_timeout_alerts",
        "_schedule_publication_loop",
        "_run_daily_prediction_if_missed",
        "_reschedule_precise_checks",
    ):
        monkeypatch.setattr(worker, method, lambda: None)
    enqueued = []
    original_ensure = scheduler._ensure_taiwan_precise_open_task

    def ensure_once(path):
        enqueued.append(path)
        return original_ensure(path)

    monkeypatch.setattr(scheduler, "_ensure_taiwan_precise_open_task", ensure_once)
    worker.start()
    assert enqueued == [db_path]
    assert state["executed"] == []
    with connect(db_path) as conn:
        pending = conn.execute("SELECT run_at FROM scheduler_tasks WHERE status = 'pending'").fetchone()
    assert pending["run_at"] == DEADLINE.isoformat()
    assert state["timers"][-1].interval == 7.25
    state["now"] = DEADLINE
    state["timers"][-1].callback()
    assert len(state["executed"]) == 1


@pytest.mark.parametrize("late_seconds", [0, 0.1, 78])
def test_restart_at_or_after_deadline_executes_once_then_resumes_default(deadline_loop, late_seconds):
    worker, state, _db_path = deadline_loop
    state["now"] = DEADLINE + timedelta(seconds=late_seconds)
    worker._schedule_task_loop()
    assert len(state["executed"]) == 1
    assert state["timers"][-1].interval == 30
    state["timers"][-1].callback()
    assert len(state["executed"]) == 1


def test_clock_backward_jump_rechecks_wall_deadline_without_opening_early(deadline_loop):
    worker, state, _db_path = deadline_loop
    worker._schedule_task_loop()
    timer = state["timers"][-1]
    state["now"] = DEADLINE - timedelta(seconds=78)
    timer.callback()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 30

    state["now"] = DEADLINE - timedelta(seconds=0.5)
    state["timers"][-1].callback()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 0.5
    state["now"] = DEADLINE
    state["timers"][-1].callback()
    assert len(state["executed"]) == 1


def test_nearest_persisted_taiwan_task_wins_over_tomorrow(deadline_loop):
    from domains.scheduler import service

    worker, state, db_path = deadline_loop
    service.upsert_scheduler_task(
        db_path,
        task_type=service.TASK_TYPE_TAIWAN_PRECISE_OPEN,
        payload={"schedule_date": "2026-10-09"},
        run_at=(DEADLINE + timedelta(days=1)).isoformat(),
    )
    worker._schedule_task_loop()
    assert state["timers"][-1].interval == 7.25


@pytest.mark.parametrize("status", ["done", "failed", "running"])
def test_non_pending_taiwan_task_does_not_cause_tight_polling(deadline_loop, status):
    from db import connect

    worker, state, db_path = deadline_loop
    with connect(db_path) as conn:
        conn.execute("UPDATE scheduler_tasks SET status = ?", (status,))
    worker._schedule_task_loop()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 30


def test_other_task_near_deadline_keeps_default_poll_interval(deadline_loop):
    from db import connect

    worker, state, db_path = deadline_loop
    with connect(db_path) as conn:
        conn.execute("UPDATE scheduler_tasks SET task_type = 'daily_prediction'")
    worker._schedule_task_loop()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 30


def test_far_taiwan_deadline_keeps_default_poll_interval(deadline_loop):
    worker, state, _db_path = deadline_loop
    state["now"] = DEADLINE - timedelta(hours=2)
    worker._schedule_task_loop()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 30


def test_due_pending_task_retries_in_one_second_after_acquisition_error(deadline_loop, monkeypatch):
    worker, state, _db_path = deadline_loop
    state["now"] = DEADLINE
    monkeypatch.setattr(worker, "_run_due_tasks", lambda: None)
    worker._schedule_task_loop()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 1


def test_second_worker_cannot_open_a_claimed_deadline_task_again(deadline_loop, monkeypatch):
    from crawler import scheduler

    worker, state, db_path = deadline_loop
    state["now"] = DEADLINE
    second_worker = scheduler.CrawlerScheduler(db_path)
    second_worker._running = True
    second_executed = []
    monkeypatch.setattr(second_worker, "_execute_task", lambda task: second_executed.append(task))

    def execute_while_another_worker_checks(task):
        state["executed"].append(task)
        second_worker._schedule_task_loop()
        assert state["timers"][-1].interval == 30

    monkeypatch.setattr(worker, "_execute_task", execute_while_another_worker_checks)
    worker._schedule_task_loop()
    assert len(state["executed"]) == 1
    assert second_executed == []
    second_worker._schedule_task_loop()
    assert second_executed == []


@pytest.mark.parametrize("invalid", ["", "not-an-ISO-date"])
def test_invalid_deadline_metadata_keeps_the_loop_alive(deadline_loop, invalid):
    from db import connect

    worker, state, db_path = deadline_loop
    with connect(db_path) as conn:
        conn.execute("UPDATE scheduler_tasks SET run_at = ?", (invalid,))
    # Read invalid metadata without trying to acquire the intentionally malformed row.
    assert worker._task_loop_delay_seconds() == 30


def test_deadline_metadata_read_failure_keeps_the_loop_alive(deadline_loop, monkeypatch):
    from domains.scheduler import service

    worker, state, _db_path = deadline_loop

    def unavailable(_path):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(service, "get_next_taiwan_precise_open_run_at", unavailable)
    worker._schedule_task_loop()
    assert state["executed"] == []
    assert state["timers"][-1].interval == 30


def test_deadline_lookup_is_one_narrow_read_and_does_not_write(deadline_loop, monkeypatch):
    from db import connect
    from domains.scheduler import repository

    worker, _state, db_path = deadline_loop
    queries = []
    original = repository.find_next_pending_task

    def narrow_read(conn, *, task_type):
        queries.append(task_type)
        return original(conn, task_type=task_type)

    monkeypatch.setattr(repository, "find_next_pending_task", narrow_read)
    with connect(db_path) as conn:
        before = dict(conn.execute("SELECT * FROM scheduler_tasks").fetchone())
    assert worker._task_loop_delay_seconds() == 7.25
    assert queries == ["taiwan_precise_open"]
    with connect(db_path) as conn:
        after = dict(conn.execute("SELECT * FROM scheduler_tasks").fetchone())
    assert after == before
