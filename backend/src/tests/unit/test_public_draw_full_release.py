"""Public Taiwan history uses the same immutable 25-second release clock as live draws."""

from datetime import datetime, timedelta

import pytest

from core.time_utils import BEIJING_TZ
from db import connect
import public.api as public_api
import public.draw_reveal as draw_reveal
from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json
from tests.unit.test_public_draw_history_delay import _setup_db
from tests.unit.test_latest_draw_reveal_slice import _Snapshots


START = datetime(2026, 8, 19, 22, 32, 0, tzinfo=BEIJING_TZ)


def _row(**changes):
    return {
        "lottery_type_id": 3, "year": 2026, "term": 100,
        "is_opened": 1, "draw_time": "2026-08-19 22:32:00",
        "opened_at": "2026-08-19 22:32:00", "numbers": "08,09,10,11,12,13,14",
        **changes,
    }


def _live(**changes):
    return {
        "current_issue": "2026100", "draw_time": "2026-08-19 22:32:00",
        "reveal_start": "2026-08-19 22:32:00",
        "result_balls": [{"value": str(i)} for i in range(8, 14)],
        "special_ball": {"value": "14"}, **changes,
    }


def _history(db_path, monkeypatch, *, seconds=1, delay=0):
    monkeypatch.setattr(public_api, "beijing_now", lambda: START + timedelta(seconds=seconds))
    monkeypatch.setattr("runtime_config.get_config", lambda *_: delay)
    return public_api.get_draw_history(db_path, 3, 2026)


@pytest.mark.parametrize("seconds,visible", [(0, False), (1, False), (149.999, False), (150, True)])
def test_history_zero_delay_still_waits_for_the_seventh_ball(tmp_path, monkeypatch, seconds, visible):
    payload = _history(_setup_db(tmp_path), monkeypatch, seconds=seconds)
    assert ("100" in [item["issue"] for item in payload["items"]]) is visible


def test_history_old_planned_time_does_not_bypass_recent_opened_at(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET draw_time = ?, opened_at = ? WHERE term = 100",
                     ("2026-08-19 22:20:00", "2026-08-19 22:32:00"))
        conn.commit()
    payload = _history(db_path, monkeypatch, delay=8)
    assert [item["issue"] for item in payload["items"]] == ["99"]


@pytest.mark.parametrize("opened_at", ["invalid", "2026-08-19", "2026-8-19 2:3:4", "2026-02-30 22:32:00"])
def test_history_invalid_nonempty_opened_at_cannot_use_an_old_draw_time(tmp_path, monkeypatch, opened_at):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET opened_at = ? WHERE term = 99", (opened_at,))
        conn.commit()
    assert [item["issue"] for item in _history(db_path, monkeypatch, seconds=600)["items"]] == ["100"]


@pytest.mark.parametrize("draw_time", ["2026-8-19 21:0:0", "invalid", "2026-08-20 22:32:00"])
def test_history_bad_or_future_draw_anchor_never_exposes_numbers(tmp_path, monkeypatch, draw_time):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET draw_time = ? WHERE term = 99", (draw_time,))
        conn.commit()
    assert "99" not in [item["issue"] for item in _history(db_path, monkeypatch, seconds=600)["items"]]


