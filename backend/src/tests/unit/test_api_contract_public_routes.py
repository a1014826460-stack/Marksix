from __future__ import annotations

from unittest.mock import patch

from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json


def test_public_latest_draw_contract():
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    payload = {
        "year": 2026,
        "term": 188,
        "numbers": "01,02,03,04,05,06,07",
        "is_opened": True,
    }

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.db_path, 3)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_public_next_draw_deadline_contract_adds_server_time():
    ctx = make_ctx("/api/public/next-draw-deadline?lottery_type=2")
    payload = {
        "draw_deadline": "1782570600000",
        "next_time": "2026-06-27 21:30:00",
    }

    with patch("routes.public_routes.time.time", return_value=1782560000), \
         patch("routes.public_routes.get_public_next_draw_deadline", return_value=dict(payload)) as deadline:
        public_routes.next_draw_deadline(ctx)

    deadline.assert_called_once_with(ctx.db_path, 2)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {
        "draw_deadline": "1782570600000",
        "next_time": "2026-06-27 21:30:00",
        "server_time": "1782560000",
    }


def test_public_notice_contract_and_web_mapping():
    ctx = make_ctx("/api/public/notice?web=6")

    with patch("routes.public_routes.get_public_notice", return_value={"code": 600, "data": {"content": "hello"}}) as notice:
        public_routes.notice(ctx)

    notice.assert_called_once_with(ctx.db_path, 6)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"code": 600, "data": {"content": "hello"}}


def test_public_notice_contract_ignores_invalid_web():
    ctx = make_ctx("/api/index/notice?web=bad")

    with patch("routes.public_routes.get_public_notice", return_value={"code": 200, "data": {"content": ""}}) as notice:
        public_routes.notice(ctx)

    notice.assert_called_once_with(ctx.db_path, None)
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == {"code": 200, "data": {"content": ""}}
