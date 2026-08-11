from __future__ import annotations

from database.health import collect_database_health


def test_database_health_reports_both_roles_without_exposing_targets(monkeypatch):
    monkeypatch.setattr("database.health._probe_target", lambda _target: None)
    monkeypatch.setattr("database.health._collect_operational_metrics", lambda _target: {
        "available": True,
        "idle_in_transaction": {"count": 0, "longest_seconds": 0},
        "lock_waits": {"count": 0, "longest_seconds": 0},
        "publication_outbox_unpublished": 0,
    })

    result = collect_database_health(
        "postgresql://writer/secret", "postgresql://reader/secret", include_operational=True,
    )

    assert result == {
        "ok": True,
        "database": {
            "write": {"ok": True},
            "read": {"ok": True},
        },
        "operational": {
            "available": True,
            "idle_in_transaction": {"count": 0, "longest_seconds": 0},
            "lock_waits": {"count": 0, "longest_seconds": 0},
            "publication_outbox_unpublished": 0,
        },
    }
    assert "secret" not in repr(result)


def test_database_health_marks_a_failed_role_and_redacts_exception_text(monkeypatch):
    def fail_reader(target):
        if "reader" in target:
            raise RuntimeError(f"connection failed: {target}")

    monkeypatch.setattr("database.health._probe_target", fail_reader)
    monkeypatch.setattr("database.health._collect_operational_metrics", lambda _target: {"available": True})

    result = collect_database_health(
        "postgresql://writer/secret", "postgresql://reader/secret", include_operational=True,
    )

    assert result["ok"] is False
    assert result["database"]["write"] == {"ok": True}
    assert result["database"]["read"] == {
        "ok": False,
        "error": "dependency unavailable",
    }
    assert "postgresql://" not in result["database"]["read"]["error"]


def test_default_database_health_skips_expensive_operational_queries(monkeypatch):
    monkeypatch.setattr("database.health._probe_target", lambda _target: None)
    monkeypatch.setattr(
        "database.health._collect_operational_metrics",
        lambda _target: (_ for _ in ()).throw(AssertionError("must not query metrics")),
    )

    result = collect_database_health("postgresql://writer/secret", "postgresql://reader/secret")

    assert "operational" not in result


def test_database_operational_metrics_report_transactions_locks_and_outbox(monkeypatch):
    from database.health import _collect_operational_metrics

    executed: list[str] = []

    class Cursor:
        def execute(self, query):
            executed.append(query)

        def fetchone(self):
            if "pg_stat_activity" in executed[-1]:
                return (2, 321.8, 3, 44.9)
            return (5,)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr("database.health.psycopg.connect", lambda *_args, **_kwargs: Connection())

    assert _collect_operational_metrics("postgresql://writer/secret") == {
        "available": True,
        "idle_in_transaction": {"count": 2, "longest_seconds": 321},
        "lock_waits": {"count": 3, "longest_seconds": 44},
        "publication_outbox_unpublished": 5,
    }
    assert "pg_stat_activity" in executed[1]
    assert "publication_outbox" in executed[2]


def test_probe_uses_a_dedicated_short_timeout_connection(monkeypatch):
    captured = {}

    class Cursor:
        def execute(self, query):
            captured.setdefault("queries", []).append(query)

        def fetchone(self):
            return (1,)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            captured["closed"] = True

    def fake_connect(target, *, connect_timeout):
        captured.update(
            {
                "target": target,
                "connect_timeout": connect_timeout,
            }
        )
        return Connection()

    monkeypatch.setattr("database.health.psycopg.connect", fake_connect)

    from database.health import _probe_target

    _probe_target("postgresql://writer/secret")

    assert captured == {
        "target": "postgresql://writer/secret",
        "connect_timeout": 2,
        "queries": ["SET LOCAL statement_timeout = 2000", "SELECT 1"],
        "closed": True,
    }


def test_operational_probe_uses_transaction_local_timeout_for_pgbouncer(monkeypatch):
    captured: list[str] = []

    class Cursor:
        def execute(self, query):
            captured.append(query)

        def fetchone(self):
            return (0, 0, 0, 0) if "pg_stat_activity" in captured[-1] else (0,)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr(
        "database.health.psycopg.connect",
        lambda _target, *, connect_timeout: Connection(),
    )

    from database.health import _collect_operational_metrics

    _collect_operational_metrics("postgresql://writer/secret")

    assert captured[0] == "SET LOCAL statement_timeout = 2000"
