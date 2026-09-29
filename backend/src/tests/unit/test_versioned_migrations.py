from __future__ import annotations

import re

import pytest


def test_latest_migration_creates_forced_announcement_tables():
    from database import versioned_migrations

    class _Connection:
        engine = "sqlite"

        def __init__(self):
            self.statements: list[str] = []

        def execute(self, sql, _params=None):
            self.statements.append(str(sql))

    conn = _Connection()
    latest = versioned_migrations.MIGRATIONS[-1]

    assert versioned_migrations.CURRENT_SCHEMA_VERSION == 32
    assert latest.version == 32
    assert latest.name == "resync_wuxing_number_groups_and_element_content"
    # forced_announcements 表由迁移 27 创建，验证它仍然存在
    forced = next(m for m in versioned_migrations.MIGRATIONS if m.version == 27)
    assert forced.name == "create_forced_announcements"
    forced.apply(conn)
    assert any("CREATE TABLE IF NOT EXISTS forced_announcements" in sql for sql in conn.statements)
    assert any("CREATE TABLE IF NOT EXISTS forced_announcement_sites" in sql for sql in conn.statements)


def test_migration_thirty_adds_lottery_draws_opened_at_once(tmp_path):
    """迁移 30 给 lottery_draws 补 opened_at 揭示锚点列，且可重复执行。"""
    from db import connect
    from database.versioned_migrations import _add_lottery_draws_opened_at

    db_path = str(tmp_path / "opened-at-migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE lottery_draws (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lottery_type_id INTEGER NOT NULL,
                year INTEGER NOT NULL,
                term INTEGER NOT NULL,
                numbers TEXT NOT NULL,
                draw_time TEXT,
                status INTEGER NOT NULL DEFAULT 1,
                is_opened INTEGER NOT NULL DEFAULT 0,
                next_term INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        _add_lottery_draws_opened_at(conn)
        _add_lottery_draws_opened_at(conn)
        columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(lottery_draws)").fetchall()
        ]

    assert columns.count("opened_at") == 1


def test_migration_twenty_nine_moves_the_history_gate_without_touching_custom_values(tmp_path):
    from db import connect
    from database.versioned_migrations import _raise_history_publication_delay_to_eight_minutes

    db_path = str(tmp_path / "history-delay-migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value_text TEXT,
                value_type TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO system_config (key, value_text, value_type, updated_at) VALUES "
            "('history_backfill_delay_after_draw', '4', 'int', 'old'), "
            "('alert.draw_red_timeout_seconds', '300', 'int', 'old')"
        )

        _raise_history_publication_delay_to_eight_minutes(conn)
        migrated = conn.execute(
            "SELECT value_text, updated_at FROM system_config WHERE key = 'history_backfill_delay_after_draw'"
        ).fetchone()
        untouched = conn.execute(
            "SELECT value_text FROM system_config WHERE key = 'alert.draw_red_timeout_seconds'"
        ).fetchone()

        # 管理员显式改过的值不会被迁移覆盖。
        conn.execute(
            "UPDATE system_config SET value_text = '45' WHERE key = 'history_backfill_delay_after_draw'"
        )
        _raise_history_publication_delay_to_eight_minutes(conn)
        custom = conn.execute(
            "SELECT value_text FROM system_config WHERE key = 'history_backfill_delay_after_draw'"
        ).fetchone()

    assert migrated["value_text"] == "8"
    assert migrated["updated_at"] != "old"
    assert untouched["value_text"] == "300"
    assert custom["value_text"] == "45"


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


def test_twssz_import_creates_a_missing_public_source_before_created_mirror(monkeypatch):
    from database import versioned_migrations

    ensured: list[tuple[int, str]] = []
    created: list[str] = []

    class _Connection:
        engine = "postgres"

        def table_exists(self, table_name):
            return False

    monkeypatch.setattr(
        "database.schema.legacy.ensure_basic_prediction_payload_table",
        lambda _conn, _pk, *, modes_id, title: ensured.append((modes_id, title)),
    )
    monkeypatch.setattr(
        "utils.created_prediction_store.ensure_created_prediction_table",
        lambda _conn, table_name, *, commit: created.append(table_name),
    )
    monkeypatch.setattr(
        "utils.created_prediction_store.upsert_created_prediction_row",
        lambda *_args, **_kwargs: None,
    )

    versioned_migrations._import_twssz_static_prediction_history(_Connection())

    assert [mode_id for mode_id, _title in ensured] == [44, 78, 481, 69, 51, 43, 66]
    assert created == [
        "mode_payload_44", "mode_payload_78", "mode_payload_481", "mode_payload_69",
        "mode_payload_51", "mode_payload_43", "mode_payload_66",
    ]


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


