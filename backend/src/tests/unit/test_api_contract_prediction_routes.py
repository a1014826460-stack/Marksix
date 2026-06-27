from __future__ import annotations

import json
from unittest.mock import patch

from admin.prediction import build_prediction_api_response
from routes import admin_prediction_routes, admin_site_routes
from tests.helpers.api_contract import make_ctx, response_json


def _raw_prediction_result() -> dict:
    return {
        "mode": {
            "key": "title_251",
            "title": "九肖二",
            "default_modes_id": 251,
            "default_table": "mode_payload_251",
            "resolved_labels": ["鼠", "牛"],
        },
        "source": {
            "db_path": "postgresql://example",
            "table": "mode_payload_251",
            "source_modes_id": 251,
            "source_table_title": "九肖二",
            "history_count": 12,
        },
        "input": {
            "latest_term": "2026188",
            "latest_outcome": "鼠",
        },
        "prediction": {
            "labels": ["鼠", "牛"],
            "content": {"text": "鼠牛"},
            "content_json": "{\"text\":\"鼠牛\"}",
        },
        "backtest": {"hit_rate": 0.65},
        "explanation": ["sample"],
        "warning": "",
    }


def test_prediction_api_response_contract_keeps_public_shape():
    raw_result = _raw_prediction_result()
    payload = build_prediction_api_response(
        mechanism_key="title_251",
        request_payload={
            "res_code": "01,02,03,04,05,06,07",
            "content": "sample",
            "source_table": "mode_payload_251",
            "target_hit_rate": 0.65,
            "lottery_type": "3",
            "year": "2026",
            "term": "188",
            "web": "6",
        },
        raw_result=raw_result,
        safety={"result_visibility": "visible", "reason": "opened"},
    )

    assert list(payload.keys()) == ["ok", "protocol_version", "generated_at", "data", "legacy"]
    assert payload["ok"] is True
    assert payload["protocol_version"] == 1
    assert list(payload["data"].keys()) == [
        "mechanism",
        "source",
        "request",
        "context",
        "prediction",
        "backtest",
        "explanation",
        "warning",
    ]
    assert payload["data"]["mechanism"] == {
        "key": "title_251",
        "title": "九肖二",
        "default_modes_id": 251,
        "default_table": "mode_payload_251",
        "resolved_labels": ["鼠", "牛"],
    }
    assert payload["data"]["request"] == {
        "res_code": "01,02,03,04,05,06,07",
        "content": "sample",
        "source_table": "mode_payload_251",
        "target_hit_rate": 0.65,
        "lottery_type": "3",
        "year": "2026",
        "term": "188",
        "web": "6",
    }
    assert payload["data"]["context"]["draw"] == {"result_visibility": "visible", "reason": "opened"}
    assert payload["data"]["prediction"]["labels"] == ["鼠", "牛"]
    assert payload["data"]["prediction"]["content"] == {"text": "鼠牛"}
    assert payload["data"]["prediction"]["display_text"] == json.dumps(raw_result["prediction"]["content"], ensure_ascii=False)
    assert payload["legacy"] == _raw_prediction_result()


def test_prediction_api_response_contract_keeps_hidden_draw_context_shape():
    safety = {
        "issue": "2026188",
        "lottery_type": "3",
        "year": "2026",
        "term": "188",
        "lottery_type_id": 3,
        "year_value": 2026,
        "term_value": 188,
        "is_opened": False,
        "reason": "draw_found",
        "result_visibility": "hidden",
    }

    raw_result = _raw_prediction_result()
    payload = build_prediction_api_response(
        mechanism_key="title_251",
        request_payload={
            "res_code": None,
            "content": "sample",
            "source_table": "mode_payload_251",
            "target_hit_rate": 0.65,
            "lottery_type": "3",
            "year": "2026",
            "term": "188",
            "web": "6",
        },
        raw_result=raw_result,
        safety=safety,
    )

    assert list(payload.keys()) == ["ok", "protocol_version", "generated_at", "data", "legacy"]
    assert list(payload["data"].keys()) == [
        "mechanism",
        "source",
        "request",
        "context",
        "prediction",
        "backtest",
        "explanation",
        "warning",
    ]
    assert payload["data"]["request"]["res_code"] is None
    assert payload["data"]["context"]["draw"] == safety
    assert payload["data"]["prediction"]["content"] == raw_result["prediction"]["content"]
    assert payload["data"]["prediction"]["display_text"] == json.dumps(raw_result["prediction"]["content"], ensure_ascii=False)


def test_predict_route_contract_sends_prediction_api_response():
    ctx = make_ctx("/api/predict/title_251?target_hit_rate=0.65", method="GET")
    ctx.state["current_user"] = {"role": "admin", "username": "admin"}
    expected_response = {"ok": True, "protocol_version": 1, "data": {"prediction": {"labels": ["鼠"]}}}

    with patch("routes.admin_prediction_routes.require_generation_access"), \
         patch("routes.admin_prediction_routes.get_prediction_config", return_value="CONFIG"), \
         patch("routes.admin_prediction_routes.get_config", return_value=0.65), \
         patch("routes.admin_prediction_routes.run_prediction", return_value=_raw_prediction_result()) as run_prediction, \
         patch("routes.admin_prediction_routes.build_prediction_api_response", return_value=expected_response) as build_response:
        admin_prediction_routes.run_mechanism_prediction(ctx)

    run_prediction.assert_called_once()
    build_response.assert_called_once()
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == expected_response


def test_site_prediction_modules_route_contract_keeps_service_payload():
    ctx = make_ctx("/api/admin/sites/5/prediction-modules", method="GET")
    payload = {
        "site": {"id": 5, "web_id": 6},
        "modules": [{"id": 10, "mechanism_key": "title_251"}],
        "available_mechanisms": [{"key": "title_251"}],
    }

    with patch("routes.admin_site_routes.parse_site_route_context") as parse_context, \
         patch("routes.admin_site_routes.resolve_site_context"), \
         patch("routes.admin_site_routes.list_site_prediction_modules", return_value=payload):
        parse_context.return_value.parts = ["", "api", "admin", "sites", "5", "prediction-modules"]
        parse_context.return_value.site_id = 5

        admin_site_routes.site_detail(ctx)

    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload
