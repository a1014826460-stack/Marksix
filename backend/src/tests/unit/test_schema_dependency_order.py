from __future__ import annotations

from database.bootstrap import ensure_admin_tables
from database.schema.auth import ensure_auth_tables
from database.schema.sites import ensure_site_tables


class _Cursor:
    def fetchall(self):
        return []

    def fetchone(self):
        return None


class _RecordingPostgresConnection:
    engine = "postgres"

    def __init__(self):
        self.executed: list[str] = []
        self.tables: set[str] = set()

    def execute(self, sql, _params=None):
        statement = str(sql)
        self.executed.append(statement)
        if "CREATE TABLE IF NOT EXISTS managed_sites" in statement:
            self.tables.add("managed_sites")
        if "CREATE TABLE IF NOT EXISTS site_permissions" in statement:
            self.tables.add("site_permissions")
        return _Cursor()

    def table_exists(self, table_name):
        return table_name in self.tables

    def table_columns(self, table_name):
        if table_name == "managed_sites":
            return [
                "id", "web_id", "name", "domain", "lottery_type_id", "enabled",
                "blueprint_name", "announcement", "notes", "created_at", "updated_at",
            ]
        return []


def test_site_permissions_are_created_only_after_managed_sites_exist():
    conn = _RecordingPostgresConnection()

    ensure_auth_tables(conn, "id BIGSERIAL PRIMARY KEY")
    assert not any("CREATE TABLE IF NOT EXISTS site_permissions" in sql for sql in conn.executed)

    ensure_site_tables(conn, "id BIGSERIAL PRIMARY KEY")

    managed_sites_index = next(
        index for index, sql in enumerate(conn.executed)
        if "CREATE TABLE IF NOT EXISTS managed_sites" in sql
    )
    site_permissions_index = next(
        index for index, sql in enumerate(conn.executed)
        if "CREATE TABLE IF NOT EXISTS site_permissions" in sql
    )
    site_permissions_sql = conn.executed[site_permissions_index]

    assert managed_sites_index < site_permissions_index
    assert "REFERENCES admin_users(id) ON DELETE CASCADE" in site_permissions_sql
    assert "REFERENCES managed_sites(id) ON DELETE CASCADE" in site_permissions_sql


def test_postgres_migration_baseline_orders_auth_lottery_sites_before_dependent_tables(monkeypatch):
    from database.versioned_migrations import _baseline_schema

    calls: list[str] = []

    class _BootstrapConnection:
        engine = "postgres"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("database.bootstrap.seed_system_config_defaults", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("database.bootstrap.ensure_system_config_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("database.bootstrap._sync_legacy_image_assets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("database.bootstrap.seed_bootstrap_data", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("database.bootstrap.ensure_indexes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("database.bootstrap.auto_increment_primary_key", lambda *_args, **_kwargs: "id BIGSERIAL PRIMARY KEY")

    for name in (
        "ensure_auth_tables", "ensure_lottery_tables", "ensure_site_tables", "ensure_scheduler_tables",
        "ensure_prediction_tables", "ensure_legacy_asset_tables", "ensure_liubuzhong_table",
        "ensure_site_specific_prediction_tables", "ensure_twcaibawang_prediction_tables", "ensure_audit_tables",
        "ensure_log_tables", "ensure_traffic_tables", "ensure_config_history_tables",
    ):
        monkeypatch.setattr(
            "database.bootstrap." + name,
            lambda *_args, _name=name, **_kwargs: calls.append(_name),
        )

    _baseline_schema(_BootstrapConnection())

    assert calls[:3] == ["ensure_auth_tables", "ensure_lottery_tables", "ensure_site_tables"]


def test_site_id_alignment_migrates_existing_permissions_before_cascade_delete(tmp_path):
    from db import connect
    from database.schema.sites import align_managed_site_ids_with_web_ids

    db_path = str(tmp_path / "site-id-permissions.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE admin_users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE managed_sites (id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL, "
            "domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL, blueprint_name TEXT, "
            "announcement TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE site_permissions (user_id INTEGER NOT NULL, site_id INTEGER NOT NULL, "
            "can_view INTEGER NOT NULL, can_manage INTEGER NOT NULL, can_generate INTEGER NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (user_id, site_id), "
            "FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE CASCADE, "
            "FOREIGN KEY (site_id) REFERENCES managed_sites(id) ON DELETE CASCADE)"
        )
        conn.execute("INSERT INTO admin_users (id, username) VALUES (1, 'operator')")
        conn.execute(
            "INSERT INTO managed_sites (id, web_id, name, enabled, created_at, updated_at) "
            "VALUES (9, 4, 'site', 1, '2026-01-01', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO site_permissions (user_id, site_id, can_view, can_manage, can_generate, created_at, updated_at) "
            "VALUES (1, 9, 1, 0, 1, '2026-01-01', '2026-01-01')"
        )

        align_managed_site_ids_with_web_ids(conn)

        permission = conn.execute(
            "SELECT site_id, can_view, can_generate FROM site_permissions WHERE user_id = 1"
        ).fetchone()
        assert dict(permission) == {"site_id": 4, "can_view": 1, "can_generate": 1}
