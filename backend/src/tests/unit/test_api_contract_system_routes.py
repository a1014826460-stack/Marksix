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
