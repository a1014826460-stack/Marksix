from __future__ import annotations

import io
from http import HTTPStatus
from unittest.mock import patch

import pytest

from app_http.request_context import RequestContext
from app_http.response import ResponseWriter
from core.errors import ValidationError
from routes import (
    admin_config_routes,
    admin_draw_routes,
    admin_log_routes,
    admin_lottery_routes_extra,
    admin_number_routes,
    admin_payload_routes,
    public_routes,
)
from tests.helpers.api_contract import Headers, StubHandler, make_ctx


def _header_values(handler: StubHandler, name: str) -> list[str]:
    return [value for key, value in handler.response_headers if key.lower() == name.lower()]


def test_request_context_rejects_json_body_larger_than_one_megabyte():
    handler = StubHandler("/api/auth/login", method="POST", body=b"{}")
    handler.headers["Content-Length"] = str(1024 * 1024 + 1)
    ctx = RequestContext(handler, "POST")

    with pytest.raises(ValidationError, match="请求体过大"):
        ctx.read_json()


def test_response_writer_does_not_grant_unconfigured_cross_origin_access(monkeypatch):
    monkeypatch.delenv("LOTTERY_CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("LOTTERY_PUBLIC_CORS_ALLOWED_ORIGINS", raising=False)
    handler = StubHandler("/api/admin/users")
    handler.headers = Headers({"Origin": "https://untrusted.example"})

    ResponseWriter(handler).send_json({"users": []})

    assert handler.response_status == HTTPStatus.OK
    assert _header_values(handler, "Access-Control-Allow-Origin") == []


def test_response_writer_allows_only_explicitly_configured_origin(monkeypatch):
    monkeypatch.setenv("LOTTERY_CORS_ALLOWED_ORIGINS", "https://admin.example")
    handler = StubHandler("/api/admin/users")
    handler.headers = Headers({"Origin": "https://admin.example"})

    ResponseWriter(handler).send_json({"users": []})

    assert _header_values(handler, "Access-Control-Allow-Origin") == ["https://admin.example"]
    assert _header_values(handler, "Vary") == ["Origin"]


def test_public_site_page_clamps_history_limit_without_changing_payload_shape():
    handler = StubHandler("/api/public/site-page?history_limit=99999")
    ctx = RequestContext(handler, "GET")
    expected_payload = {"site": {}, "draw": {}, "modules": []}

    with patch("routes.public_routes.get_public_site_page_data", return_value=expected_payload) as get_site_page:
        public_routes.site_page(ctx)

    assert get_site_page.call_args.kwargs["history_limit"] == 50
    assert ctx.handler.response_status == HTTPStatus.OK


def test_bounded_integer_parser_rejects_negative_and_malformed_values():
    from app_http.security import parse_bounded_int

    with pytest.raises(ValidationError, match="limit 必须大于等于 1"):
        parse_bounded_int("-1", default=20, maximum=500, field_name="limit")
    with pytest.raises(ValidationError, match="limit 必须为整数"):
        parse_bounded_int("many", default=20, maximum=500, field_name="limit")


def test_admin_draw_list_clamps_limit_before_database_query():
    ctx = make_ctx("/api/admin/draws?limit=99999&page=2")

    with patch("routes.admin_draw_routes.list_draws", return_value={"draws": [], "total": 0}) as list_draws:
        admin_draw_routes.list_draw_routes(ctx)

    list_draws.assert_called_once_with(ctx.db_path, limit=500, offset=500, lottery_type_id=None)
    assert ctx.handler.response_status == HTTPStatus.OK


def test_admin_number_list_clamps_limit_before_database_query():
    ctx = make_ctx("/api/admin/numbers?limit=99999")

    with patch("routes.admin_number_routes.list_numbers", return_value=[]) as list_numbers:
        admin_number_routes.list_number_routes(ctx)

    list_numbers.assert_called_once_with(ctx.db_path, 500, "", "")
    assert ctx.handler.response_status == HTTPStatus.OK


def test_admin_payload_list_clamps_page_size_before_service_call(monkeypatch):
    ctx = make_ctx("/api/admin/sites/3/mode-payload/mode_payload_470?page=2&page_size=99999")
    current_site = object()
    monkeypatch.setattr(admin_payload_routes, "parse_site_route_context", lambda _ctx: type("SiteRoute", (), {"parts": ctx.path.split("/"), "site_id": 3})())
    monkeypatch.setattr(admin_payload_routes, "resolve_site_context", lambda *_args, **_kwargs: type("Site", (), {"web_id": 4})())
    monkeypatch.setattr(admin_payload_routes, "validate_web_matches_site", lambda *_args, **_kwargs: None)

    with patch("routes.admin_payload_routes.list_mode_payload_rows", return_value={"rows": []}) as list_rows:
        admin_payload_routes.site_payload_detail(ctx)

    assert list_rows.call_args.kwargs["page"] == 2
    assert list_rows.call_args.kwargs["page_size"] == 500
    assert ctx.handler.response_status == HTTPStatus.OK


def test_admin_log_list_clamps_page_and_page_size_before_service_call():
    ctx = make_ctx("/api/admin/logs?page=99999&page_size=99999")

    with patch("domains.logs.service.query_error_logs", return_value={"items": []}) as query_logs:
        admin_log_routes.list_logs(ctx)

    assert query_logs.call_args.kwargs["page"] == 500
    assert query_logs.call_args.kwargs["page_size"] == 500
    assert ctx.handler.response_status == HTTPStatus.OK


def test_fetch_run_list_clamps_limit_before_service_call():
    ctx = make_ctx("/api/admin/fetch-runs?limit=99999")

    with patch("routes.admin_lottery_routes_extra.list_fetch_runs", return_value=[]) as list_runs:
        admin_lottery_routes_extra.fetch_runs(ctx)

    list_runs.assert_called_once_with(ctx.db_path, 500)
    assert ctx.handler.response_status == HTTPStatus.OK
