from datetime import datetime, timedelta

import pytest

import helpers
from core.time_utils import BEIJING_TZ
from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api
from app_http.router import Router
from routes import legacy_routes


ANCHOR = datetime(2026, 10, 8, 21, 22, 0, tzinfo=BEIJING_TZ)
CODES = "01,02,03,04,05,06,07"


@pytest.fixture
def gate_db(tmp_path):
    path = str(tmp_path / "taiwan_result_gate.sqlite3")
    with connect(path) as conn:
        conn.execute("CREATE TABLE fixed_data (sign TEXT, name TEXT, code TEXT)")
        conn.execute("CREATE TABLE lottery_draws (id INTEGER PRIMARY KEY, lottery_type_id INTEGER, year INTEGER, term INTEGER, numbers TEXT, is_opened INTEGER, next_term INTEGER, draw_time TEXT, opened_at TEXT)")
        conn.execute("INSERT INTO lottery_draws VALUES (1, 3, 2026, 282, ?, 1, 283, '2026-10-08 21:00:00', '2026-10-08 21:22:00')", (CODES,))
        conn.execute("CREATE TABLE mode_payload_tables (modes_id INTEGER PRIMARY KEY, table_name TEXT)")
        conn.execute("INSERT INTO mode_payload_tables VALUES (251, 'mode_payload_251')")
        conn.execute("CREATE TABLE mode_payload_251 (year TEXT, term TEXT, web INTEGER, type INTEGER, content TEXT, xiao TEXT, code TEXT, res_code TEXT, res_sx TEXT)")
        conn.execute("INSERT INTO mode_payload_251 VALUES ('2026', '282', 6, 3, '[\"鼠|05,17\"]', '鼠,牛', '01,02', ?, '鼠,牛,虎,兔,龙,蛇,马')", (CODES,))
        conn.commit()
    return path


def source_row(**changes):
    return {"year": "2026", "term": "282", "type": 3, "content": "鼠|05,17", "code": "01,02", "res_code": CODES, "res_sx": "鼠,牛,虎,兔,龙,蛇,马", "res_color": "red,blue,green,red,blue,green,red", "special_number": "07", "numbers": CODES, "result_text": "马07准", "is_correct": True, **changes}


def assert_hidden(row):
    assert row["res_code"] == ""
    assert row["res_sx"] == ""
    assert row["special_number"] == ""
    assert row["numbers"] == ""
    assert row["is_correct"] is None
    assert row["result_text"] == "待开奖"
    assert row["content"] == "鼠|05,17"
    assert row["code"] == "01,02"


@pytest.mark.parametrize("seconds", [0, 149.999])
def test_overlay_requires_full_reveal_even_after_history_delay(gate_db, monkeypatch, seconds):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=seconds))
    monkeypatch.setattr(helpers, "_resolve_history_delay_minutes", lambda conn: 0)
    with connect(gate_db) as conn:
        row = helpers.apply_lottery_draw_overlay(conn, [source_row()])[0]
    assert_hidden(row)
    assert row["draw_is_opened"] is False


def test_overlay_releases_at_150_seconds(gate_db, monkeypatch):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=150))
    monkeypatch.setattr(helpers, "_resolve_history_delay_minutes", lambda conn: 0)
    with connect(gate_db) as conn:
        row = helpers.apply_lottery_draw_overlay(conn, [source_row()])[0]
    assert row["res_code"] == CODES
    assert row["draw_is_opened"] is True


@pytest.mark.parametrize("changes", [{"term": "283"}, {"year": "bad"}, {"type": "bad"}, {"type": 4}])
def test_overlay_closes_missing_or_invalid_authority(gate_db, changes):
    with connect(gate_db) as conn:
        row = helpers.apply_lottery_draw_overlay(conn, [source_row(**changes)])[0]
    assert_hidden(row)


def test_compat_gates_before_field_projection(gate_db, monkeypatch):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=149))
    with connect(gate_db) as conn:
        payload = handle_frontend_kaijiang_api("/api/kaijiang/getJyxiao2", {"web": ["6"], "type": ["3"], "num": ["2"]}, conn)
    row = payload["data"][0]
    assert row["res_code"] == ""
    assert row["res_sx"] == ""
    assert row["content"] == '["鼠|05,17"]'
    assert row["xiao"] == "鼠,牛"


def test_cached_public_history_rechecks_authority_without_hiding_candidates(gate_db, monkeypatch):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=10))
    payload = {"draw": {"result_balls": [{"value": "01"}], "special_ball": None}, "modules": [{"history": [{"year": "2026", "term": "282", "is_opened": True, "is_correct": True, "result_text": "马07", "raw": source_row(), "formula": {"parity": {"labels": ["单"], "is_correct": True}}, "result": {"res_code": "07", "res_sx": "马", "is_opened": True}, "best_pick": {"code": "07"}}]}]}
    with connect(gate_db) as conn:
        result = helpers.apply_public_result_gate(conn, payload, default_lottery_type_id=3)
    row = result["modules"][0]["history"][0]
    assert row["is_opened"] is False
    assert row["is_correct"] is None
    assert row["result"]["res_code"] == ""
    assert row["formula"]["parity"]["is_correct"] is None
    assert row["best_pick"]["code"] == "07"
    assert_hidden(row["raw"])
    assert result["draw"] == payload["draw"]
    assert payload["modules"][0]["history"][0]["raw"]["res_code"] == CODES


