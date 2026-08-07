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