def test_migration_ten_registers_twbst528_profile_site_identity_and_modules(tmp_path):
    """The new vendor site must be deployable without manual database edits."""
    import json

    from db import connect
    from database.versioned_migrations import _install_twbst528_site_profile
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    db_path = str(tmp_path / "twbst528-migration.sqlite3")
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
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL,
                mode_id INTEGER NOT NULL,
                status INTEGER NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                title TEXT,
                UNIQUE(site_id, mechanism_key)
            )
            """
        )

        _install_twbst528_site_profile(conn)
        _install_twbst528_site_profile(conn)
        profile = conn.execute(
            "SELECT required_mode_ids_json FROM site_blueprint_profiles WHERE blueprint_name = 'twbst528'"
        ).fetchone()
        site = conn.execute(
            "SELECT id, web_id, name, domain, lottery_type_id, enabled, blueprint_name FROM managed_sites WHERE id = 10"
        ).fetchone()
        modules = conn.execute(
            "SELECT mode_id, status FROM site_prediction_modules WHERE site_id = 10 ORDER BY sort_order, id"
        ).fetchall()

    expected_mode_ids = required_mode_ids_for_site_key("twbst528")
    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == expected_mode_ids
    assert dict(site) == {
        "id": 10,
        "web_id": 10,
        "name": "台湾百事通",
        "domain": "www.twbst528.com",
        "lottery_type_id": 3,
        "enabled": 1,
        "blueprint_name": "twbst528",
    }
    assert [(int(row["mode_id"]), int(row["status"])) for row in modules] == [
        (mode_id, 1) for mode_id in expected_mode_ids
    ]


def test_migration_fourteen_resyncs_twbst528_for_the_taiwan_pmt_image(tmp_path):
    from db import connect
    from database.versioned_migrations import _sync_twbst528_taiwan_pmt_image

    db_path = str(tmp_path / "twbst528-pmt-migration.sqlite3")
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
                id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL,
                domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL,
                blueprint_name TEXT, announcement TEXT, notes TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL,
                sort_order INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                title TEXT, UNIQUE(site_id, mechanism_key)
            )
            """
        )

        _sync_twbst528_taiwan_pmt_image(conn)
        image_module = conn.execute(
            "SELECT mechanism_key, mode_id, status FROM site_prediction_modules WHERE site_id = 10 AND mode_id = 478"
        ).fetchone()

    assert dict(image_module) == {"mechanism_key": "tw_pmt_image", "mode_id": 478, "status": 1}


def test_migration_twenty_four_inserts_twssz_title_five_authorization(tmp_path):
    """An existing twssz module profile must gain title_5 without resetting its rows."""
    from db import connect
    from database.versioned_migrations import _sync_twssz_title_five_authorization

    db_path = str(tmp_path / "twssz-title-five-migration.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE site_blueprint_profiles (
                blueprint_name TEXT PRIMARY KEY, required_mode_ids_json TEXT NOT NULL,
                known_unavailable_mode_ids_json TEXT NOT NULL, blocked_items_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE managed_sites (
                id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL,
                domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL,
                blueprint_name TEXT, announcement TEXT, notes TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE site_prediction_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER NOT NULL,
                mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL,
                sort_order INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                title TEXT, UNIQUE(site_id, mechanism_key)
            )
            """
        )

        _sync_twssz_title_five_authorization(conn)
        first = conn.execute(
            "SELECT mechanism_key, mode_id, status FROM site_prediction_modules "
            "WHERE site_id = 9 AND mechanism_key = 'title_5'"
        ).fetchone()
        _sync_twssz_title_five_authorization(conn)
        all_rows = conn.execute(
            "SELECT mechanism_key FROM site_prediction_modules "
            "WHERE site_id = 9 AND mechanism_key = 'title_5'"
        ).fetchall()

    assert dict(first) == {"mechanism_key": "title_5", "mode_id": 5, "status": 1}
    assert len(all_rows) == 1


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
    monkeypatch.setattr(server, "create_cache_store", lambda: object())

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


# ── 迁移 32：号码五行整体改判（fixed_data + 已落库五行正文）──────────────

#: 迁移前 `public.fixed_data` `sign='五行'` 的旧分组正文（新表有 25 个号码换组）。
LEGACY_WUXING_CODES: dict[str, str] = {
    "金": "03,04,11,12,25,26,33,34,41,42",
    "木": "07,08,15,16,23,24,37,38,45,46",
    "水": "13,14,21,22,29,30,43,44",
    "火": "01,02,09,10,17,18,31,32,39,40,47,48",
    "土": "05,06,19,20,27,28,35,36,49",
}

#: `sign='五行肖'`（**生肖五行**）—— 迁移必须一字不动。
WUXING_XIAO_ROWS: tuple[tuple[str, str], ...] = (
    ("金肖", "鸡,猴"),
    ("木肖", "兔,虎"),
    ("水肖", "鼠,猪"),
    ("火肖", "蛇,马"),
    ("土肖", "牛,龙,羊,狗"),
)


def _create_fixed_data_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE fixed_data (
            id INTEGER PRIMARY KEY,
            year TEXT, sign TEXT, type INTEGER, name TEXT,
            xu INTEGER, code TEXT, status INTEGER
        )
        """
    )


