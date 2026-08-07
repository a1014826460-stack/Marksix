from __future__ import annotations

from database.health import collect_database_health


def test_database_health_reports_both_roles_without_exposing_targets(monkeypatch):
    monkeypatch.setattr("database.health._probe_target", lambda _target: None)

    result = collect_database_health("postgresql://writer/secret", "postgresql://reader/secret")

    assert result == {
        "ok": True,
        "database": {
            "write": {"ok": True},
            "read": {"ok": True},
        },
    }
    assert "secret" not in repr(result)


def test_database_health_marks_a_failed_role_and_redacts_exception_text(monkeypatch):
    def fail_reader(target):
        if "reader" in target:
            raise RuntimeError(f"connection failed: {target}")

    monkeypatch.setattr("database.health._probe_target", fail_reader)

    result = collect_database_health("postgresql://writer/secret", "postgresql://reader/secret")

    assert result["ok"] is False
    assert result["database"]["write"] == {"ok": True}
    assert result["database"]["read"] == {
        "ok": False,
        "error": "dependency unavailable",
    }
    assert "postgresql://" not in result["database"]["read"]["error"]


def test_probe_uses_a_dedicated_short_timeout_connection(monkeypatch):
    captured = {}

    class Cursor:
        def execute(self, query):
            assert query == "SELECT 1"

        def fetchone(self):
            return (1,)

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            captured["closed"] = True

    def fake_connect(target, *, connect_timeout, options):
        captured.update(
            {
                "target": target,
                "connect_timeout": connect_timeout,
                "options": options,
            }
        )
        return Connection()

    monkeypatch.setattr("database.health.psycopg.connect", fake_connect)

    from database.health import _probe_target

    _probe_target("postgresql://writer/secret")

    assert captured == {
        "target": "postgresql://writer/secret",
        "connect_timeout": 2,
        "options": "-c statement_timeout=2000",
        "closed": True,
    }
