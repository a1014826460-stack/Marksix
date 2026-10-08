from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest

from db import connect
from routes import admin_dashboard_routes, admin_draw_routes, admin_payload_routes
from tests.helpers.api_contract import make_ctx, response_json
from tests.unit.test_public_draw_full_release import START
from tests.unit.test_public_draw_history_delay import _setup_db as _setup_history_db


def _setup_db(tmp_path):
    db_path = _setup_history_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("ALTER TABLE lottery_draws ADD COLUMN next_term INTEGER")
        conn.commit()
    return db_path


@pytest.mark.parametrize("operation", ["list", "create", "update", "autofill"])
@pytest.mark.parametrize("seconds", [-1, 0, 149])
def test_admin_can_read_future_draw_numbers_only_before_plan(tmp_path, monkeypatch, operation, seconds):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START + timedelta(seconds=seconds))
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET is_opened=0, opened_at=NULL WHERE term=100")
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
    method = "GET" if operation == "list" else "PATCH" if operation == "update" else "POST"
    ctx = make_ctx("/api/admin/draws/2" if operation == "update" else "/api/admin/draws", method=method)
    ctx.handler.server.db_path = db_path
    ctx.state["current_user"] = {"role": "admin", "username": "operator"}
    with patch.object(admin_draw_routes, "list_draws", return_value={"draws": [row], "total": 1}), \
         patch.object(admin_draw_routes, "save_draw", return_value=row), \
         patch.object(admin_draw_routes, "autofill_taiwan_future_draws", return_value={"created": [
             {key: row[key] for key in ("year", "term", "draw_time", "numbers")}
         ]}):
        getattr(admin_draw_routes, {"list": "list_draw_routes", "create": "create_draw",
            "update": "draw_detail", "autofill": "autofill_future_draws"}[operation])(ctx)
    response = response_json(ctx)
    output = response["draws"][0] if operation == "list" else response["data"]["created"][0] if operation == "autofill" else response["draw"]
    assert output["numbers"] == (row["numbers"] if seconds < 0 else "")
    assert output["numbers_restricted"] is (seconds >= 0)
    assert ("Cache-Control", "no-store") in ctx.handler.response_headers
    assert row["numbers"] == "08,09,10,11,12,13,14"


@pytest.mark.parametrize("role", [None, "viewer", "admin", "super_admin"])
def test_future_draw_exception_requires_admin_and_never_changes_public_gate(tmp_path, monkeypatch, role):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START - timedelta(seconds=1))
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET is_opened=0, opened_at=NULL WHERE term=100")
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
        assert helpers.apply_public_result_gate(conn, row)["numbers"] == ""
    ctx = make_ctx("/api/admin/draws")
    ctx.handler.server.db_path = db_path
    if role:
        ctx.state["current_user"] = {"role": role}
    with patch.object(admin_draw_routes, "list_draws", return_value={"draws": [row]}):
        admin_draw_routes.list_draw_routes(ctx)
    assert response_json(ctx)["draws"][0]["numbers"] == (row["numbers"] if role in ("admin", "super_admin") else "")


@pytest.mark.parametrize("changes", [
    {"draw_time": ""}, {"draw_time": "2026-02-30 22:32:00"},
    {"year": 2025}, {"term": 0}, {"is_opened": 1},
])
def test_admin_edit_exception_closes_for_invalid_or_opened_draw(tmp_path, monkeypatch, changes):
    import helpers
    from routes.admin_result_response import gate_admin_draw_management_response

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START - timedelta(seconds=1))
    with connect(db_path) as conn:
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
    row.update(is_opened=0, opened_at=None)
    row.update(changes)
    ctx = make_ctx("/api/admin/draws")
    ctx.handler.server.db_path = db_path
    ctx.state["current_user"] = {"role": "admin"}
    assert gate_admin_draw_management_response(ctx, row)["numbers"] == ""


def test_admin_can_save_changed_future_numbers_without_public_release(tmp_path):
    from domains.lottery.service import save_draw
    from tables import ensure_admin_tables
    from helpers import apply_public_result_gate

    db_path = str(tmp_path / "future-admin-edit.sqlite3")
    ensure_admin_tables(db_path)
    original = {"lottery_type_id": 3, "year": 2099, "term": 1, "numbers": "01,02,03,04,05,06,07",
        "draw_time": "2099-01-01 22:32:00", "status": True, "is_opened": False, "next_term": 2}
    created = save_draw(db_path, original)
    result = save_draw(db_path, {**original, "numbers": "08,09,10,11,12,13,14"}, created["id"])
    assert result["numbers"] == "08,09,10,11,12,13,14"
    assert not result["is_opened"]
    with connect(db_path) as conn:
        assert apply_public_result_gate(conn, result)["numbers"] == ""