def test_migration_thirty_two_rewrites_the_wuxing_number_groups_idempotently(tmp_path):
    """`sign='五行'` 按新表重写；值一致时不写库；`sign='五行肖'` 不被触碰。"""
    from db import connect
    from database.versioned_migrations import _resync_fixed_data_wuxing_groups
    from predict.common import ELEMENT_NUMBER_GROUPS, ELEMENT_ORDER

    db_path = str(tmp_path / "wuxing-groups-migration.sqlite3")
    with connect(db_path) as conn:
        _create_fixed_data_table(conn)
        row_id = 0
        for label in ELEMENT_ORDER:
            row_id += 1
            conn.execute(
                "INSERT INTO fixed_data (id, year, sign, type, name, xu, code, status) "
                "VALUES (?, '2026', '五行', 2, ?, 1, ?, 1)",
                (row_id, label, LEGACY_WUXING_CODES[label]),
            )
        for label, code in WUXING_XIAO_ROWS:
            row_id += 1
            conn.execute(
                "INSERT INTO fixed_data (id, year, sign, type, name, xu, code, status) "
                "VALUES (?, '', '五行肖', 1, ?, 0, ?, 1)",
                (row_id, label, code),
            )

        first = _resync_fixed_data_wuxing_groups(conn)
        second = _resync_fixed_data_wuxing_groups(conn)
        wuxing = {
            str(row["name"]): str(row["code"])
            for row in conn.execute(
                "SELECT name, code FROM fixed_data WHERE sign = '五行' ORDER BY id"
            ).fetchall()
        }
        xiao = {
            str(row["name"]): str(row["code"])
            for row in conn.execute(
                "SELECT name, code FROM fixed_data WHERE sign = '五行肖' ORDER BY id"
            ).fetchall()
        }

    assert first == 5  # 五个标签的正文都换了
    assert second == 0  # 幂等：第二次不发出任何 UPDATE
    assert wuxing == {
        label: ",".join(ELEMENT_NUMBER_GROUPS[label]) for label in ELEMENT_ORDER
    }
    assert xiao == dict(WUXING_XIAO_ROWS)  # 生肖五行一字未动
    covered = sorted(number for codes in wuxing.values() for number in codes.split(","))
    assert covered == [f"{index:02d}" for index in range(1, 50)]  # 49 码互斥全覆盖


class _FakePayloadCursor:
    def __init__(self, rows=None, rowcount: int = 1) -> None:
        self._rows = list(rows or [])
        self.rowcount = rowcount

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


CREATED_PAYLOAD_COLUMNS: tuple[str, ...] = (
    "id", "content", "web_id", "web", "type", "year", "term",
)


class _FakePayloadConn:
    """最小假 PostgreSQL 连接：只实现「重写 created 五行正文」走到的语句。"""

    engine = "postgres"
    target = "postgresql://fake/db"

    def __init__(self, tables: dict[str, list[dict]]) -> None:
        self.tables = tables
        self.updates: list[tuple[str, str]] = []

    def execute(self, sql_text, params=None):
        sql = " ".join(str(sql_text).split())
        if "information_schema.tables" in sql:
            _schema, table = params
            return _FakePayloadCursor([{"?column?": 1}] if table in self.tables else [])
        if "pg_attribute" in sql:
            return _FakePayloadCursor(
                [{"column_name": name, "column_type": "text"} for name in CREATED_PAYLOAD_COLUMNS]
            )
        if sql.upper().startswith("SELECT"):
            table = re.search(r'FROM "created"\."(mode_payload_\d+)"', sql).group(1)
            return _FakePayloadCursor(list(self.tables[table]))
        if sql.upper().startswith("UPDATE"):
            table = re.search(r'UPDATE "created"\."(mode_payload_\d+)"', sql).group(1)
            new_content, row_id, expected_content = params
            affected = 0
            for row in self.tables[table]:
                if str(row["id"]) == str(row_id) and row["content"] == expected_content:
                    row["content"] = new_content
                    affected += 1
            self.updates.append((table, str(row_id)))
            return _FakePayloadCursor(rowcount=affected)
        raise AssertionError(f"未预期的 SQL：{sql}")


