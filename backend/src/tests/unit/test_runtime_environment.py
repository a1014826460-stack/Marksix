from __future__ import annotations

import pytest

from runtime_environment import RuntimeEnvironmentError, validate_runtime_database_target


def test_development_accepts_windows_native_postgres_loopback():
    validate_runtime_database_target(
        "postgresql://postgres:secret@127.0.0.1:5432/liuhecai",
        runtime_environment="development",
    )


@pytest.mark.parametrize(
    "target",
    [
        "postgresql://postgres:secret@pgbouncer:6432/liuhecai",
        "postgresql://postgres:secret@localhost:6432/liuhecai",
        "postgresql://postgres:secret@database.example:5432/liuhecai",
    ],
)
def test_development_rejects_non_native_postgres_targets(target: str):
    with pytest.raises(RuntimeEnvironmentError, match="development"):
        validate_runtime_database_target(target, runtime_environment="development")


def test_production_accepts_compose_pgbouncer_target():
    validate_runtime_database_target(
        "postgresql://postgres:secret@pgbouncer:6432/liuhecai",
        runtime_environment="production",
    )


def test_production_managed_mode_accepts_remote_postgres_endpoint():
    validate_runtime_database_target(
        "postgresql://postgres:secret@managed-db.internal:5432/liuhecai",
        runtime_environment="production",
        database_mode="managed",
    )


def test_production_managed_mode_rejects_loopback_postgres_endpoint():
    with pytest.raises(RuntimeEnvironmentError, match="loopback"):
        validate_runtime_database_target(
            "postgresql://postgres:secret@127.0.0.1:5432/liuhecai",
            runtime_environment="production",
            database_mode="managed",
        )


def test_production_rejects_unknown_database_mode():
    with pytest.raises(RuntimeEnvironmentError, match="LIUHECAI_DATABASE_MODE"):
        validate_runtime_database_target(
            "postgresql://postgres:secret@managed-db.internal:5432/liuhecai",
            runtime_environment="production",
            database_mode="other",
        )


@pytest.mark.parametrize(
    "target",
    [
        "postgresql://postgres:secret@127.0.0.1:5432/liuhecai",
        "postgresql://postgres:secret@postgres:5432/liuhecai",
        "postgresql://postgres:secret@pgbouncer:5432/liuhecai",
    ],
)
def test_production_rejects_non_compose_pgbouncer_targets(target: str):
    with pytest.raises(RuntimeEnvironmentError, match="production"):
        validate_runtime_database_target(target, runtime_environment="production")


def test_missing_runtime_profile_is_rejected(monkeypatch):
    monkeypatch.delenv("LIUHECAI_RUNTIME_ENV", raising=False)

    with pytest.raises(RuntimeEnvironmentError, match="LIUHECAI_RUNTIME_ENV"):
        validate_runtime_database_target("postgresql://postgres:secret@127.0.0.1:5432/liuhecai")
