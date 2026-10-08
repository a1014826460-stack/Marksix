from __future__ import annotations

from unittest.mock import patch

import pytest

from core.errors import ValidationError
from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json


def _assert_blocked_latest_draw(ctx, payload):
    body = response_json(ctx)
    server_now = body.pop("server_now")
    server_now_ms = body.pop("server_now_ms")
    assert isinstance(server_now, int)
    assert isinstance(server_now_ms, int)
    assert server_now_ms // 1000 == server_now
    assert body == {
        **payload,
        "result_balls": [],
        "special_ball": None,
        "revealed_count": 0,
        "total_balls": 7,
        "reveal_interval_seconds": 25,
        "is_complete": False,
        "next_reveal_at": "",
    }


def test_public_latest_draw_contract():
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    payload = {
        "current_issue": "2026188",
        "draw_time": "2026-08-07",
        "reveal_start": "",
        "result_balls": [{"value": f"{i:02d}"} for i in range(1, 7)],
        "special_ball": {"value": "07"},
    }

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.db_path, 3)
    assert ctx.handler.response_status == 200
    _assert_blocked_latest_draw(ctx, payload)


@pytest.mark.parametrize("lottery_type_id", [1, 2])
def test_site_page_without_explicit_type_uses_resolved_hk_macau_site_type(lottery_type_id):
    ctx = make_ctx("/api/public/site-page?site_id=10")
    draw = {
        "current_issue": "2026277",
        "draw_time": "2026-10-04",
        "reveal_start": "",
        "result_balls": [{"value": f"{i:02d}"} for i in range(1, 7)],
        "special_ball": {"value": "07"},
    }
    payload = {"site": {"id": 10, "lottery_type_id": lottery_type_id}, "draw": draw, "modules": []}

    with patch("routes.public_routes.get_public_site_page_data", return_value=payload):
        public_routes.site_page(ctx)

    assert ctx.handler.response_status == 200
    body = response_json(ctx)
    assert body["draw"] == draw
    assert body["site"]["lottery_type_id"] == lottery_type_id
    assert body["modules"] == []


def test_public_latest_draw_does_not_apply_history_visibility_gate(monkeypatch):
    ctx = make_ctx("/api/public/latest-draw?lottery_type=3")
    payload = {
        "current_issue": "2026188",
        "draw_time": "2026-08-07",
        "reveal_start": "",
        "result_balls": [{"value": f"{i:02d}"} for i in range(1, 7)],
        "special_ball": {"value": "07"},
    }

    monkeypatch.setattr(
        "public.api._history_result_visible",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("history gate called")),
    )
    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.db_path, 3)
    assert ctx.handler.response_status == 200
    _assert_blocked_latest_draw(ctx, payload)


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
        "server_now": 1782560000,
        "server_now_ms": 1782560000000,
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


def test_public_fixed_data_groups_contract_reads_sign_from_query():
    """合数单双等固定分组的号码表必须由后端只读接口提供（前端不得硬编码）。"""
    ctx = make_ctx("/api/public/fixed-data-groups?sign=%E5%90%88%E5%8D%95%E5%8F%8C")
    payload = {
        "sign": "合单双",
        "groups": [
            {"label": "合单", "codes": ["01", "03"]},
            {"label": "合双", "codes": ["02", "04"]},
        ],
    }

    with patch("routes.public_routes.load_fixed_data_groups", return_value=payload) as handler:
        public_routes.fixed_data_groups(ctx)

    handler.assert_called_once_with(ctx.db_path, "合单双")
    assert ctx.handler.response_status == 200
    assert response_json(ctx) == payload


def test_public_fixed_data_groups_contract_rejects_blank_sign():
    ctx = make_ctx("/api/public/fixed-data-groups?sign=")

    with patch("routes.public_routes.load_fixed_data_groups") as handler:
        with pytest.raises(ValidationError):
            public_routes.fixed_data_groups(ctx)

    handler.assert_not_called()

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


def test_public_latest_draw_taiwan_snapshot_hit_rechecks_primary():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), _Snapshots(latest=payload))

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    _assert_blocked_latest_draw(ctx, payload)


def test_public_latest_draw_miss_uses_write_database_and_backfills_snapshot():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    snapshots = _Snapshots()
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), snapshots)

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    assert snapshots.published == [("latest", 3, payload, {"version": "2026012", "is_opened": True})]
    _assert_blocked_latest_draw(ctx, payload)


def test_public_latest_draw_cache_failure_falls_back_to_write_database():
    from cache.contracts import CacheUnavailable

    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), _Snapshots(error=CacheUnavailable("offline")))

    with patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    _assert_blocked_latest_draw(ctx, payload)


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

class _RawCache:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.writes = []

    def get(self, key):
        if self.error:
            raise self.error
        return self.value

    def set(self, key, value, *, ttl_seconds):
        if self.error:
            raise self.error
        self.writes.append((key, value, ttl_seconds))


def _with_site_cache(ctx, cache):
    ctx.state["cache_store"] = cache
    return ctx


def test_public_latest_draw_site_cache_hit_skips_site_context_resolution():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    ctx = _with_site_cache(_with_snapshots(make_ctx("/api/public/latest-draw?site_id=12"), _Snapshots(latest=payload)), _RawCache(b"3"))

    with patch("routes.public_routes.resolve_site_context") as resolve_site, \
         patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    resolve_site.assert_not_called()
    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    _assert_blocked_latest_draw(ctx, payload)


def test_public_latest_draw_site_cache_miss_resolves_from_write_target_and_backfills():
    payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
    cache = _RawCache()
    ctx = _with_site_cache(_with_snapshots(make_ctx("/api/public/latest-draw?site_id=12"), _Snapshots(latest=payload)), cache)

    with patch("routes.public_routes.resolve_site_context", return_value=type("Site", (), {"lottery_type_id": 3})()) as resolve_site, \
         patch("routes.public_routes.get_public_latest_draw", return_value=payload) as latest_draw:
        public_routes.latest_draw(ctx)

    resolve_site.assert_called_once_with(ctx.write_db_path, path_site_id=12, query=ctx.query)
    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    assert cache.writes == [("public:site-lottery:v1:id:12", b"3", 60)]
    _assert_blocked_latest_draw(ctx, payload)


def test_public_latest_draw_invalid_or_unavailable_site_cache_falls_back_to_write_target():
    from cache.contracts import CacheUnavailable

    for cache in (_RawCache(b"not-a-number"), _RawCache(error=CacheUnavailable("offline"))):
        payload = {"current_issue": "2026012", "draw_time": "2026-08-07", "result_balls": [], "special_ball": None}
        ctx = _with_site_cache(_with_snapshots(make_ctx("/api/public/latest-draw?site_id=12"), _Snapshots(latest=payload)), cache)
        with patch("routes.public_routes.resolve_site_context", return_value=type("Site", (), {"lottery_type_id": 3})()) as resolve_site, \
             patch("routes.public_routes.get_public_latest_draw", return_value=payload):
            public_routes.latest_draw(ctx)
        resolve_site.assert_called_once_with(ctx.write_db_path, path_site_id=12, query=ctx.query)
        _assert_blocked_latest_draw(ctx, payload)
