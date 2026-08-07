from __future__ import annotations

from routes import system_routes
from tests.helpers.api_contract import make_ctx, response_json


def _make_system_ctx(path: str):
    ctx = make_ctx(path)
    ctx.state["detect_database_engine"] = lambda db_path: "postgres"
    ctx.state["database_summary"] = lambda db_path: {"tables": 12, "engine": "postgres"}
    ctx.state["scheduler_worker_health"] = lambda db_path: {
        "status": "healthy",
        "active": True,
        "holder_id": "test-worker",
    }
    ctx.state["lottery_draw_health"] = lambda db_path: {
        "status": "healthy",
        "stale_lottery_type_ids": [],
        "lotteries": [],
    }
    ctx.state["dependency_health"] = lambda _write_target, _read_target: {
        "ok": True,
        "database": {
            "write": {"ok": True},
            "read": {"ok": True},
        },
    }
    return ctx


def test_health_route_contract():
    ctx = _make_system_ctx("/health")

    system_routes.health(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"status": "ok", "engine": "postgres"}


def test_api_health_route_contract():
    ctx = _make_system_ctx("/api/health")

    system_routes.api_health(ctx)

    payload = response_json(ctx)
    assert ctx.handler.response_status == 200
    assert payload["ok"] is True
    assert payload["summary"] == {"tables": 12, "engine": "postgres"}
    assert payload["scheduler_worker"] == {
        "status": "healthy",
        "active": True,
        "holder_id": "test-worker",
    }
    assert payload["draws"] == {
        "status": "healthy",
        "stale_lottery_type_ids": [],
        "lotteries": [],
    }


def test_liveness_does_not_call_dependency_health():
    ctx = _make_system_ctx("/health/live")
    ctx.state["dependency_health"] = lambda *_args: (_ for _ in ()).throw(AssertionError())

    system_routes.liveness(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True, "status": "alive"}


def test_readiness_stays_available_when_read_replica_is_down():
    ctx = _make_system_ctx("/health/ready")
    ctx.state["dependency_health"] = lambda *_args: {
        "ok": False,
        "database": {
            "write": {"ok": True},
            "read": {"ok": False, "error": "dependency unavailable"},
        },
    }

    system_routes.readiness(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx)["ok"] is False


def test_readiness_returns_503_when_the_write_database_is_down():
    ctx = _make_system_ctx("/health/ready")
    ctx.state["dependency_health"] = lambda *_args: {
        "ok": False,
        "database": {
            "write": {"ok": False, "error": "dependency unavailable"},
            "read": {"ok": True},
        },
    }

    system_routes.readiness(ctx)

    assert ctx.handler.response_status == 503


def test_dependency_health_returns_role_status_without_targets():
    ctx = _make_system_ctx("/health/dependencies")

    system_routes.dependencies(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx)["database"]["write"] == {"ok": True}
