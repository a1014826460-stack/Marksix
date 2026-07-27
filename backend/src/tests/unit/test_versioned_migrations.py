from __future__ import annotations

import pytest


def test_runtime_validation_rejects_a_postgres_database_without_migration_ledger(monkeypatch):
    from database import versioned_migrations

    class _Connection:
        engine = "postgres"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def table_exists(self, table_name):
            assert table_name == "schema_migrations"
            return False

    monkeypatch.setattr(versioned_migrations, "connect", lambda _target: _Connection())

    with pytest.raises(versioned_migrations.SchemaMigrationRequired, match="database.versioned_migrations"):
        versioned_migrations.validate_runtime_schema("postgresql://migration-test")


def test_runtime_validation_reads_the_ledger_without_executing_schema_ddl(monkeypatch):
    from database import versioned_migrations

    class _Cursor:
        def fetchall(self):
            return [
                {"version": migration.version}
                for migration in versioned_migrations.MIGRATIONS
            ]

    class _Connection:
        engine = "postgres"

        def __init__(self):
            self.statements: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def table_exists(self, table_name):
            return table_name == "schema_migrations"

        def execute(self, sql, _params=None):
            self.statements.append(str(sql))
            return _Cursor()

    conn = _Connection()
    monkeypatch.setattr(versioned_migrations, "connect", lambda _target: conn)

    versioned_migrations.validate_runtime_schema("postgresql://migration-test")

    assert conn.statements
    assert not any(statement.lstrip().upper().startswith(("CREATE", "ALTER", "DROP")) for statement in conn.statements)


def test_explicit_migration_runner_uses_a_transaction_advisory_lock_and_records_the_baseline(monkeypatch):
    from database import versioned_migrations

    class _Cursor:
        def fetchall(self):
            return []

    class _Connection:
        engine = "postgres"

        def __init__(self):
            self.statements: list[str] = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, sql, _params=None):
            self.statements.append(str(sql))
            return _Cursor()

    conn = _Connection()
    applied: list[int] = []
    reconciled: list[bool] = []
    monkeypatch.setattr(versioned_migrations, "connect", lambda _target: conn)
    monkeypatch.setattr(
        versioned_migrations,
        "MIGRATIONS",
        (versioned_migrations.Migration(1, "baseline", lambda _conn: applied.append(1)),),
    )
    monkeypatch.setattr(
        versioned_migrations,
        "_reconcile_created_prediction_tables",
        lambda _conn: reconciled.append(True),
    )

    assert versioned_migrations.run_migrations("postgresql://migration-test") == [1]
    assert applied == [1]
    assert any("pg_advisory_xact_lock" in statement for statement in conn.statements)
    assert any("CREATE TABLE IF NOT EXISTS schema_migrations" in statement for statement in conn.statements)
    assert any("INSERT INTO schema_migrations" in statement for statement in conn.statements)
    assert reconciled == [True]


def test_created_table_reconciliation_uses_metadata_and_discovered_public_payload_tables(monkeypatch):
    """A valid public payload table must not depend on stale metadata to be mirrored."""
    from database import versioned_migrations
    from utils import created_prediction_store

    class _Cursor:
        def fetchall(self):
            return [
                {"table_name": "mode_payload_47"},
                {"table_name": "mode_payload_99"},  # Stale metadata without a public source table.
            ]

    class _Connection:
        def table_exists(self, table_name):
            return table_name in {"mode_payload_tables", "mode_payload_47", "mode_payload_53"}

        def list_tables(self, prefix):
            assert prefix == "mode_payload_"
            return ["mode_payload_53", "mode_payload_47", "mode_payload_tables"]

        def execute(self, sql, _params=None):
            assert "SELECT table_name FROM mode_payload_tables" in sql
            return _Cursor()

    reconciled: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        created_prediction_store,
        "ensure_created_prediction_table",
        lambda _conn, table_name, *, commit: (
            (_ for _ in ()).throw(ValueError("源表不存在"))
            if table_name == "mode_payload_99"
            else reconciled.append((table_name, commit))
        ),
    )

    versioned_migrations._reconcile_created_prediction_tables(_Connection())

    assert reconciled == [("mode_payload_47", False), ("mode_payload_53", False)]


