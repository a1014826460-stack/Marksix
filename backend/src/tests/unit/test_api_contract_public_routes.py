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


def test_public_site_links_contract_passes_current_site_key():
    ctx = make_ctx("/api/public/site-links?current_site_key=twjsz666")
    payload = {
        "links": [
            {
                "site_key": "shengshi8800",
                "name": "盛世台湾六合彩",
                "domain": "www.tw8800.com",
                "url": "https://www.tw8800.com/",
            }
        ]
    }

    with patch("routes.public_routes.get_public_site_links", return_value=payload) as handler:
        public_routes.site_links(ctx)

    handler.assert_called_once_with(ctx.db_path, "twjsz666")
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_public_site_links_contract_missing_current_site_key_defaults_to_empty():
    ctx = make_ctx("/api/public/site-links")
    payload: dict = {"links": []}

    with patch("routes.public_routes.get_public_site_links", return_value=payload) as handler:
        public_routes.site_links(ctx)

    handler.assert_called_once_with(ctx.db_path, "")
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload

class _Snapshots:
    def __init__(self, latest=None, current=None, error=None):
        self.latest = latest
        self.current = current
        self.error = error
        self.published = []

    def get_latest_draw(self, lottery_type):
        if self.error:
            raise self.error
        return self.latest

    def get_current_period(self, lottery_type):
        if self.error:
            raise self.error
        return self.current

    def publish_latest_draw(self, lottery_type, payload, **kwargs):
        self.published.append(("latest", lottery_type, payload, kwargs))
        if self.error:
            raise self.error
        return True

    def publish_current_period(self, lottery_type, payload, **kwargs):
        self.published.append(("current", lottery_type, payload, kwargs))
        if self.error:
            raise self.error
        return True


def _with_snapshots(ctx, snapshots):
    ctx.state["public_draw_snapshots"] = snapshots
    ctx.handler.server.write_db_path = "postgresql://write:write@localhost:5432/test"
    ctx.handler.server.read_db_path = "postgresql://read:read@localhost:5432/test"
    return ctx


def test_public_latest_draw_snapshot_hit_skips_database():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), _Snapshots(latest=payload))

    with patch("routes.public_routes.get_public_latest_draw") as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_not_called()
    assert response_json(ctx) == payload


def test_public_latest_draw_miss_uses_write_database_and_backfills_snapshot():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    snapshots = _Snapshots()
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), snapshots)

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    assert snapshots.published == [("latest", 3, payload, {"version": "2026012", "is_opened": True})]
    assert response_json(ctx) == payload


def test_public_latest_draw_cache_failure_falls_back_to_write_database():
    from cache.contracts import CacheUnavailable

    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), _Snapshots(error=CacheUnavailable("offline")))

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    assert response_json(ctx) == payload


def test_public_current_period_snapshot_hit_skips_database():
    payload = {"lottery_type_id": 3, "lottery_name": "台湾彩", "current_period": "2026012", "current_year": 2026, "current_term": 12}
    ctx = _with_snapshots(make_ctx("/api/public/current-period?lottery_type=3"), _Snapshots(current=payload))

    with patch("routes.public_routes.get_current_period") as current_period:
        public_routes.current_period(ctx)

    current_period.assert_not_called()
    assert response_json(ctx) == payload


def test_public_current_period_miss_uses_write_database_and_backfills_snapshot():
    payload = {"lottery_type_id": 3, "lottery_name": "台湾彩", "current_period": "2026012", "current_year": 2026, "current_term": 12}
    snapshots = _Snapshots()
    ctx = _with_snapshots(make_ctx("/api/public/current-period?lottery_type=3"), snapshots)

    with patch("routes.public_routes.get_current_period", return_value=payload) as current_period:
        public_routes.current_period(ctx)

    current_period.assert_called_once_with(ctx.write_db_path, 3)
    assert snapshots.published == [("current", 3, payload, {"version": "2026012", "is_opened": True})]
    assert response_json(ctx) == payload
