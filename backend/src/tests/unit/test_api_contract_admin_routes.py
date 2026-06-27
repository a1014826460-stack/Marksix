from __future__ import annotations

from unittest.mock import patch

from routes import admin_draw_routes, admin_lottery_routes, admin_site_routes
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