def test_history_year_list_uses_the_same_full_release_gate(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM lottery_draws WHERE term = 99")
        conn.commit()
    assert _history(db_path, monkeypatch)["years"] == []


def test_history_adds_clock_metadata_from_the_effective_anchor(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET opened_at = '2026-08-19 22:32:05' WHERE term = 100")
        conn.commit()
    payload = _history(db_path, monkeypatch, seconds=155)
    item = next(item for item in payload["items"] if item["issue"] == "100")
    assert item["draw_time"] == "2026-08-19 22:32:00"
    assert item["reveal_start"] == "2026-08-19 22:32:05"
    assert payload["server_now"] == int((START + timedelta(seconds=155)).timestamp())


@pytest.mark.parametrize("seconds,want", [(149.999, False), (150, True)])
def test_shared_full_release_predicate_matches_the_live_seventh_ball(seconds, want):
    predicate = getattr(draw_reveal, "is_full_draw_released", None)
    assert callable(predicate), "public response surfaces need one common full-release predicate"
    assert predicate(_row(), lottery_type_id=3, now=START + timedelta(seconds=seconds)) is want


@pytest.mark.parametrize("changes", [
    {"is_opened": 0}, {"is_opened": "0"}, {"is_opened": None},
    {"draw_time": "invalid"}, {"opened_at": "invalid"},
    {"numbers": "08,09,,11,12,13,14"}, {"numbers": "08,09,10,11,12,13"},
    {"numbers": "08,09,10,11,12,13,14,15"},
])
def test_shared_full_release_requires_authoritative_complete_valid_draw(changes):
    predicate = getattr(draw_reveal, "is_full_draw_released", None)
    assert callable(predicate)
    assert predicate(_row(**changes), lottery_type_id=3, now=START + timedelta(seconds=600)) is False


@pytest.mark.parametrize("interval", [0, 1, 5, 24, 25, 100])
def test_taiwan_callers_cannot_change_the_fixed_twenty_five_second_release(interval):
    result = draw_reveal.apply_reveal_slice(_live(), lottery_type_id=3, now=START + timedelta(seconds=25), interval_seconds=interval)
    assert result["revealed_count"] == 2
    assert result["reveal_interval_seconds"] == 25


@pytest.mark.parametrize("issue", [None, "", "  ", "invalid", True])
def test_live_payload_without_a_valid_issue_cannot_open_even_with_old_anchors(issue):
    result = draw_reveal.apply_reveal_slice(_live(current_issue=issue), lottery_type_id=3, now=START + timedelta(seconds=600))
    assert result["revealed_count"] == 0
    assert result["special_ball"] is None


@pytest.mark.parametrize("planned", ["invalid", "", None, "2026-02-30 22:32:00"])
def test_real_latest_draw_rebuild_rejects_malformed_planned_anchor(tmp_path, monkeypatch, planned):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET draw_time = ?, opened_at = '2026-08-19 22:32:00' WHERE term = 100", (planned,))
        conn.commit()
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    ctx.handler.server.write_db_path = db_path
    monkeypatch.setattr(draw_reveal, "beijing_now", lambda: START + timedelta(seconds=150))
    public_routes.latest_draw(ctx)
    result = response_json(ctx)
    assert result["current_issue"] == "2026100"
    assert result["revealed_count"] == 0
    assert result["result_balls"] == []
    assert result["special_ball"] is None


@pytest.mark.parametrize("route", ["latest-draw", "site-page", "next-draw-deadline"])
def test_live_public_routes_disallow_http_response_caching(monkeypatch, route):
    ctx = make_ctx(f"/api/public/{route}?lottery_type=3")
    monkeypatch.setattr(public_routes, "get_public_latest_draw", lambda *_: _live())
    monkeypatch.setattr(public_routes, "get_public_site_page_data", lambda *_, **__: {"site": {"id": 1}, "draw": _live(), "modules": []})
    monkeypatch.setattr(public_routes, "get_public_next_draw_deadline", lambda *_: {"current_issue": "2026100", "next_time": 1})
    getattr(public_routes, route.replace("-", "_"))(ctx)
    assert dict(ctx.handler.response_headers).get("Cache-Control") == "no-store"


def test_deadline_response_exposes_a_numeric_authoritative_server_clock(monkeypatch):
    ctx = make_ctx("/api/public/next-draw-deadline?lottery_type=3")
    monkeypatch.setattr(public_routes, "get_public_next_draw_deadline", lambda *_: {"current_issue": "2026100", "next_time": 1})
    monkeypatch.setattr(public_routes.time, "time", lambda: 1787149921)
    public_routes.next_draw_deadline(ctx)
    assert response_json(ctx)["server_now"] == 1787149921


def test_next_deadline_current_draw_time_is_planned_time_not_opened_at(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE lottery_draws SET opened_at = '2026-08-19 22:34:00' WHERE term = 100")
        conn.commit()
    monkeypatch.setattr(public_api, "get_effective_next_draw_payload", lambda *_: {"current_issue": "2026100", "next_issue": "2026101", "next_time": 1})
    monkeypatch.setattr(public_api, "resolve_next_time_ms", lambda *_, **__: 1)
    assert public_api.get_public_next_draw_deadline(db_path, 3)["current_draw_time"] == 1787149920


def test_next_deadline_matches_the_padded_taiwan_issue_before_term_one_hundred(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM lottery_draws WHERE term = 100")
        conn.commit()
    monkeypatch.setattr(public_api, "get_effective_next_draw_payload", lambda *_: {"current_issue": "2026099", "next_issue": "2026100", "next_time": 1})
    monkeypatch.setattr(public_api, "resolve_next_time_ms", lambda *_, **__: 1)
    assert public_api.get_public_next_draw_deadline(db_path, 3)["current_draw_time"] == 1787144400


@pytest.mark.parametrize("outlet", ["cache", "site-page"])
def test_taiwan_cached_old_dates_and_wrong_balls_are_replaced_by_primary_truth(tmp_path, monkeypatch, outlet):
    db_path = _setup_db(tmp_path)
    cached = _live(draw_time="2026-08-18 22:32:00", reveal_start="2026-08-18 22:32:00",
                   result_balls=[{"value": "41"}] * 6, special_ball={"value": "42"})
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    ctx.handler.server.write_db_path = db_path
    ctx.handler.server.read_db_path = "must-not-read-a-replica"
    monkeypatch.setattr(draw_reveal, "beijing_now", lambda: START + timedelta(seconds=1))
    if outlet == "cache":
        ctx.state["public_draw_snapshots"] = _Snapshots(latest=cached)
        public_routes.latest_draw(ctx)
        result = response_json(ctx)
    else:
        public_routes._send_site_page(ctx, {"site": {"id": 1}, "draw": cached, "modules": []}, 3)
        result = response_json(ctx)["draw"]
    assert result["current_issue"] == "2026100"
    assert result["revealed_count"] == 1
    assert [ball["value"] for ball in result["result_balls"]] == ["08"]
    assert result["special_ball"] is None
    assert cached["special_ball"]["value"] == "42"
    assert cached["draw_time"] == "2026-08-18 22:32:00"


def test_taiwan_stale_cached_issue_is_not_used_to_label_another_draw(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    ctx.handler.server.write_db_path = db_path
    ctx.state["public_draw_snapshots"] = _Snapshots(latest=_live(current_issue="2026099"))
    monkeypatch.setattr(draw_reveal, "beijing_now", lambda: START + timedelta(seconds=1))
    public_routes.latest_draw(ctx)
    result = response_json(ctx)
    assert result["current_issue"] == "2026100"
    assert [ball["value"] for ball in result["result_balls"]] == ["08"]


def test_taiwan_cache_cannot_open_a_draw_that_has_no_authoritative_row(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("DELETE FROM lottery_draws")
        conn.commit()
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    ctx.handler.server.write_db_path = db_path
    ctx.state["public_draw_snapshots"] = _Snapshots(latest=_live())
    monkeypatch.setattr(draw_reveal, "beijing_now", lambda: START + timedelta(seconds=600))
    public_routes.latest_draw(ctx)
    result = response_json(ctx)
    assert result["result_balls"] == []
    assert result["special_ball"] is None


def test_site_page_rechecks_cached_module_actual_results_against_primary_draw(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        conn.execute("ALTER TABLE lottery_draws ADD COLUMN next_term INTEGER")
        conn.commit()
    history = {"year": "2026", "term": "100", "issue": "2026100", "prediction_text": "候选42",
               "result_text": "马14", "is_opened": True, "is_correct": True,
               "raw": {"year": "2026", "term": "100", "type": 3, "res_code": "08,09,10,11,12,13,14", "special_number": "14"}}
    payload = {"site": {"id": 1, "lottery_type_id": 3}, "draw": _live(), "modules": [{"history": [history]}]}
    ctx = make_ctx("/api/public/site-page?lottery_type=3")
    ctx.handler.server.write_db_path = db_path
    ctx.handler.server.read_db_path = "must-not-read-a-replica"
    monkeypatch.setattr(draw_reveal, "beijing_now", lambda: START + timedelta(seconds=1))
    monkeypatch.setattr("helpers.beijing_now", lambda: START + timedelta(seconds=1))
    public_routes._send_site_page(ctx, payload, 3)
    result = response_json(ctx)["modules"][0]["history"][0]
    assert result["result_text"] == "待开奖"
    assert result["is_opened"] is False
    assert result["is_correct"] is None
    assert result["raw"]["res_code"] == ""
    assert result["raw"]["special_number"] == ""
    assert result["prediction_text"] == "候选42"
    assert history["raw"]["special_number"] == "14"


@pytest.mark.parametrize("seconds,count", [(24.999, 1), (25, 2), (149.999, 6), (150, 7)])
def test_live_release_millisecond_clock_keeps_strict_boundaries(seconds, count):
    result = draw_reveal.apply_reveal_slice(_live(), lottery_type_id=3, now=START + timedelta(seconds=seconds))
    assert result["revealed_count"] == count
    assert result["server_now_ms"] == 1787149920000 + round(seconds * 1000)
    assert result["server_now"] == result["server_now_ms"] // 1000


def test_history_clock_preserves_milliseconds_without_a_second_read(tmp_path, monkeypatch):
    result = _history(_setup_db(tmp_path), monkeypatch, seconds=600.125)
    assert result["server_now_ms"] == 1787150520125
    assert result["server_now"] == 1787150520


def test_deadline_clock_preserves_milliseconds_from_the_same_time_sample(monkeypatch):
    ctx = make_ctx("/api/public/next-draw-deadline?lottery_type=3")
    monkeypatch.setattr(public_routes, "get_public_next_draw_deadline", lambda *_: {"current_issue": "2026100", "next_time": 1})
    monkeypatch.setattr(public_routes.time, "time", lambda: 1787149921.125)
    public_routes.next_draw_deadline(ctx)
    result = response_json(ctx)
    assert result["server_now_ms"] == 1787149921125
    assert result["server_now"] == 1787149921
    assert result["server_time"] == "1787149921"
