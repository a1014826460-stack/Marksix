"""PostgreSQL migration-ledger integration coverage.

Requires TEST_DATABASE_URL. The target database must be disposable because the
test clears only the migration ledger before exercising the lock-protected
baseline bookkeeping.
"""

from __future__ import annotations

import pytest

from tests.conftest import requires_test_db


@requires_test_db
def test_postgres_runtime_validation_accepts_the_current_migration_ledger(db_path):
    from database.versioned_migrations import run_migrations, validate_runtime_schema

    run_migrations(db_path)
    validate_runtime_schema(db_path)


@requires_test_db
def test_postgres_migration_runner_is_idempotent_after_the_baseline(db_path):
    from database.versioned_migrations import run_migrations

    run_migrations(db_path)
    assert run_migrations(db_path) == []


@requires_test_db
def test_postgres_runtime_config_operations_do_not_issue_schema_ddl(db_path, monkeypatch):
    import runtime_config
    from database.versioned_migrations import run_migrations

    run_migrations(db_path)
    monkeypatch.setattr(
        runtime_config,
        "ensure_system_config_table",
        lambda *_args, **_kwargs: pytest.fail("runtime config operation attempted schema DDL"),
    )

    runtime_config.list_system_configs(db_path)
    runtime_config.upsert_system_config(
        db_path,
        key="logging.backup_count",
        value=7,
        value_type="int",
    )


@requires_test_db
def test_postgres_scheduler_task_is_exclusively_acquired_and_recovers_after_lock_timeout(db_path):
    from datetime import datetime, timedelta, timezone

    from db import connect
    from database.versioned_migrations import run_migrations
    from domains.scheduler import service

    run_migrations(db_path)
    run_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    task_key = f"integration-recovery:{datetime.now(timezone.utc).timestamp()}"
    service.upsert_scheduler_task(
        db_path,
        task_type="integration_recovery",
        payload={"key": task_key},
        run_at=run_at,
        max_attempts=2,
        task_key_override=task_key,
    )

    acquired_by_a = service.acquire_due_scheduler_tasks(db_path, worker_id="integration-worker-a")
    assert [task["task_key"] for task in acquired_by_a] == [task_key]
    assert service.acquire_due_scheduler_tasks(db_path, worker_id="integration-worker-b") == []

    stale_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE scheduler_tasks SET locked_at = ? WHERE task_key = ?",
            (stale_at, task_key),
        )

    acquired_by_b = service.acquire_due_scheduler_tasks(db_path, worker_id="integration-worker-b")
    assert [task["task_key"] for task in acquired_by_b] == [task_key]
