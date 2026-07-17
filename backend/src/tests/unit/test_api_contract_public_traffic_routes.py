from __future__ import annotations

from unittest.mock import patch

from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json


def test_public_traffic_events_records_body_and_request_metadata():
    ctx = make_ctx(
        "/api/public/traffic-events",
        method="POST",
        payload={
            "site_key": "twjinniu",
            "event_type": "site_page_view",
            "visitor_id": "visitor-1",
            "path": "/twjinniu",
        },
    )
    ctx.handler.headers["User-Agent"] = "pytest-agent"
    payload = {"ok": True, "id": 10, "site_key": "twjinniu"}

    with patch(
        "routes.public_routes.record_traffic_event",
        return_value=payload,
    ) as record:
        public_routes.traffic_events(ctx)

    record.assert_called_once_with(
        ctx.db_path,
        {
            "site_key": "twjinniu",
            "event_type": "site_page_view",
            "visitor_id": "visitor-1",
            "path": "/twjinniu",
        },
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload
