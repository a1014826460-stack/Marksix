from __future__ import annotations

import json

import pytest

from cache.memory import MemoryCacheStore
from cache.public_snapshots import (
    PublicDrawSnapshots,
    current_period_snapshot_keys,
    latest_draw_snapshot_keys,
)


def _latest_draw_payload() -> dict[str, object]:
    return {
        "current_issue": "2026131",
        "draw_time": "2026-05-14 22:30:00",
        "reveal_start": "2026-05-14 22:30:00",
        "result_balls": [
            {"value": "01", "zodiac": "马", "color": "red"},
            {"value": "02", "zodiac": "蛇", "color": "blue"},
        ],
        "special_ball": {"value": "07", "zodiac": "鼠", "color": "red"},
    }


def _current_period_payload() -> dict[str, object]:
    return {
        "lottery_type_id": 3,
        "lottery_name": "台湾彩",
        "current_period": "2026131",
        "current_year": 2026,
        "current_term": 131,
    }


def test_snapshot_keys_are_namespaced_by_schema_endpoint_and_lottery_type():
    latest = latest_draw_snapshot_keys(3, "2026-131")
    period = current_period_snapshot_keys(3, "2026-131")

    assert latest.pointer_key == "public:draw-snapshot:v1:lottery:3:latest-draw:pointer"
    assert latest.version_key == "public:draw-snapshot:v1:lottery:3:latest-draw:version:2026-131"
    assert period.pointer_key == "public:draw-snapshot:v1:lottery:3:current-period:pointer"
    assert period.version_key == "public:draw-snapshot:v1:lottery:3:current-period:version:2026-131"


def test_publish_opened_latest_draw_makes_only_complete_payload_visible():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache, clock=lambda: 1234.5)
    payload = _latest_draw_payload()

    published = snapshots.publish_latest_draw(
        3,
        payload,
        version="2026-131",
        is_opened=True,
    )

    assert published is True
    assert snapshots.get_latest_draw(3) == payload
    raw = cache.get(latest_draw_snapshot_keys(3, "2026-131").version_key)
    assert raw is not None
    assert json.loads(raw) == {
        "schema_version": 1,
        "snapshot_type": "latest_draw",
        "lottery_type_id": 3,
        "published_at": 1234.5,
        "payload": payload,
    }


def test_republish_without_explicit_timestamp_reuses_the_first_one():
    """站点/接口重建路径不带 `published_at` 时也必须逐字节可复现。

    版本键不可变，而 envelope 带发布时间：若每次都用当前时钟，同一载荷重复发布就会
    写出不同字节并被拒绝（2026-10-05 同 prediction-snapshot 的时钟粒度问题）。
    """
    cache = MemoryCacheStore()
    ticks = iter([500.0, 500.25])
    snapshots = PublicDrawSnapshots(cache, ttl_seconds=300, clock=lambda: next(ticks))
    payload = _latest_draw_payload()
    version_key = latest_draw_snapshot_keys(3, "2026-131").version_key

    assert snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True) is True
    first = json.loads(cache.get(version_key))

    assert snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True) is True
    second = json.loads(cache.get(version_key))

    assert first == second
    assert first["published_at"] == 500.0
    assert snapshots.get_latest_draw(3) == payload


def test_outbox_retry_keeps_its_own_explicit_timestamp():
    """显式传入 `published_at`（outbox 重试）时必须原样使用，不被首次发布时刻覆盖。"""
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache, ttl_seconds=300, clock=lambda: 900.0)
    payload = _latest_draw_payload()

    snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True, published_at=777.0)

    envelope = json.loads(cache.get(latest_draw_snapshot_keys(3, "2026-131").version_key))
    assert envelope["published_at"] == 777.0


def test_future_issue_is_not_published_and_cannot_replace_opened_snapshot():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    opened_payload = _latest_draw_payload()
    snapshots.publish_latest_draw(3, opened_payload, version="2026-131", is_opened=True)

    future_payload = _latest_draw_payload() | {"current_issue": "2026132"}
    published = snapshots.publish_latest_draw(
        3,
        future_payload,
        version="2026-132",
        is_opened=False,
    )

    assert published is False
    assert snapshots.get_latest_draw(3) == opened_payload
    assert cache.get(latest_draw_snapshot_keys(3, "2026-132").version_key) is None


@pytest.mark.parametrize("forbidden_key", ["numbers", "res_sx", "res_color", "is_opened"])
def test_public_snapshot_rejects_raw_or_future_issue_fields(forbidden_key: str):
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    payload = _latest_draw_payload() | {forbidden_key: "secret"}

    with pytest.raises(ValueError, match="not allowed"):
        snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True)

    assert snapshots.get_latest_draw(3) is None