def test_postgres_ensure_admin_tables_only_validates_runtime_schema(monkeypatch):
    import database.bootstrap as bootstrap

    validated: list[str] = []
    monkeypatch.setattr(bootstrap, "detect_database_engine", lambda _target: "postgres")
    monkeypatch.setattr(bootstrap, "validate_runtime_schema", lambda target: validated.append(str(target)))

    bootstrap.ensure_admin_tables("postgresql://migration-test")

    assert validated == ["postgresql://migration-test"]


def test_migration_command_rejects_sqlite_targets():
    from database.versioned_migrations import run_migrations

    with pytest.raises(RuntimeError, match="仅支持 PostgreSQL"):
        run_migrations("migration-test.sqlite3")


def test_migration_nine_drops_only_the_prefix_hash_unique_constraint():
    from database.versioned_migrations import _relax_prediction_control_prefix_uniqueness

    class _Cursor:
        def fetchall(self):
            return [
                {
                    "constraint_name": "prediction_generation_controls_prefix_key",
                    "constraint_definition": "UNIQUE (lottery_type_id, year, term, mode_id, prefix_hash)",
                },
                {
                    "constraint_name": "prediction_generation_controls_site_key",
                    "constraint_definition": "UNIQUE (lottery_type_id, year, term, mode_id, web_id)",
                },
            ]

    class _Connection:
        engine = "postgres"

        def __init__(self):
            self.statements: list[str] = []

        def execute(self, sql, _params=None):
            self.statements.append(str(sql))
            return _Cursor()

    conn = _Connection()
    _relax_prediction_control_prefix_uniqueness(conn)

    assert len(conn.statements) == 2
    assert "pg_constraint" in conn.statements[0]
    assert "conname AS constraint_name" in conn.statements[0]
    assert "DROP CONSTRAINT" in conn.statements[1]
    assert "prefix_key" in conn.statements[1]


