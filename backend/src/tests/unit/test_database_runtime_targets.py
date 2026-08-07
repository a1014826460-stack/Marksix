from __future__ import annotations

import pytest

from database.runtime_targets import resolve_database_targets
from tests.helpers.api_contract import make_ctx


def test_write_url_overrides_legacy_database_url():
    targets = resolve_database_targets(
        environ={
            "DATABASE_URL": "postgresql://legacy/db",
            "DATABASE_WRITE_URL": "postgresql://writer/db",
            "DATABASE_READ_URL": "postgresql://reader/db",
        }
    )

    assert targets.write == "postgresql://writer/db"
    assert targets.read == "postgresql://reader/db"


def test_legacy_database_url_remains_the_local_write_and_read_default():
    targets = resolve_database_targets(environ={"DATABASE_URL": "postgresql://local/db"})

    assert targets.write == "postgresql://local/db"
    assert targets.read == "postgresql://local/db"


def test_explicit_cli_target_overrides_write_environment_but_keeps_read_environment():
    targets = resolve_database_targets(
        explicit_write="postgresql://cli/db",
        environ={
            "DATABASE_WRITE_URL": "postgresql://writer/db",
            "DATABASE_READ_URL": "postgresql://reader/db",
        },
    )

    assert targets.write == "postgresql://cli/db"
    assert targets.read == "postgresql://reader/db"


def test_missing_database_target_is_rejected():
    with pytest.raises(RuntimeError, match="DATABASE_WRITE_URL or DATABASE_URL"):
        resolve_database_targets(environ={})


@pytest.mark.parametrize("name", ["DATABASE_WRITE_URL", "DATABASE_READ_URL"])
def test_non_postgres_runtime_target_is_rejected(name):
    environ = {"DATABASE_URL": "postgresql://local/db", name: "sqlite:///runtime.db"}

    with pytest.raises(RuntimeError, match=name):
        resolve_database_targets(environ=environ)


def test_request_context_exposes_write_and_read_targets_with_legacy_write_alias():
    ctx = make_ctx("/health")
    ctx.handler.server.write_db_path = "postgresql://writer/db"
    ctx.handler.server.read_db_path = "postgresql://reader/db"

    assert ctx.write_db_path == "postgresql://writer/db"
    assert ctx.read_db_path == "postgresql://reader/db"
    assert ctx.db_path == "postgresql://writer/db"


def test_request_context_falls_back_to_legacy_db_path_for_both_roles():
    ctx = make_ctx("/health")

    assert ctx.write_db_path == ctx.handler.server.db_path
    assert ctx.read_db_path == ctx.handler.server.db_path
    assert ctx.db_path == ctx.handler.server.db_path