def test_invalid_pointer_or_invalid_json_is_treated_as_a_cache_miss():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    keys = latest_draw_snapshot_keys(3, "2026-131")

    cache.set(keys.pointer_key, b"\xff", ttl_seconds=60)
    assert snapshots.get_latest_draw(3) is None

    cache.set(keys.pointer_key, keys.version_key.encode("utf-8"), ttl_seconds=60)
    cache.set(keys.version_key, b"not-json", ttl_seconds=60)
    assert snapshots.get_latest_draw(3) is None


def test_pointer_to_another_snapshot_scope_is_treated_as_a_cache_miss():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    latest_keys = latest_draw_snapshot_keys(3, "2026-131")
    other_keys = current_period_snapshot_keys(3, "2026-131")
    cache.set(latest_keys.pointer_key, other_keys.version_key.encode("utf-8"), ttl_seconds=60)
    cache.set(
        other_keys.version_key,
        json.dumps(
            {
                "schema_version": 1,
                "snapshot_type": "latest_draw",
                "lottery_type_id": 3,
                "published_at": 1234.5,
                "payload": _latest_draw_payload(),
            }
        ).encode("utf-8"),
        ttl_seconds=60,
    )

    assert snapshots.get_latest_draw(3) is None


def test_latest_draw_ball_may_include_wuxing_element_field():
    snapshots = PublicDrawSnapshots(MemoryCacheStore())
    payload = _latest_draw_payload()
    payload["result_balls"] = [
        {"value": "01", "zodiac": "马", "color": "red", "element": "金"},
        {"value": "02", "zodiac": "蛇", "color": "blue", "element": "水"},
    ]
    payload["special_ball"] = {"value": "07", "zodiac": "鼠", "color": "red", "element": "木"}

    published = snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True)

    assert published is True
    assert snapshots.get_latest_draw(3) == payload


@pytest.mark.parametrize("nested_key", ["numbers", "res_sx", "res_color", "is_opened"])
def test_latest_draw_rejects_forbidden_database_fields_nested_in_a_ball(nested_key: str):
    snapshots = PublicDrawSnapshots(MemoryCacheStore())
    payload = _latest_draw_payload()
    payload["result_balls"] = [{"value": "01", "zodiac": "马", "color": "red", nested_key: "secret"}]

    with pytest.raises(ValueError, match="ball"):
        snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True)


def test_latest_draw_rejects_ball_with_an_unexpected_type_or_field_set():
    snapshots = PublicDrawSnapshots(MemoryCacheStore())
    payload = _latest_draw_payload()
    payload["special_ball"] = {"value": 7, "zodiac": "鼠", "color": "red"}

    with pytest.raises(ValueError, match="ball"):
        snapshots.publish_latest_draw(3, payload, version="2026-131", is_opened=True)


@pytest.mark.parametrize("published_at", [True, float("inf"), float("nan")])
def test_nonfinite_or_boolean_published_at_is_treated_as_a_cache_miss(published_at: object):
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    keys = latest_draw_snapshot_keys(3, "2026-131")
    cache.set(keys.pointer_key, keys.version_key.encode("utf-8"), ttl_seconds=60)
    cache.set(
        keys.version_key,
        json.dumps(
            {
                "schema_version": 1,
                "snapshot_type": "latest_draw",
                "lottery_type_id": 3,
                "published_at": published_at,
                "payload": _latest_draw_payload(),
            }
        ).encode("utf-8"),
        ttl_seconds=60,
    )

    assert snapshots.get_latest_draw(3) is None


def test_huge_integer_published_at_does_not_raise_during_cache_read():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    keys = latest_draw_snapshot_keys(3, "2026-131")
    cache.set(keys.pointer_key, keys.version_key.encode("utf-8"), ttl_seconds=60)
    cache.set(
        keys.version_key,
        json.dumps(
            {
                "schema_version": 1,
                "snapshot_type": "latest_draw",
                "lottery_type_id": 3,
                "published_at": 10**1000,
                "payload": _latest_draw_payload(),
            }
        ).encode("utf-8"),
        ttl_seconds=60,
    )

    assert snapshots.get_latest_draw(3) == _latest_draw_payload()


def test_current_period_snapshot_has_its_own_typed_payload_and_pointer():
    cache = MemoryCacheStore()
    snapshots = PublicDrawSnapshots(cache)
    payload = _current_period_payload()

    published = snapshots.publish_current_period(
        3,
        payload,
        version="2026-131",
        is_opened=True,
    )

    assert published is True
    assert snapshots.get_current_period(3) == payload
    assert snapshots.get_latest_draw(3) is None


def test_current_period_rejects_a_payload_for_another_lottery_type():
    snapshots = PublicDrawSnapshots(MemoryCacheStore())

    with pytest.raises(ValueError, match="lottery_type_id"):
        snapshots.publish_current_period(
            3,
            _current_period_payload() | {"lottery_type_id": 1},
            version="2026-131",
            is_opened=True,
        )