def test_migration_three_upserts_shengshi8800_profile_and_only_migrates_default_site_four_rows(tmp_path):
    """Site 4's reachable-page profile must be explicit on already deployed DBs."""
    from db import connect
    from database.versioned_migrations import _sync_shengshi8800_page_authorization
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    db_path = str(tmp_path / "shengshi8800-migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_blueprint_profiles (
                blueprint_name TEXT PRIMARY KEY,
                required_mode_ids_json TEXT NOT NULL,
                known_unavailable_mode_ids_json TEXT NOT NULL,
                blocked_items_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                blueprint_name TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO site_blueprint_profiles (
                blueprint_name, required_mode_ids_json,
                known_unavailable_mode_ids_json, blocked_items_json,
                created_at, updated_at
            ) VALUES ('shengshi8800', '[64]', '[]', '[]', 'old', 'old')
            """
        )
        conn.execute(
            """
            INSERT INTO managed_sites (id, web_id, blueprint_name) VALUES
                (4, 4, 'default'),
                (40, 4, NULL),
                (41, 4, 'custom-site-four'),
                (5, 5, 'default')
            """
        )

        _sync_shengshi8800_page_authorization(conn)
        profile = conn.execute(
            """
            SELECT required_mode_ids_json, known_unavailable_mode_ids_json,
                   blocked_items_json, updated_at
            FROM site_blueprint_profiles
            WHERE blueprint_name = 'shengshi8800'
            """
        ).fetchone()
        sites = conn.execute(
            "SELECT id, blueprint_name FROM managed_sites ORDER BY id"
        ).fetchall()

    import json

    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == required_mode_ids_for_site_key(
        "shengshi8800"
    )
    assert json.loads(str(profile["known_unavailable_mode_ids_json"])) == []
    assert json.loads(str(profile["blocked_items_json"])) == []
    assert str(profile["updated_at"]) != "old"
    assert [(int(row["id"]), row["blueprint_name"]) for row in sites] == [
        (4, "shengshi8800"),
        (5, "default"),
        (40, "shengshi8800"),
        (41, "custom-site-four"),
    ]


def test_migration_four_registers_twssz_profile_and_site_identity(tmp_path):
    """The new vendor site must have a deployable profile without manual DB edits."""
    import json

    from db import connect
    from database.versioned_migrations import _install_twssz_site_profile
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    db_path = str(tmp_path / "twssz-migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_blueprint_profiles (
                blueprint_name TEXT PRIMARY KEY,
                required_mode_ids_json TEXT NOT NULL,
                known_unavailable_mode_ids_json TEXT NOT NULL,
                blocked_items_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY,
                web_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                domain TEXT,
                lottery_type_id INTEGER,
                enabled INTEGER NOT NULL,
                blueprint_name TEXT,
                announcement TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        _install_twssz_site_profile(conn)
        profile = conn.execute(
            "SELECT required_mode_ids_json FROM site_blueprint_profiles WHERE blueprint_name = 'twssz'"
        ).fetchone()
        site = conn.execute(
            "SELECT id, web_id, name, domain, lottery_type_id, enabled, blueprint_name FROM managed_sites WHERE id = 9"
        ).fetchone()

    assert profile is not None
    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == required_mode_ids_for_site_key("twssz")
    assert dict(site) == {
        "id": 9,
        "web_id": 9,
        "name": "台湾神算子",
        "domain": "www.twssz.com",
        "lottery_type_id": 3,
        "enabled": 1,
        "blueprint_name": "twssz",
    }


def test_migration_five_imports_twssz_static_prediction_history_into_created_tables(monkeypatch):
    """The vendor's supplied historical table must be available through the shared API."""
    from database import versioned_migrations

    ensured: list[tuple[str, bool]] = []
    inserted: list[tuple[str, dict[str, str], bool]] = []

    monkeypatch.setattr(
        "utils.created_prediction_store.ensure_created_prediction_table",
        lambda _conn, table_name, *, commit: ensured.append((table_name, commit)),
    )
    monkeypatch.setattr(
        "utils.created_prediction_store.upsert_created_prediction_row",
        lambda _conn, table_name, row_data, *, commit: inserted.append((table_name, row_data, commit)),
    )

    versioned_migrations._import_twssz_static_prediction_history(object())

    assert ensured == [
        ("mode_payload_44", False),
        ("mode_payload_78", False),
        ("mode_payload_481", False),
        ("mode_payload_69", False),
        ("mode_payload_51", False),
        ("mode_payload_43", False),
        ("mode_payload_66", False),
    ]
    assert len(inserted) == 56
    assert all(row[1]["type"] == "3" and row[1]["web"] == "9" for row in inserted)
    assert all(row[1]["year"] == "0" for row in inserted)
    assert all(row[2] is False for row in inserted)
    assert inserted[0] == (
        "mode_payload_44",
        {
            "type": "3",
            "year": "0",
            "term": "204",
            "web": "9",
            "web_id": "9",
            "modes_id": "44",
            "content": "兔,牛,猪,龙,蛇,羊,鼠",
        },
        False,
    )
    assert inserted[-1] == (
        "mode_payload_66",
        {
            "type": "3",
            "year": "0",
            "term": "197",
            "web": "9",
            "web_id": "9",
            "modes_id": "66",
            "content": "20,44,49,13,12",
        },
        False,
    )


def test_compose_runs_migrations_from_the_source_directory_before_api_and_worker_start():
    from pathlib import Path

    compose = (Path(__file__).resolve().parents[4] / "docker-compose.yml").read_text(encoding="utf-8")

    assert 'command: ["sh", "-c", "cd /app/src && python -m database.versioned_migrations' in compose
    assert "--db-path \\\"$$DATABASE_URL\\\"" in compose
    assert "db-migrate:" in compose
    assert compose.count("condition: service_completed_successfully") >= 2


def test_api_validates_schema_before_loading_dynamic_prediction_configs(monkeypatch):
    from app_http import server

    calls: list[str] = []
    monkeypatch.setattr(server, "ensure_admin_tables", lambda _db_path: calls.append("validate_schema"))
    monkeypatch.setattr(server, "ensure_prediction_configs_loaded", lambda _db_path: calls.append("load_configs"))
    monkeypatch.setattr(server, "init_logging", lambda _db_path: None)
    monkeypatch.setattr(server, "log_startup_risk_warnings", lambda: None)
    monkeypatch.setattr(server, "detect_database_engine", lambda _db_path: "postgres")

    class _HttpServer:
        def __init__(self, *_args):
            pass

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            pass

    monkeypatch.setattr(server, "ThreadingHTTPServer", _HttpServer)

    with pytest.raises(KeyboardInterrupt):
        server.run_server("127.0.0.1", 8000, "postgresql://migration-test")

    assert calls == ["validate_schema", "load_configs"]


def test_worker_validates_schema_before_loading_dynamic_prediction_configs(monkeypatch):
    import scheduler_worker

    calls: list[str] = []
    monkeypatch.setattr(scheduler_worker, "ensure_admin_tables", lambda _db_path: calls.append("validate_schema"))
    monkeypatch.setattr(scheduler_worker, "ensure_prediction_configs_loaded", lambda _db_path: calls.append("load_configs"))
    monkeypatch.setattr(scheduler_worker, "init_logging", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "log_startup_risk_warnings", lambda: None)
    monkeypatch.setattr(scheduler_worker, "detect_database_engine", lambda _db_path: "postgres")
    # This test covers schema/config ordering, not runtime endpoint policy.
    monkeypatch.setattr(scheduler_worker, "validate_runtime_database_target", lambda _db_path: None)
    monkeypatch.setattr(scheduler_worker, "try_acquire_scheduler_worker_lease", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(scheduler_worker, "_task_poll_interval_seconds", lambda _db_path: 0)
    monkeypatch.setattr(scheduler_worker, "_worker_lease_seconds", lambda _db_path: 30)
    monkeypatch.setattr(scheduler_worker.time, "sleep", lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(
        scheduler_worker,
        "build_parser",
        lambda: type("P", (), {"parse_args": lambda _self: type("A", (), {"db_path": "postgresql://migration-test"})()})(),
    )

    with pytest.raises(KeyboardInterrupt):
        scheduler_worker.main()

    assert calls == ["validate_schema", "load_configs"]


def test_database_log_handler_does_not_create_tables_at_runtime():
    from logger import DatabaseLogHandler

    assert not hasattr(DatabaseLogHandler, "_ensure_table")


def test_runtime_config_operations_do_not_prepare_schema(monkeypatch, tmp_path):
    import runtime_config
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "runtime-config-no-ddl.sqlite3")
    ensure_admin_tables(db_path)
    monkeypatch.setattr(
        runtime_config,
        "ensure_system_config_table",
        lambda *_args, **_kwargs: pytest.fail("runtime config operation must not run schema DDL"),
    )
    monkeypatch.setattr(
        runtime_config,
        "seed_system_config_defaults",
        lambda *_args, **_kwargs: pytest.fail("runtime config operation must not seed schema"),
    )

    assert runtime_config.list_system_configs(db_path)
    runtime_config.upsert_system_config(db_path, key="logging.backup_count", value=7, value_type="int")
    runtime_config.reset_config(db_path, "logging.backup_count")


@pytest.mark.parametrize(
    "key",
    (
        "database.backup_timeout_seconds",
        "database.backup_verify_timeout_seconds",
        "database.backup_min_free_space_mb",
    ),
)
def test_backup_numeric_configuration_rejects_negative_values(key):
    from runtime_config import validate_config_value

    assert validate_config_value(key, -1, "int") == (False, f"'{key}' 不能为负数，当前值: -1")
