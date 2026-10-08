from copy import deepcopy
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core.time_utils import BEIJING_TZ
from db import connect
from routes import vendor_routes


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("elapsed", [-1, 1, 149, 150])
def test_vendor_response_rechecks_full_result_gate(tmp_path, monkeypatch, cached, elapsed):
    db_path = str(tmp_path / "gate.db")
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE lottery_draws (id INTEGER PRIMARY KEY, lottery_type_id INTEGER, year INTEGER, term INTEGER, numbers TEXT, is_opened INTEGER, next_term INTEGER, draw_time TEXT, opened_at TEXT)")
        conn.execute("INSERT INTO lottery_draws VALUES (1,3,2026,281,'01,02,03,04,05,06,07',1,282,'2026-10-08 22:32:00','2026-10-08 22:32:00')")
        conn.commit()
    anchor = datetime(2026, 10, 8, 22, 32, tzinfo=BEIJING_TZ)
    monkeypatch.setattr("helpers.beijing_now", lambda: anchor + timedelta(seconds=elapsed))
    monkeypatch.setattr("helpers._resolve_history_delay_minutes", lambda *_args: 0)
    payload = {"site": {"id": 1, "lottery_type": 3}, "modules": [{"history": [{"year": "2026", "term": "281", "content": "候选01,07,12", "res_code": "01,02,03,04,05,06,07", "res_sx": "鼠,牛,虎,兔,龙,蛇,马", "result_text": "开:马07", "is_correct": True}]}]}
    original = deepcopy(payload)
    monkeypatch.setattr(vendor_routes, "build_vendor_homepage_modules", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(vendor_routes, "read_through", lambda *_args, **_kwargs: payload)
    captured = {}
    query = {"site_id": "1", "lottery_type": "3" if cached else None}
    ctx = SimpleNamespace(db_path=db_path, write_db_path=db_path, state={},
                          query_value=lambda key, default=None: query.get(key, default),
                          response=SimpleNamespace(set_header=lambda key, value: captured.setdefault("headers", {}).update({key: value})),
                          send_json=lambda data: captured.update(data=data))
    vendor_routes.homepage_modules(ctx)
    row = captured["data"]["modules"][0]["history"][0]
    assert bool(row["res_code"]) is (elapsed >= 150)
    if elapsed < 150:
        assert row["is_correct"] is None
        assert "07" not in row["result_text"]
    assert row["content"] == "候选01,07,12"
    assert captured["headers"]["Cache-Control"] == "no-store"
    assert payload == original
