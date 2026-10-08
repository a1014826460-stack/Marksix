"""服务端分片揭示契约：台湾彩按 reveal_start + 25s×N 逐球开放。

固定行为：
1. 台湾彩：第 1 球在 reveal_start 当刻可见；第 7 球（特码）在 +150 秒可见。
2. 任何时刻对外可见的号码个数只由「服务器时间 - 锚点」决定，与请求次数无关。
3. 锚点之前不下发号码；台湾彩缺少有效锚点时关闭揭示，空载荷保持兼容。
4. 港澳彩（源站本来就公开号码）**不叠加时间闸门**：已入库几个就下发几个，
   `next_reveal_at` 为空串；台湾彩是提前入库的未来真值，必须逐球放行。
5. 缓存/发布链路拿到的始终是**完整**载荷，分片只发生在对外响应边界。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import logging
from unittest.mock import patch

import pytest

from core.time_utils import BEIJING_TZ
from public.draw_reveal import (
    DRAW_BALL_COUNT,
    PACED_REVEAL_LOTTERY_TYPES,
    REVEAL_INTERVAL_SECONDS,
    apply_reveal_slice,
    is_paced_lottery_type,
    reveal_anchor,
    reveal_count,
)
from routes import public_routes
from tests.helpers.api_contract import make_ctx, response_json

ANCHOR = datetime(2026, 10, 4, 22, 32, 2, tzinfo=BEIJING_TZ)
TAIWAN = 3
HONGKONG = 1
MACAU = 2


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
    assert reveal_anchor({"draw_time": "2026-10-04 22:32:00", "reveal_start": "2026-10-04 22:32:02"}) == ANCHOR
    assert reveal_anchor({"draw_time": "2026-10-04 22:32:00", "reveal_start": ""}) == datetime(
        2026, 10, 4, 22, 32, 0, tzinfo=BEIJING_TZ
    )
    assert reveal_anchor({"draw_time": "2026-08-07"}) is None
    assert reveal_anchor({}) is None


@pytest.mark.parametrize("planned", [None, "", "  ", "invalid", "2026-02-30 22:32:00", "2026-13-04 22:32:00", "2026-10-04 24:00:00", "2026-2-3 2:3:4"])
def test_taiwan_valid_preferred_cannot_open_without_a_valid_planned_draw(planned):
    payload = {**_payload(), "draw_time": planned}
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))
    assert sliced["revealed_count"] == 0
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["is_complete"] is False
    assert sliced["next_reveal_at"] == ""
    assert reveal_anchor(payload) is None


def test_taiwan_missing_planned_draw_does_not_open_from_preferred_alone():
    payload = _payload()
    payload.pop("draw_time")
    assert reveal_anchor(payload) is None
    assert apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))["revealed_count"] == 0


@pytest.mark.parametrize("elapsed,expected", [(-1, 0), (0, 1), (24, 1), (25, 2), (149, 6), (150, 7)])
def test_taiwan_early_opened_at_cannot_open_before_its_planned_draw(elapsed, expected):
    payload = {**_payload(reveal_start="2026-10-04 22:30:00"), "draw_time": "2026-10-04 22:32:02"}

    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(elapsed))

    assert sliced["revealed_count"] == expected
    assert sliced["reveal_start"] == "2026-10-04 22:32:02"
    assert (sliced["special_ball"] or {}).get("value") == ("49" if expected == 7 else None)
    assert payload["reveal_start"] == "2026-10-04 22:30:00", "cache keeps the original complete payload"


@pytest.mark.parametrize("preferred", ["invalid", "2026-02-30 22:32:02", "2026-13-04 22:32:02", "2026-10-04 24:00:00", "2026-10-04", "2026-2-3 2:3:4", "2026-10-04T22:32:02+08:00"])
def test_taiwan_invalid_preferred_anchor_cannot_fall_back_to_valid_draw_time(preferred):
    payload = _payload(reveal_start=preferred)

    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))

    assert sliced["revealed_count"] == 0
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["is_complete"] is False
    assert sliced["next_reveal_at"] == ""
    assert reveal_anchor(payload) is None


@pytest.mark.parametrize("preferred", [None, "", "  "])
def test_taiwan_empty_preferred_anchor_uses_planned_draw_time(preferred):
    payload = {**_payload(reveal_start=preferred), "draw_time": "2026-10-04T22:32:02"}
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(25))
    assert sliced["revealed_count"] == 2
    assert sliced["reveal_start"] == "2026-10-04 22:32:02"


def test_taiwan_canonicalizes_valid_t_separator_without_restarting_reveal():
    payload = _payload(reveal_start="2026-10-04T22:32:02")
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(150))
    assert sliced["revealed_count"] == 7
    assert sliced["reveal_start"] == "2026-10-04 22:32:02"


@pytest.mark.parametrize("lottery_type_id", [HONGKONG, MACAU])
@pytest.mark.parametrize("preferred", ["2026-10-04 22:30:00", "invalid", "2026-2-3 2:3:4"])
def test_hk_macau_preserve_legacy_anchor_and_immediate_source_behavior(lottery_type_id, preferred):
    payload = {**_payload(reveal_start=preferred), "draw_time": "2026-10-05 22:32:00"}
    sliced = apply_reveal_slice(payload, lottery_type_id=lottery_type_id, now=_at(0))
    assert sliced["revealed_count"] == 7
    assert sliced["special_ball"]["value"] == "49"
    assert sliced["reveal_start"] == preferred
    assert sliced["next_reveal_at"] == ""


@pytest.mark.parametrize("bad_ball", [None, {}, {"value": ""}, {"value": "  "}, "not-a-ball"])
def test_taiwan_only_delivers_contiguous_regular_prefix_before_a_hole(bad_ball):
    payload = _payload()
    payload["result_balls"][2] = bad_ball
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))
    assert sliced["revealed_count"] == 2
    assert [ball["value"] for ball in sliced["result_balls"]] == ["01", "02"]
    assert sliced["special_ball"] is None


@pytest.mark.parametrize("regular_count", [0, 1, 3, 5])
def test_taiwan_special_cannot_move_into_a_missing_regular_slot(regular_count):
    payload = _payload()
    payload["result_balls"] = payload["result_balls"][:regular_count]
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))
    assert sliced["revealed_count"] == regular_count
    assert len(sliced["result_balls"]) == regular_count
    assert sliced["special_ball"] is None


@pytest.mark.parametrize("has_special,expected", [(True, 7), (False, 6)])
def test_taiwan_extra_regular_ball_cannot_replace_the_seventh_special_slot(has_special, expected):
    payload = _payload()
    payload["result_balls"].append({"value": "31"})
    if not has_special:
        payload["special_ball"] = None
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))
    assert sliced["revealed_count"] == expected
    assert [ball["value"] for ball in sliced["result_balls"]] == ["01", "02", "03", "04", "05", "06"]
    assert (sliced["special_ball"] or {}).get("value") == ("49" if has_special else None)


@pytest.mark.parametrize("regular", [[], [None, {"value": "02"}], "invalid-list"])
def test_taiwan_raw_numbers_without_issue_or_anchor_cannot_bypass_an_empty_prefix(regular):
    payload = {**_payload(reveal_start="invalid"), "current_issue": "", "draw_time": "", "result_balls": regular}
    sliced = apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(600))
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["revealed_count"] == 0
    assert sliced["is_complete"] is False


def test_only_taiwan_is_paced_and_unknown_types_fail_safe_to_paced():
    assert PACED_REVEAL_LOTTERY_TYPES == frozenset({TAIWAN})
    assert is_paced_lottery_type(TAIWAN) is True
    assert is_paced_lottery_type("3") is True
    assert is_paced_lottery_type(HONGKONG) is False
    assert is_paced_lottery_type(MACAU) is False
    # 漏传/非法彩种按节拍处理：只会多一段节拍，绝不会提前放号
    assert is_paced_lottery_type(None) is True
    assert is_paced_lottery_type("") is True
    assert is_paced_lottery_type("taiwan") is True


# ── 纯函数：切片 ────────────────────────────────────────────────────────────

def test_slice_hides_unrevealed_balls_and_reports_progress():
    sliced = apply_reveal_slice(_payload(), lottery_type_id=TAIWAN, now=_at(0))

    assert sliced["revealed_count"] == 1
    assert sliced["total_balls"] == DRAW_BALL_COUNT
    assert sliced["reveal_interval_seconds"] == REVEAL_INTERVAL_SECONDS
    assert sliced["is_complete"] is False
    assert [ball["value"] for ball in sliced["result_balls"]] == ["01"]
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"] == "2026-10-04 22:32:27"
    assert sliced["reveal_start"] == "2026-10-04 22:32:02"


def test_slice_reveals_special_ball_only_at_the_end():
    before = apply_reveal_slice(_payload(), lottery_type_id=TAIWAN, now=_at(149))
    after = apply_reveal_slice(_payload(), lottery_type_id=TAIWAN, now=_at(150))

    assert before["revealed_count"] == 6
    assert before["special_ball"] is None
    assert [ball["value"] for ball in before["result_balls"]] == ["01", "02", "03", "04", "05", "06"]

    assert after["revealed_count"] == 7
    assert after["is_complete"] is True
    assert [ball["value"] for ball in after["result_balls"]] == ["01", "02", "03", "04", "05", "06"]
    assert after["special_ball"]["value"] == "49"
    assert after["next_reveal_at"] == ""


def test_slice_sends_no_numbers_before_the_anchor():
    sliced = apply_reveal_slice(_payload(), lottery_type_id=TAIWAN, now=_at(-30))

    assert sliced["revealed_count"] == 0
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"] == "2026-10-04 22:32:02"


def test_slice_without_anchor_blocks_legacy_taiwan_numbers():
    legacy = {"current_issue": "2026277", "draw_time": "2026-08-07", "result_balls": [{"value": "01"}], "special_ball": None}

    sliced = apply_reveal_slice(legacy, lottery_type_id=TAIWAN, now=_at(0))
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["revealed_count"] == 0
    assert sliced["is_complete"] is False
    assert sliced["next_reveal_at"] == ""
    assert "blocked_reason" not in sliced


@pytest.mark.parametrize("lottery_type_id", [TAIWAN, None, "invalid"])
@pytest.mark.parametrize("anchor", ["", "invalid", "2026-10-04", "2026-10-04T22:32:02+08:00"])
def test_unparseable_taiwan_anchor_never_exposes_complete_numbers(lottery_type_id, anchor):
    payload = {**_payload(reveal_start=anchor), "draw_time": anchor}
    sliced = apply_reveal_slice(payload, lottery_type_id=lottery_type_id, now=_at(600))
    assert sliced["result_balls"] == []
    assert sliced["special_ball"] is None
    assert sliced["revealed_count"] == 0
    assert sliced["is_complete"] is False
    assert sliced["total_balls"] == 7
    assert sliced["reveal_interval_seconds"] == 25
    assert sliced["server_now"] == int(_at(600).timestamp())
    assert len(payload["result_balls"]) == 6
    assert payload["special_ball"] is not None


def test_issue_without_numbers_or_anchor_still_reports_pending_progress():
    sliced = apply_reveal_slice({"current_issue": "2026277"}, lottery_type_id=TAIWAN, now=_at(0))
    assert sliced["revealed_count"] == 0
    assert sliced["is_complete"] is False
    assert sliced["server_now"] == int(_at(0).timestamp())


@pytest.mark.parametrize("payload", [{}, {"current_issue": "", "draw_time": "", "reveal_start": "", "result_balls": [], "special_ball": None}])
def test_no_draw_response_preserves_its_shape(payload):
    assert apply_reveal_slice(payload, lottery_type_id=TAIWAN, now=_at(0)) == payload


@pytest.mark.parametrize("lottery_type_id", [HONGKONG, MACAU])
def test_hk_macau_payload_without_anchor_preserves_legacy_behavior(lottery_type_id):
    payload = {**_payload(reveal_start=""), "draw_time": "invalid"}
    assert apply_reveal_slice(payload, lottery_type_id=lottery_type_id, now=_at(0)) == payload


@pytest.mark.parametrize("elapsed,count", [(-1, 0), (0, 1), (24.99, 1), (25, 2), (50, 3), (75, 4), (100, 5), (125, 6), (149.99, 6), (150, 7)])
def test_response_progress_and_server_clock_share_the_same_instant(elapsed, count):
    sliced = apply_reveal_slice(_payload(), lottery_type_id=TAIWAN, now=_at(elapsed))
    assert sliced["revealed_count"] == count
    assert sliced["is_complete"] is (count == 7)
    assert sliced["server_now"] == int(_at(elapsed).timestamp())
    assert (sliced["special_ball"] is not None) is (count == 7)


def test_slice_does_not_mutate_the_complete_payload_used_for_cache():
    complete = _payload()

    apply_reveal_slice(complete, lottery_type_id=TAIWAN, now=_at(0))

    assert len(complete["result_balls"]) == 6
    assert complete["special_ball"]["value"] == "49"
    assert "revealed_count" not in complete
    assert "server_now" not in complete


def test_slice_keeps_partial_source_data_incomplete():
    # 台湾彩源站只补到 3 个号码：可以下发 3 个，但绝不因此判定已完整。
    sliced = apply_reveal_slice(_payload(balls=3), lottery_type_id=TAIWAN, now=_at(600))

    assert sliced["revealed_count"] == 3
    assert sliced["is_complete"] is False
    assert len(sliced["result_balls"]) == 3
    assert sliced["special_ball"] is None
    assert sliced["next_reveal_at"]


# ── 港澳彩：不叠加时间闸门（源站本来就公开）────────────────────────────────

@pytest.mark.parametrize("lottery_type_id", [HONGKONG, MACAU])
def test_hk_macau_reveal_everything_already_available(lottery_type_id):
    """港澳彩一拿到号码就全量下发，不受 reveal_start + 25s 节拍限制。"""
    at_anchor = apply_reveal_slice(_payload(), lottery_type_id=lottery_type_id, now=_at(0))
    assert at_anchor["revealed_count"] == 7
    assert at_anchor["is_complete"] is True
    assert at_anchor["next_reveal_at"] == ""
    assert [ball["value"] for ball in at_anchor["result_balls"]] == [
        "01", "02", "03", "04", "05", "06"
    ]
    assert at_anchor["special_ball"]["value"] == "49"
    # 锚点之前也一样（港澳没有「等待开盘」语义，载荷里有多少就是多少）
    before = apply_reveal_slice(_payload(), lottery_type_id=lottery_type_id, now=_at(-300))
    assert before["revealed_count"] == 7
    assert before["is_complete"] is True


@pytest.mark.parametrize("lottery_type_id", [HONGKONG, MACAU])
def test_hk_macau_partial_source_data_is_returned_as_is(lottery_type_id):
    sliced = apply_reveal_slice(_payload(balls=4), lottery_type_id=lottery_type_id, now=_at(0))

    assert sliced["revealed_count"] == 4
    assert sliced["is_complete"] is False
    assert len(sliced["result_balls"]) == 4
    assert sliced["special_ball"] is None
    # 不承诺下一次揭示时间：前端按 5 秒轮询补齐
    assert sliced["next_reveal_at"] == ""


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

    with patch("routes.public_routes.get_public_latest_draw", return_value=complete) as latest_draw, \
         patch("public.draw_reveal.beijing_now", return_value=_at(25)):
        public_routes.latest_draw(ctx)

    latest_draw.assert_called_once_with(ctx.write_db_path, 3)
    body = response_json(ctx)
    assert body["revealed_count"] == 2
    assert [ball["value"] for ball in body["result_balls"]] == ["01", "02"]
    # 快照对象保持完整，后续请求继续按时间推进
    assert len(complete["result_balls"]) == 6
    assert complete["special_ball"]["value"] == "49"
    assert "revealed_count" not in complete


def test_site_page_route_slices_the_draw_section_at_the_boundary():
    """站点聚合快照里保存完整号码，台湾彩聚合出口按同一节奏逐球开放。"""
    ctx = make_ctx("/api/public/site-page?site_id=10&lottery_type=3")
    payload = {"site": {"id": 10}, "draw": _payload(), "modules": []}

    with patch("public.draw_reveal.beijing_now", return_value=_at(25)), \
         patch("routes.public_routes.get_public_latest_draw", return_value=payload["draw"]):
        public_routes._send_site_page(ctx, payload, TAIWAN)

    body = response_json(ctx)
    assert body["draw"]["revealed_count"] == 2
    assert [ball["value"] for ball in body["draw"]["result_balls"]] == ["01", "02"]
    assert body["draw"]["is_complete"] is False
    # 传给快照的完整载荷不被改写
    assert len(payload["draw"]["result_balls"]) == 6
    assert "revealed_count" not in payload["draw"]


@pytest.mark.parametrize("lottery_type_id", [HONGKONG, MACAU])
def test_site_page_route_sends_every_hk_macau_ball_immediately(lottery_type_id):
    """港澳彩站点聚合出口：拿到几个就下发几个，不按 25 秒节拍裁号。"""
    ctx = make_ctx(f"/api/public/site-page?site_id=10&lottery_type={lottery_type_id}")
    payload = {"site": {"id": 10}, "draw": _payload(), "modules": []}

    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        public_routes._send_site_page(ctx, payload, lottery_type_id)

    body = response_json(ctx)
    assert body["draw"]["revealed_count"] == 7
    assert body["draw"]["is_complete"] is True
    assert body["draw"]["next_reveal_at"] == ""
    assert body["draw"]["special_ball"]["value"] == "49"
    assert len(payload["draw"]["result_balls"]) == 6
    assert "revealed_count" not in payload["draw"]


@pytest.mark.parametrize("lottery_type_id", [TAIWAN, None, "invalid", 99, True])
def test_site_page_inferred_taiwan_or_unknown_type_without_anchor_blocks_numbers(lottery_type_id):
    ctx = make_ctx("/api/public/site-page?site_id=10")
    draw = {**_payload(reveal_start=""), "draw_time": "invalid"}
    payload = {"site": {"id": 10, "lottery_type_id": lottery_type_id}, "draw": draw, "modules": []}

    with patch("routes.public_routes.get_public_latest_draw", return_value=draw):
        public_routes._send_site_page(ctx, payload)

    body = response_json(ctx)
    assert body["draw"]["result_balls"] == []
    assert body["draw"]["special_ball"] is None
    assert body["draw"]["revealed_count"] == 0
    assert len(payload["draw"]["result_balls"]) == 6


def test_site_page_explicit_taiwan_type_takes_precedence_over_site_metadata():
    ctx = make_ctx("/api/public/site-page?site_id=10&lottery_type=3")
    payload = {"site": {"id": 10, "lottery_type_id": HONGKONG}, "draw": _payload(), "modules": []}

    with patch("public.draw_reveal.beijing_now", return_value=_at(0)), \
         patch("routes.public_routes.get_public_latest_draw", return_value=payload["draw"]):
        public_routes._send_site_page(ctx, payload, TAIWAN)

    assert response_json(ctx)["draw"]["revealed_count"] == 1


def test_latest_draw_route_sends_every_macau_ball_immediately():
    complete = _payload()
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=2"), _Snapshots(latest=complete))

    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        public_routes.latest_draw(ctx)

    body = response_json(ctx)
    assert body["revealed_count"] == 7
    assert body["is_complete"] is True
    assert body["next_reveal_at"] == ""
    assert body["special_ball"]["value"] == "49"


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


@pytest.fixture
def reveal_logs(monkeypatch, caplog):
    monkeypatch.setattr(public_routes, "_DRAW_REVEAL_LOG_STATES", OrderedDict(), raising=False)
    caplog.set_level(logging.INFO, logger="public.draw_reveal")
    return caplog


def _serve_draw(payload, *, source="cache"):
    if source == "site-page":
        ctx = make_ctx("/api/public/site-page?site_id=10&lottery_type=3")
        with patch("routes.public_routes.get_public_latest_draw", return_value=payload):
            public_routes._send_site_page(ctx, {"site": {"id": 10}, "draw": payload, "modules": []}, TAIWAN)
        return response_json(ctx)["draw"]
    snapshots = _Snapshots(latest=payload if source == "cache" else None)
    ctx = _with_snapshots(make_ctx("/api/public/latest-draw?lottery_type=3"), snapshots)
    if source == "db":
        with patch("routes.public_routes.get_public_latest_draw", return_value=payload):
            public_routes.latest_draw(ctx)
    else:
        with patch("routes.public_routes.get_public_latest_draw", return_value=payload):
            public_routes.latest_draw(ctx)
    return response_json(ctx)


@pytest.mark.parametrize("source", ["cache", "db", "site-page"])
def test_each_public_outlet_reports_progress_without_logging_numbers(source, reveal_logs):
    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        response = _serve_draw(_payload(), source=source)
    records = [record for record in reveal_logs.records if record.name == "public.draw_reveal"]
    assert response["revealed_count"] == 1
    assert len(records) == 1
    metadata = records[0].result
    assert metadata["source"] == source
    assert metadata["current_issue"] == "2026277"
    assert metadata["lottery_type_id"] == 3
    assert metadata["revealed_count"] == 1
    assert metadata["is_complete"] is False
    assert metadata["server_now"] == response["server_now"]
    assert set(metadata).isdisjoint({"numbers", "result_balls", "special_ball"})


def test_progress_logging_deduplicates_polling_but_keeps_new_counts(reveal_logs):
    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        _serve_draw(_payload())
        _serve_draw(_payload(), source="site-page")
    with patch("public.draw_reveal.beijing_now", return_value=_at(25)):
        _serve_draw(_payload(), source="db")
        _serve_draw(_payload())
    records = [record for record in reveal_logs.records if record.name == "public.draw_reveal"]
    assert [record.result["revealed_count"] for record in records] == [1, 2]


def test_blocked_anchor_logging_reports_reason_and_recovery(reveal_logs):
    blocked = {**_payload(reveal_start="invalid"), "draw_time": "invalid"}
    with patch("public.draw_reveal.beijing_now", return_value=_at(-1)):
        _serve_draw(blocked)
        _serve_draw(blocked)
        _serve_draw(_payload())
    records = [record for record in reveal_logs.records if record.name == "public.draw_reveal"]
    assert len(records) == 2
    assert records[0].levelno == logging.WARNING
    assert records[0].result["reason"] == "missing_anchor"
    assert records[0].result["revealed_count"] == 0
    assert records[1].result["reason"] == ""


def test_concurrent_polling_emits_one_progress_record(reveal_logs):
    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: _serve_draw(_payload()), range(32)))
    assert all(response["revealed_count"] == 1 for response in responses)
    records = [record for record in reveal_logs.records if record.name == "public.draw_reveal"]
    assert len(records) == 1


def test_progress_deduplication_evicts_old_issues_when_bounded(monkeypatch, reveal_logs):
    monkeypatch.setattr(public_routes, "_DRAW_REVEAL_LOG_MAX_ISSUES", 3, raising=False)
    with patch("public.draw_reveal.beijing_now", return_value=_at(0)):
        for issue in ("2026277", "2026278", "2026279", "2026280", "2026277"):
            _serve_draw({**_payload(), "current_issue": issue})
    records = [record for record in reveal_logs.records if record.name == "public.draw_reveal"]
    assert [record.result["current_issue"] for record in records] == ["2026277", "2026278", "2026279", "2026280", "2026277"]
