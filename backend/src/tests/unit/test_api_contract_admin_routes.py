from __future__ import annotations

from datetime import datetime, timezone
import pytest
from unittest.mock import patch

from routes import (
    admin_backfill_routes,
    admin_draw_routes,
    admin_log_routes,
    admin_lottery_routes,
    admin_site_routes,
)
from app_http.router import Router
from tests.helpers.api_contract import make_ctx, response_json


def test_admin_sites_list_contract():
    ctx = make_ctx("/api/admin/sites")
    sites = [
        {
            "id": 1,
            "name": "台湾站",
            "web_id": 6,
            "status": True,
        }
    ]

    with patch("routes.admin_site_routes.list_sites", return_value=sites):
        admin_site_routes.list_site_routes(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"sites": sites}


def test_admin_lottery_types_list_contract():
    ctx = make_ctx("/api/admin/lottery-types")
    lottery_types = [
        {
            "id": 3,
            "name": "台湾彩",
            "status": True,
            "next_time": "2026-06-27 22:30:00",
        }
    ]

    with patch("routes.admin_lottery_routes.list_lottery_types", return_value=lottery_types):
        admin_lottery_routes.list_types(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"lottery_types": lottery_types}


def test_admin_draws_list_contract_and_query_mapping():
    ctx = make_ctx("/api/admin/draws?page=2&page_size=15&lottery_type_id=3")
    payload = {
        "items": [{"id": 99, "year": 2026, "term": 188}],
        "total": 1,
        "page": 2,
        "page_size": 15,
    }

    with patch("routes.admin_draw_routes.list_draws", return_value=payload) as list_draws:
        admin_draw_routes.list_draw_routes(ctx)

    list_draws.assert_called_once_with(
        ctx.db_path,
        limit=15,
        offset=15,
        lottery_type_id=3,
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_admin_latest_term_contract_and_query_mapping():
    ctx = make_ctx("/api/admin/lottery-draws/latest-term?lottery_type_id=3")
    payload = {"year": 2026, "term": 188, "draw_time": "2026-06-27 22:30:00"}

    with patch("routes.admin_draw_routes.get_latest_opened_draw_term", return_value=payload) as latest_term:
        admin_draw_routes.latest_term(ctx)

    latest_term.assert_called_once_with(ctx.db_path, 3)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_admin_autofill_future_draw_contract():
    ctx = make_ctx("/api/admin/draws/auto-fill-future", "POST", {"count": 8})
    payload = {
        "requested_count": 8,
        "created_count": 8,
        "preserved_existing_count": 1,
        "created": [],
    }

    with patch(
        "routes.admin_draw_routes.autofill_taiwan_future_draws", return_value=payload
    ) as autofill:
        admin_draw_routes.autofill_future_draws(ctx)

    autofill.assert_called_once_with(ctx.db_path, count=8)
    assert ctx.handler.response_status == 201
    assert response_json(ctx) == {"ok": True, "data": payload}


def test_admin_autofill_future_draw_defaults_to_twelve():
    ctx = make_ctx("/api/admin/draws/auto-fill-future", "POST", {})
    with patch("routes.admin_draw_routes.autofill_taiwan_future_draws", return_value={}) as autofill:
        admin_draw_routes.autofill_future_draws(ctx)
    autofill.assert_called_once_with(ctx.db_path, count=12)


def test_admin_autofill_settings_contract_and_actor_mapping():
    read_ctx = make_ctx("/api/admin/draws/auto-fill-future/settings")
    settings = {"enabled": True, "count": 12, "time": "07:45", "timezone": "UTC"}
    status = {"last_run": None, "next_run_at": "2026-07-28T07:45:00+00:00"}
    with patch("routes.admin_draw_routes.get_taiwan_future_autofill_settings", return_value=settings), patch(
        "routes.admin_draw_routes.get_taiwan_future_autofill_schedule_status", return_value=status
    ):
        admin_draw_routes.get_autofill_future_settings(read_ctx)
    assert response_json(read_ctx) == {"ok": True, "data": settings | status}

    write_ctx = make_ctx(
        "/api/admin/draws/auto-fill-future/settings",
        "PUT",
        {"enabled": True, "count": 20, "time": "08:30"},
    )
    write_ctx.state["current_user"] = {"id": 1, "username": "alice", "role": "admin"}
    with patch("routes.admin_draw_routes.save_taiwan_future_autofill_settings", return_value=settings) as save:
        admin_draw_routes.save_autofill_future_settings(write_ctx)
    save.assert_called_once_with(
        write_ctx.db_path,
        {"enabled": True, "count": 20, "time": "08:30"},
        changed_by="alice",
    )
    assert response_json(write_ctx) == {"ok": True, "data": settings}


def test_admin_autofill_future_draw_exact_route_wins_over_draw_detail_prefix():
    router = Router()
    admin_draw_routes.register(router)
    ctx = make_ctx("/api/admin/draws/auto-fill-future", "POST", {"count": 3})
    ctx.state["current_user"] = {"id": 1, "role": "admin"}

    with patch("routes.admin_draw_routes.autofill_taiwan_future_draws", return_value={}) as autofill:
        router.dispatch(ctx)

    autofill.assert_called_once_with(ctx.db_path, count=3)
    assert ctx.handler.response_status == 201


@pytest.mark.parametrize("count", [0, 61, "12", True, 1.0])
def test_admin_autofill_future_draw_rejects_invalid_count(count):
    ctx = make_ctx("/api/admin/draws/auto-fill-future", "POST", {"count": count})
    with patch("routes.admin_draw_routes.autofill_taiwan_future_draws") as autofill:
        with pytest.raises(ValueError, match="1 到 60"):
            admin_draw_routes.autofill_future_draws(ctx)
    autofill.assert_not_called()


def test_admin_backfill_logs_contract_and_query_mapping():
    ctx = make_ctx(
        "/api/admin/backfill-predictions/logs"
        "?lottery_type_id=3&period=2026133&action=generated"
        "&date_from=2026-06-01T00:00:00Z&date_to=2026-06-27T23:59:59Z"
        "&page=2&page_size=15"
    )
    payload = {
        "items": [
            {
                "id": 10,
                "created_at": "2026-06-27T12:00:00+00:00",
                "level": "INFO",
                "message": "期号=2026133 动作=generated",
                "lottery_type_id": 3,
            }
        ],
        "total": 16,
        "page": 2,
        "page_size": 15,
        "total_pages": 2,
    }

    with patch("routes.admin_backfill_routes.query_backfill_logs", return_value=payload) as query_logs:
        admin_backfill_routes.get_backfill_logs(ctx)

    query_logs.assert_called_once_with(
        ctx.db_path,
        lottery_type_id=3,
        period="2026133",
        action="generated",
        date_from="2026-06-01T00:00:00Z",
        date_to="2026-06-27T23:59:59Z",
        page=2,
        page_size=15,
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True, "data": payload}


def test_admin_backfill_predictions_contract_and_body_mapping():
    ctx = make_ctx(
        "/api/admin/backfill-predictions",
        method="POST",
        payload={
            "lottery_type_id": 3,
            "recent_count": 2,
            "table_names": ["mode_payload_43"],
        },
    )
    payload = {
        "lottery_type_id": 3,
        "start_issue": "2026126",
        "end_issue": "2026127",
        "draw_count": 2,
        "total_affected": 5,
        "tables_affected": 1,
        "per_table": [{"table": "mode_payload_43", "updated": 2, "backfilled": 5}],
        "draws": [
            {
                "year": 2026,
                "term": 126,
                "issue": "2026126",
                "numbers": "01,02,03,04,05,06,07",
                "res_sx": "鼠,牛,虎,兔,龙,蛇,马",
                "res_color": "red,blue,green,red,blue,green,red",
                "updated_tables": [{"table": "mode_payload_43", "affected": 5}],
                "total_affected": 5,
            }
        ],
    }

    with patch("routes.admin_backfill_routes.run_backfill_predictions", return_value=payload) as run_backfill:
        admin_backfill_routes.backfill_predictions(ctx)

    run_backfill.assert_called_once_with(
        ctx.db_path,
        lottery_type_id=3,
        start_issue="",
        end_issue="",
        recent_count=2,
        target_tables=["mode_payload_43"],
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"ok": True, "data": payload}


def test_admin_logs_contract_and_query_mapping():
    ctx = make_ctx(
        "/api/admin/logs"
        "?page=3&page_size=25&level=ERROR&module=prediction.backfill"
        "&keyword=boom&date_from=2026-06-01&date_to=2026-06-27"
        "&user_id=7&site_id=4&web_id=6&lottery_type_id=3"
        "&year=2026&term=133&task_type=daily_prediction"
        "&task_key=daily_prediction:2026-06-27&path=/api/predict/foo"
    )
    payload = {
        "items": [{"id": 12, "level": "ERROR", "message": "boom"}],
        "rows": [{"id": 12, "level": "ERROR", "message": "boom"}],
        "total": 1,
        "page": 3,
        "page_size": 25,
        "total_pages": 1,
        "available_levels": ["ERROR"],
        "available_modules": ["prediction.backfill"],
    }

    with patch("domains.logs.service.query_error_logs", return_value=payload) as query_logs:
        admin_log_routes.list_logs(ctx)

    query_logs.assert_called_once_with(
        ctx.db_path,
        page=3,
        page_size=25,
        level="ERROR",
        module="prediction.backfill",
        keyword="boom",
        date_from="2026-06-01",
        date_to="2026-06-27",
        user_id="7",
        site_id="4",
        web_id="6",
        lottery_type_id="3",
        year="2026",
        term="133",
        task_type="daily_prediction",
        task_key="daily_prediction:2026-06-27",
        path="/api/predict/foo",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_admin_log_detail_serializes_postgres_datetime_fields():
    ctx = make_ctx("/api/admin/logs/31096")
    detail = {
        "id": 31096,
        "level": "ERROR",
        "created_at": datetime(2026, 7, 28, 6, 42, 19, tzinfo=timezone.utc),
    }

    with patch("domains.logs.service.get_log_detail", return_value=detail):
        admin_log_routes.log_detail(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx)["created_at"] == "2026-07-28T06:42:19+00:00"


def test_admin_logs_export_contract_and_query_mapping():
    ctx = make_ctx(
        "/api/admin/logs/export"
        "?level=warning&module=app&keyword=timeout"
        "&date_from=2026-06-01&date_to=2026-06-27"
    )
    rows = [
        {
            "id": 21,
            "level": "WARNING",
            "module": "app",
            "message": "timeout",
        }
    ]

    with patch("domains.logs.service.export_error_logs", return_value=rows) as export_logs:
        admin_log_routes.export_logs(ctx)

    export_logs.assert_called_once_with(
        ctx.db_path,
        level="warning",
        module="app",
        keyword="timeout",
        date_from="2026-06-01",
        date_to="2026-06-27",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"rows": rows, "total": 1}
