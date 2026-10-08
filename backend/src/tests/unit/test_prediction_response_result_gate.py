from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace

from db import connect
from routes import admin_prediction_routes, admin_site_routes
from tests.helpers.api_contract import make_ctx, response_json
from tests.unit.test_legacy_taiwan_result_gate import ANCHOR, CODES, gate_db


def raw_prediction():
    return {
        "mode": {"key": "title_251", "title": "九肖二"},
        "source": {"table": "mode_payload_251", "history_count": 12},
        "input": {"res_code": CODES, "latest_term": 282, "latest_outcome": "马07", "latest_year": 2026, "latest_lottery_type_id": 3},
        "prediction": {"labels": ["鼠", "牛"], "content": "鼠牛", "content_json": '"鼠牛"'},
        "backtest": {"historical_content_hit_rate": 0.75, "historical_content_sample_size": 12, "target_hit_rate": 0.65},
    }


def run_route(db_path, raw, query):
    ctx = make_ctx("/api/predict/title_251")
    ctx.handler.server.db_path = db_path
    ctx.query = query
    with patch("routes.admin_prediction_routes.require_generation_access", return_value={"role": "admin"}), patch("routes.admin_prediction_routes.get_prediction_config", return_value=object()), patch("routes.admin_prediction_routes.get_config", return_value=0.65), patch("routes.admin_prediction_routes.run_prediction", return_value=raw), patch("routes.admin_prediction_routes.resolve_prediction_request_safety", return_value=(CODES, {"result_visibility": "visible", "reason": "opened"})):
        admin_prediction_routes.run_mechanism_prediction(ctx)
    return response_json(ctx), ctx.handler


def test_prediction_response_hides_actual_echo_context_and_verdict_before_release(gate_db, monkeypatch):
    import helpers
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=149))
    payload, handler = run_route(gate_db, raw_prediction(), {"lottery_type": ["3"], "year": ["2026"], "term": ["282"]})
    assert payload["data"]["request"]["res_code"] == ""
    assert payload["data"]["context"]["latest_outcome"] == ""
    assert payload["legacy"]["input"]["res_code"] == ""
    assert payload["legacy"]["input"]["latest_outcome"] == ""
    assert payload["data"]["backtest"]["historical_content_hit_rate"] is None
    assert payload["legacy"]["backtest"]["historical_content_hit_rate"] is None
    assert payload["data"]["prediction"]["labels"] == ["鼠", "牛"]
    assert payload["data"]["prediction"]["content"] == "鼠牛"
    assert payload["data"]["backtest"]["target_hit_rate"] == 0.65


def test_prediction_response_does_not_borrow_request_identity_for_latest_history(gate_db, monkeypatch):
    import helpers
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=150))
    raw = raw_prediction()
    del raw["input"]["latest_year"]
    del raw["input"]["latest_lottery_type_id"]
    payload, _ = run_route(gate_db, raw, {"lottery_type": ["1"], "year": ["2026"], "term": ["282"]})
    assert payload["data"]["context"]["latest_outcome"] == ""
    assert payload["legacy"]["input"]["latest_outcome"] == ""


def test_prediction_response_releases_proven_actual_fields_at_150_seconds(gate_db, monkeypatch):
    import helpers
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=150))
    payload, _ = run_route(gate_db, raw_prediction(), {"lottery_type": ["3"], "year": ["2026"], "term": ["282"]})
    assert payload["data"]["request"]["res_code"] == CODES
    assert payload["data"]["context"]["latest_outcome"] == "马07"
    assert payload["data"]["backtest"]["historical_content_hit_rate"] == 0.75


def test_site_module_run_applies_the_same_actual_result_gate(gate_db, monkeypatch):
    import helpers
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=149))
    ctx = make_ctx("/api/admin/sites/5/prediction-modules/run", method="POST", payload={"mechanism_key": "title_251", "res_code": CODES, "year": 2026, "term": 282})
    ctx.handler.server.db_path = gate_db
    route_context = SimpleNamespace(parts=["", "api", "admin", "sites", "5", "prediction-modules", "run"], site_id=5)
    site = SimpleNamespace(lottery_type_id=3, web_id=6, site_id=5)
    with patch("routes.admin_site_routes.parse_site_route_context", return_value=route_context), patch("routes.admin_site_routes.resolve_site_context", return_value=site), patch("domains.sites.permissions.can_access_site", return_value=True), patch("routes.admin_site_routes.require_site_generation_access"), patch("routes.admin_site_routes.validate_web_matches_site"), patch("routes.admin_site_routes.run_site_prediction_module", return_value=raw_prediction()):
        admin_site_routes.site_detail(ctx)
    result = response_json(ctx)
    assert result["input"]["res_code"] == ""
    assert result["input"]["latest_outcome"] == ""
    assert result["prediction"]["labels"] == ["鼠", "牛"]
