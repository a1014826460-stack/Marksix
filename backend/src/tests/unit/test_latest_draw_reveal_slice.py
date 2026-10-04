"""服务端分片揭示契约：号码按 reveal_start + 25s×N 逐球开放。

固定行为：
1. 第 1 球在 reveal_start 当刻可见；第 7 球（特码）在 +150 秒可见。
2. 任何时刻对外可见的号码个数只由「服务器时间 - 锚点」决定，与请求次数无关。
3. 锚点之前不下发号码（revealed_count=0）；没有锚点的旧载荷原样返回。
4. 香港彩保持源站轮序发布（按已入库球数下发），不叠加时间闸门。
5. 缓存/发布链路拿到的始终是**完整**载荷，分片只发生在对外响应边界。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from core.time_utils import BEIJING_TZ
from public.draw_reveal import (
    DRAW_BALL_COUNT,
    REVEAL_INTERVAL_SECONDS,
    apply_reveal_slice,
    reveal_anchor,
    reveal_count,
)
from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json

ANCHOR = datetime(2026, 10, 4, 22, 32, 2, tzinfo=BEIJING_TZ)


def _payload(*, reveal_start: str = "2026-10-04 22:32:02", balls: int = 7) -> dict:
    """完整载荷：6 个平码 + 特码；``balls`` 小于 7 时模拟源站只补到前几个号码。"""
    body = [
        {"value": f"{index + 1:02d}", "zodiac": "鼠", "color": "red", "element": "金"}
        for index in range(min(balls, DRAW_BALL_COUNT - 1))
    ]
    special = None
    if balls >= DRAW_BALL_COUNT:
        special = {"value": "49", "zodiac": "牛", "color": "green", "element": "水"}
    return {
        "current_issue": "2026277",
        "draw_time": "2026-10-04 22:32:00",
        "reveal_start": reveal_start,
        "result_balls": body,
        "special_ball": special,
    }


def _at(seconds: float) -> datetime:
    return ANCHOR + timedelta(seconds=seconds)


# ── 纯函数：节奏 ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "elapsed,expected",
    [
        (0, 1),
        (1, 1),
        (24.9, 1),
        (25, 2),
        (50, 3),
        (149.9, 6),
        (150, 7),
        (600, 7),
    ],
)
def test_reveal_count_follows_anchor_plus_interval(elapsed, expected):
    assert reveal_count(anchor=ANCHOR, available=7, now=_at(elapsed)) == expected


def test_reveal_count_is_zero_before_anchor():
    assert reveal_count(anchor=ANCHOR, available=7, now=_at(-1)) == 0


def test_reveal_count_never_exceeds_available_balls():
    assert reveal_count(anchor=ANCHOR, available=3, now=_at(600)) == 3
    assert reveal_count(anchor=ANCHOR, available=0, now=_at(600)) == 0


def test_source_availability_caps_but_never_accelerates_the_reveal():
    """源站只补到 4 个号码（港彩渐进）：时间闸门照常生效，只是被 4 封顶。"""
    assert reveal_count(anchor=ANCHOR, available=4, now=_at(0)) == 1
    assert reveal_count(anchor=ANCHOR, available=4, now=_at(75)) == 4
    assert reveal_count(anchor=ANCHOR, available=4, now=_at(600)) == 4


def test_reveal_anchor_prefers_reveal_start_then_draw_time():
    assert reveal_anchor({"reveal_start": "2026-10-04 22:32:02"}) == ANCHOR
    assert reveal_anchor({"draw_time": "2026-10-04 22:32:00", "reveal_start": ""}) == datetime(
        2026, 10, 4, 22, 32, 0, tzinfo=BEIJING_TZ
    )
    assert reveal_anchor({"draw_time": "2026-08-07"}) is None
    assert reveal_anchor({}) is None


# ── 纯函数：切片 ────────────────────────────────────────────────────────────

def test_slice_hides_unrevealed_balls_and_reports_progress():
    sliced = apply_reveal_slice(_payload(), now=_at(0))

    assert sliced["revealed_count"] == 1
    assert sliced["total_balls"] == DRAW_BALL_COUNT
    assert sliced["reveal_interval_seconds"] == REVEAL_INTERVAL_SECONDS
    assert sliced["is_complete"] is False
    assert [ball["value"] for ball in sliced["result_balls"]] == ["01"]
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"] == "2026-10-04 22:32:27"
    assert sliced["reveal_start"] == "2026-10-04 22:32:02"


def test_slice_reveals_special_ball_only_at_the_end():
    before = apply_reveal_slice(_payload(), now=_at(149))
    after = apply_reveal_slice(_payload(), now=_at(150))

    assert before["revealed_count"] == 6
    assert before["special_ball"] is None
    assert [ball["value"] for ball in before["result_balls"]] == ["01", "02", "03", "04", "05", "06"]

    assert after["revealed_count"] == 7
    assert after["is_complete"] is True
    assert [ball["value"] for ball in after["result_balls"]] == ["01", "02", "03", "04", "05", "06"]
    assert after["special_ball"]["value"] == "49"
    assert after["next_reveal_at"] == ""


def test_slice_sends_no_numbers_before_the_anchor():
    sliced = apply_reveal_slice(_payload(), now=_at(-30))

    assert sliced["revealed_count"] == 0
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"] == "2026-10-04 22:32:02"


def test_slice_without_anchor_leaves_legacy_payload_untouched():
    legacy = {"current_issue": "2026277", "draw_time": "2026-08-07", "result_balls": [{"value": "01"}], "special_ball": None}

    assert apply_reveal_slice(legacy, now=_at(0)) == legacy


def test_slice_does_not_mutate_the_complete_payload_used_for_cache():
    complete = _payload()

    apply_reveal_slice(complete, now=_at(0))

    assert len(complete["result_balls"]) == 6
    assert complete["special_ball"]["value"] == "49"
    assert "revealed_count" not in complete


def test_slice_keeps_partial_source_data_incomplete():
    # 源站只补到 3 个号码（港彩）：可以下发 3 个，但绝不因此判定已完整。
    sliced = apply_reveal_slice(_payload(balls=3), now=_at(600))

    assert sliced["revealed_count"] == 3
    assert sliced["is_complete"] is False
    assert len(sliced["result_balls"]) == 3
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"]


# ── 路由边界：缓存里保留完整载荷 ────────────────────────────────────────────

class _Snapshots:
    def __init__(self, latest=None):
        self.latest = latest
        self.published: list[tuple] = []

    def get_latest_draw(self, lottery_type):
        return self.latest

    def get_current_period(self, lottery_type):
        return None

    def publish_latest_draw(self, lottery_type, payload, **kwargs):
        self.published.append(("latest", lottery_type, payload, kwargs))
        return True

    def publish_current_period(self, lottery_type, payload, **kwargs):
        return True


def _with_snapshots(ctx, snapshots):
    ctx.state["public_draw_snapshots"] = snapshots
    ctx.handler.server.write_db_path = "postgresql://write:write@localhost:5432/test"
    ctx.handler.server.read_db_path = "postgresql://read:read@localhost:5432/test"
    return ctx


def test_route_slices_snapshot_payload_at_response_boundary():
    complete = _payload()
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), _Snapshots(latest=complete))

    with patch("routes.public_routes.get_public_latest_draw") as latest_draw, \
         patch("public.draw_reveal.beijing_now", return_value=_at(25)):
        public_routes.latest_draw(ctx)

    latest_draw.assert_not_called()
    body = response_json(ctx)
    assert body["revealed_count"] == 2
    assert [ball["value"] for ball in body["result_balls"]] == ["01", "02"]
    # 快照对象保持完整，后续请求继续按时间推进
    assert len(complete["result_balls"]) == 6
    assert complete["special_ball"]["value"] == "49"
    assert "revealed_count" not in complete


def test_site_page_route_slices_the_draw_section_at_the_boundary():
    """站点聚合快照里保存完整号码，聚合出口按同一节奏逐球开放。"""
    ctx = make_ctx("/api/public/site-page?site_id=10&lottery_type=3")
    payload = {"site": {"id": 10}, "draw": _payload(), "modules": []}

    with patch("public.draw_reveal.beijing_now", return_value=_at(25)):
        public_routes._send_site_page(ctx, payload)

    body = response_json(ctx)
    assert body["draw"]["revealed_count"] == 2
    assert [ball["value"] for ball in body["draw"]["result_balls"]] == ["01", "02"]
    assert body["draw"]["is_complete"] is False
    # 传给快照的完整载荷不被改写
    assert len(payload["draw"]["result_balls"]) == 6
    assert "revealed_count" not in payload["draw"]


def test_route_backfills_snapshot_with_complete_payload():
    complete = _payload()
    snapshots = _Snapshots()
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), snapshots)

    with patch("routes.public_routes.get_public_latest_draw", return_value=complete), \
         patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        public_routes.latest_draw(ctx)

    assert snapshots.published == [("latest", 3, complete, {"version": "2026277", "is_opened": True})]
    body = response_json(ctx)
    assert body["revealed_count"] == 1
    assert len(body["result_balls"]) == 1
    assert body["is_complete"] is False