def test_migration_thirty_two_rewrites_created_element_payloads_idempotently():
    """重写 `created.mode_payload_53` / `_482` / `_98` 的 `content`，第二次不再写。"""
    from database.versioned_migrations import (
        WUXING_ELEMENT_PAYLOAD_TABLES,
        _resync_created_wuxing_element_content,
    )

    legacy_53 = (
        '["木|07,08,15,16,23,24,37,38,45,46", "土|05,06,19,20,27,28,35,36,49", '
        '"水|13,14,21,22,29,30,43,44"]'
    )
    expected_53 = (
        '["木|08,09,16,17,24,25,38,39,46,47", "土|06,07,20,21,28,29,36,37", '
        '"水|01,14,15,22,23,30,31,44,45"]'
    )
    legacy_482 = (
        '["金|03,04,11,12,25,26,33,34,41,42",'
        '"火|01,02,09,10,17,18,31,32,39,40,47,48"]'
    )
    expected_482 = (
        '["金|04,05,12,13,26,27,34,35,42,43",'
        '"火|02,03,10,11,18,19,32,33,40,41,48,49"]'
    )
    # mode 98「杀1行」：本站生成的正文只列被杀的 1 行。
    legacy_98 = '["金|03,04,11,12,25,26,33,34,41,42"]'
    expected_98 = '["金|04,05,12,13,26,27,34,35,42,43"]'
    zodiac_content = '["鼠|01,13", "牛|02,14"]'
    # 供应商镜像的 mode_payload_129 不在范围内（created 侧为空表，仅作守门样本）。
    out_of_scope = '["火|01,02,09,10,17,18,31,32,39,40,47,48"]'

    conn = _FakePayloadConn(
        {
            "mode_payload_53": [
                {"id": "c14", "content": legacy_53, "web_id": 4, "type": 2, "year": "2026", "term": "37"},
                {"id": "c15", "content": zodiac_content, "web_id": 4, "type": 2, "year": "2026", "term": "38"},
            ],
            "mode_payload_482": [
                {"id": "c303", "content": legacy_482, "web_id": 7, "type": 3, "year": "2026", "term": "27"},
            ],
            "mode_payload_98": [
                {"id": "c26", "content": legacy_98, "web_id": 8, "type": 2, "year": "2026", "term": "152"},
            ],
            "mode_payload_129": [
                {"id": "c1", "content": out_of_scope, "web_id": 5, "type": 3, "year": "2026", "term": "124"},
            ],
        }
    )

    assert WUXING_ELEMENT_PAYLOAD_TABLES == (
        "mode_payload_53", "mode_payload_482", "mode_payload_98",
    )

    assert _resync_created_wuxing_element_content(conn) == 3
    assert conn.tables["mode_payload_53"][0]["content"] == expected_53
    assert conn.tables["mode_payload_482"][0]["content"] == expected_482
    assert conn.tables["mode_payload_98"][0]["content"] == expected_98
    # 非五行正文的行一字未动
    assert conn.tables["mode_payload_53"][1]["content"] == zodiac_content
    # 目标表之外（供应商镜像 mode 129）不在本次修复范围
    assert conn.tables["mode_payload_129"][0]["content"] == out_of_scope

    conn.updates.clear()
    assert _resync_created_wuxing_element_content(conn) == 0
    assert conn.updates == []  # 幂等：清单已是权威口径时不再发 UPDATE


def test_migration_thirty_two_runs_both_stages(monkeypatch):
    from database import versioned_migrations

    calls: list[str] = []
    monkeypatch.setattr(
        versioned_migrations,
        "_resync_fixed_data_wuxing_groups",
        lambda _conn: calls.append("fixed_data"),
    )
    monkeypatch.setattr(
        versioned_migrations,
        "_resync_created_wuxing_element_content",
        lambda _conn: calls.append("created_content"),
    )

    versioned_migrations._resync_wuxing_number_groups_and_element_content(object())

    assert calls == ["fixed_data", "created_content"]