class RouteContext:
    def __init__(self, path, query, db_path):
        self.path = path
        self.method = "GET"
        self.query = query
        self.db_path = self.write_db_path = db_path
        self.state = {"prediction_snapshots": object()}
        self.headers = {}
        self.response = self
        self.sent = None

    def query_value(self, name, default=None):
        return self.query.get(name, [default])[0]

    def send_json(self, value):
        self.sent = value

    def set_header(self, name, value):
        self.headers[name] = value


def test_module_rows_rechecks_an_already_cached_full_result(gate_db, monkeypatch):
    from cache import prediction_snapshots
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=20))
    monkeypatch.setattr(prediction_snapshots, "read_through", lambda *args, **kwargs: {"rows": [source_row()]})
    ctx = RouteContext("/api/legacy/module-rows", {"modes_id": ["251"], "web": ["6"], "type": ["3"]}, gate_db)
    legacy_routes.module_rows(ctx)
    assert_hidden(ctx.sent["rows"][0])
    assert "no-store" in ctx.headers["Cache-Control"]


def test_compat_endpoint_does_not_reuse_projected_result_snapshot(gate_db, monkeypatch):
    from cache import prediction_snapshots
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=20))
    monkeypatch.setattr(prediction_snapshots, "read_through", lambda *args, **kwargs: {"data": [{"res_code": CODES, "res_sx": "马", "content": "stale"}]})
    ctx = RouteContext("/api/kaijiang/getJyxiao2", {"num": ["2"], "web": ["6"], "type": ["3"]}, gate_db)
    router = Router()
    legacy_routes.register(router, default_pc=305, default_web=6, default_type=3)
    next(route.handler for route in router._routes if route.matcher(ctx))(ctx)
    assert ctx.sent["data"][0]["res_code"] == ""
    assert ctx.sent["data"][0]["content"] == '["鼠|05,17"]'
    assert "no-store" in ctx.headers["Cache-Control"]


def test_released_history_keeps_nested_special_result(gate_db, monkeypatch):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=150))
    row = {"year": "2026", "term": "282", "result": {"res_code": "07"}, "raw": source_row()}
    with connect(gate_db) as conn:
        result = helpers.apply_public_result_gate(conn, {"rows": [row]}, default_lottery_type_id=3)
    assert result["rows"][0]["result"]["res_code"] == "07"


@pytest.mark.parametrize("lottery_type", [1, 2])
def test_non_taiwan_supplier_rows_keep_their_existing_result_without_authority(gate_db, lottery_type):
    with connect(gate_db) as conn:
        result = helpers.apply_lottery_draw_overlay(conn, [source_row(type=lottery_type, year="supplier")])
    assert result[0]["res_code"] == CODES


@pytest.mark.parametrize("row", [{"numbers": CODES}, {"special_zodiac": "马"}, {"is_correct": True}])
def test_result_projection_without_period_identity_is_closed(row):
    result = helpers.apply_public_result_gate(None, {"rows": [row]}, default_lottery_type_id=3)["rows"][0]
    assert result.get("numbers", "") == ""
    assert result.get("special_zodiac", "") == ""
    assert result.get("is_correct") is None


def test_fixed_data_numbers_mapping_is_not_an_actual_draw():
    payload = {"numbers": [{"sign": "生肖", "name": "马", "code": "07,19,31,43"}]}
    assert helpers.apply_public_result_gate(None, payload) == payload


@pytest.mark.parametrize("child_key", ["raw", "result"])
def test_released_parent_cannot_release_a_nested_different_issue(gate_db, monkeypatch, child_key):
    monkeypatch.setattr(helpers, "beijing_now", lambda: ANCHOR + timedelta(seconds=20))
    with connect(gate_db) as conn:
        conn.execute("INSERT INTO lottery_draws VALUES (2, 3, 2026, 280, ?, 1, 281, '2026-10-07 21:00:00', '2026-10-07 21:00:00')", (CODES,))
        conn.commit()
        payload = {"rows": [{"year": "2026", "term": "280", "type": 3, child_key: source_row(), "content": "鼠|05,17", "code": "01,02"}]}
        result = helpers.apply_public_result_gate(conn, payload, default_lottery_type_id=3)
    assert_hidden(result["rows"][0][child_key])
    assert result["rows"][0]["content"] == "鼠|05,17"