@pytest.mark.parametrize("operation", ["list", "create", "update", "autofill"])
def test_admin_draw_responses_hide_full_numbers_until_public_release(tmp_path, monkeypatch, operation):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START + timedelta(seconds=1))
    with connect(db_path) as conn:
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
    method = "GET" if operation == "list" else "PATCH" if operation == "update" else "POST"
    route = "/api/admin/draws/2" if operation == "update" else "/api/admin/draws"
    ctx = make_ctx(route, method=method, payload={"numbers": row["numbers"]} if method != "GET" else None)
    ctx.handler.server.db_path = db_path
    with patch.object(admin_draw_routes, "list_draws", return_value={"draws": [row], "total": 1}), \
         patch.object(admin_draw_routes, "save_draw", return_value=row), \
         patch.object(admin_draw_routes, "autofill_taiwan_future_draws", return_value={"created": [
             {key: row[key] for key in ("year", "term", "draw_time", "numbers")}
         ]}):
        getattr(admin_draw_routes, {"list": "list_draw_routes", "create": "create_draw",
            "update": "draw_detail", "autofill": "autofill_future_draws"}[operation])(ctx)
    response = response_json(ctx)
    output = response["draws"][0] if operation == "list" else response["data"]["created"][0] if operation == "autofill" else response["draw"]
    assert output["numbers"] == ""
    assert output["numbers_restricted"] is True
    assert ("Cache-Control", "no-store") in ctx.handler.response_headers
    assert row["numbers"] == "08,09,10,11,12,13,14", "response redaction must not mutate internal results"


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_admin_payload_actual_results_are_hidden_without_erasing_candidates(tmp_path, monkeypatch, method):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START + timedelta(seconds=1))
    row = {"id": 12, "year": 2026, "term": 100, "type": 3,
        "content": "candidate text", "code": "01,02", "res_code": "14", "res_sx": "马"}
    ctx = make_ctx("/api/admin/sites/7/mode-payload/mode_payload_43" + ("/12" if method == "PATCH" else ""),
        method=method, payload={"content": "candidate text"} if method == "PATCH" else None)
    ctx.handler.server.db_path = db_path
    site = type("Site", (), {"site_id": 7, "web_id": 6, "lottery_type_id": 3})()
    with patch.object(admin_payload_routes, "resolve_site_context", return_value=site), \
         patch.object(admin_payload_routes, "validate_web_matches_site"), \
         patch.object(admin_payload_routes, "ensure_mode_payload_row_belongs_to_site"), \
         patch.object(admin_payload_routes, "list_mode_payload_rows", return_value={"rows": [row]}), \
         patch.object(admin_payload_routes, "update_mode_payload_row", return_value={"row": row}):
        admin_payload_routes.site_payload_detail(ctx)
    response = response_json(ctx)
    output = response["rows"][0] if method == "GET" else response["row"]
    assert output["res_code"] == output["res_sx"] == ""
    assert output["result_restricted"] is True
    assert output["content"] == "candidate text" and output["code"] == "01,02"
    assert ("Cache-Control", "no-store") in ctx.handler.response_headers
    assert row["res_code"] == "14"


def test_admin_service_omitted_numbers_preserve_hidden_existing_value(tmp_path):
    from domains.lottery.service import save_draw
    from tables import ensure_admin_tables

    db_path = str(tmp_path / "preserve-hidden-numbers.sqlite3")
    ensure_admin_tables(db_path)
    original = {"lottery_type_id": 3, "year": 2099, "term": 1, "numbers": "01,02,03,04,05,06,07",
        "draw_time": "2099-01-01 22:32:00", "status": True, "is_opened": False, "next_term": 2}
    created = save_draw(db_path, original)
    update = {key: value for key, value in original.items() if key != "numbers"}
    update["status"] = False
    result = save_draw(db_path, update, created["id"])
    assert result["numbers"] == original["numbers"]
    assert result["status"] is False
    with pytest.raises(ValueError, match="开奖号码不能为空"):
        save_draw(db_path, {**update, "numbers": ""}, created["id"])


@pytest.mark.parametrize("seconds,hidden", [(149, True), (150, False)])
def test_dashboard_uses_the_same_complete_release_gate(tmp_path, monkeypatch, seconds, hidden):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START + timedelta(seconds=seconds))
    with connect(db_path) as conn:
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
    ctx = make_ctx("/api/admin/dashboard")
    ctx.handler.server.db_path = db_path
    with patch.object(admin_dashboard_routes, "get_dashboard_overview", return_value={"today_draws": [row]}):
        admin_dashboard_routes.overview(ctx)
    output = response_json(ctx)["today_draws"][0]
    assert output["numbers"] == ("" if hidden else "08,09,10,11,12,13,14")
    assert output.get("numbers_restricted", False) is hidden
    assert ("Cache-Control", "no-store") in ctx.handler.response_headers


def test_admin_payload_without_period_identity_cannot_leak_actual_results():
    row = {"id": 12, "content": "candidate", "code": "01,02", "res_code": "14", "res_sx": "马"}
    ctx = make_ctx("/api/admin/sites/7/mode-payload/mode_payload_43")
    site = type("Site", (), {"site_id": 7, "web_id": 6, "lottery_type_id": 3})()
    with patch.object(admin_payload_routes, "resolve_site_context", return_value=site), \
         patch.object(admin_payload_routes, "validate_web_matches_site"), \
         patch.object(admin_payload_routes, "list_mode_payload_rows", return_value={"rows": [row]}):
        admin_payload_routes.site_payload_detail(ctx)
    output = response_json(ctx)["rows"][0]
    assert output["res_code"] == output["res_sx"] == ""
    assert output["result_restricted"] is True
    assert output["content"] == "candidate" and output["code"] == "01,02"


def test_retry_task_response_hides_nested_unreleased_results(tmp_path, monkeypatch):
    import helpers

    db_path = _setup_db(tmp_path)
    monkeypatch.setattr(helpers, "beijing_now", lambda: START + timedelta(seconds=1))
    with connect(db_path) as conn:
        row = dict(conn.execute("SELECT * FROM lottery_draws WHERE term=100").fetchone())
    ctx = make_ctx("/api/admin/dashboard/scheduler-tasks/42/retry", method="POST", payload={})
    ctx.handler.server.db_path = db_path
    with patch.object(admin_dashboard_routes, "retry_failed_scheduler_task", return_value={"id": 42, "result": row}):
        admin_dashboard_routes.retry_scheduler_task(ctx)
    assert response_json(ctx)["task"]["result"]["numbers"] == ""
