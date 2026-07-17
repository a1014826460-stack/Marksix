from __future__ import annotations

from unittest.mock import patch

from routes import admin_traffic_routes
from tests.helpers.api_contract import make_ctx, response_json


def test_admin_traffic_overview_contract_and_query_mapping():
    ctx = make_ctx(
        "/api/admin/traffic/overview"
        "?date_from=2026-06-28T00:00:00Z&date_to=2026-06-29T00:00:00Z"
    )
    payload = {"summary": {"pv": 5, "uv": 4, "api_compat_hits": 1}}

    with patch(
        "routes.admin_traffic_routes.get_traffic_overview",
        return_value=payload,
    ) as get_overview:
        admin_traffic_routes.overview(ctx)

    get_overview.assert_called_once_with(
        ctx.db_path,
        date_from="2026-06-28T00:00:00Z",
        date_to="2026-06-29T00:00:00Z",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_admin_traffic_sites_contract_and_query_mapping():
    ctx = make_ctx("/api/admin/traffic/sites?date_from=2026-06-28&date_to=2026-06-29")
    payload = {"sites": [{"site_key": "twjinniu", "pv": 4, "uv": 3}]}

    with patch(
        "routes.admin_traffic_routes.get_traffic_sites",
        return_value=payload,
    ) as get_sites:
        admin_traffic_routes.sites(ctx)

    get_sites.assert_called_once_with(
        ctx.db_path,
        date_from="2026-06-28",
        date_to="2026-06-29",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_admin_traffic_timeseries_contract_and_query_mapping():
    ctx = make_ctx("/api/admin/traffic/timeseries?date_from=2026-06-28&date_to=2026-06-29")
    payload = {"items": [{"date": "2026-06-28", "site_key": "twjinniu", "pv": 4}]}

    with patch(
        "routes.admin_traffic_routes.get_traffic_timeseries",
        return_value=payload,
    ) as get_timeseries:
        admin_traffic_routes.timeseries(ctx)

    get_timeseries.assert_called_once_with(
        ctx.db_path,
        date_from="2026-06-28",
        date_to="2026-06-29",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload
