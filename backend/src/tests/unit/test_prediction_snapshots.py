"""预测资料快照：版本发布、载荷校验、回落与开关。"""

from __future__ import annotations

import json

import pytest

from cache.contracts import CacheUnavailable
from cache.memory import MemoryCacheStore
from cache.prediction_snapshots import (
    KIND_HOMEPAGE,
    KIND_LEGACY,
    KIND_SITE,
    PublicPredictionSnapshots,
    payload_is_cacheable,
    read_through,
    reset_enabled_cache,
    snapshot_enabled,
    snapshot_keys,
    snapshot_version,
)

LEGACY_PAYLOAD = {
    "data": [
        {"content": "蛇,猪,猴", "res_code": "01,27,37,20,43,02,10", "res_sx": "马,龙,马,猪,鼠,蛇,鸡", "term": "266"}
    ]
}


def _snapshots(cache: MemoryCacheStore | None = None, ttl: int = 300) -> PublicPredictionSnapshots:
    return PublicPredictionSnapshots(cache or MemoryCacheStore(), ttl_seconds=ttl)


def test_publish_then_get_roundtrip():
    snapshots = _snapshots()
    assert snapshots.publish(KIND_LEGACY, "web9", 3, "getPingte-abc123", LEGACY_PAYLOAD) is True
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getPingte-abc123") == LEGACY_PAYLOAD


def test_get_returns_none_for_other_keys():
    snapshots = _snapshots()
    snapshots.publish(KIND_LEGACY, "web9", 3, "getPingte-abc123", LEGACY_PAYLOAD)
    assert snapshots.get(KIND_LEGACY, "web9", 2, "getPingte-abc123") is None
    assert snapshots.get(KIND_LEGACY, "web8", 3, "getPingte-abc123") is None
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc123") is None
    assert snapshots.get(KIND_SITE, "web9", 3, "getPingte-abc123") is None


def test_version_is_content_addressed_so_changed_payload_swaps_pointer():
    cache = MemoryCacheStore()
    snapshots = _snapshots(cache)
    snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", LEGACY_PAYLOAD)
    updated = {"data": [{"content": "虎,兔", "term": "266", "res_code": "", "res_sx": ""}]}
    snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", updated)
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") == updated
    # 同一内容重复发布是幂等的（旧版本键内容不可变）。
    snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", updated)
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") == updated


def test_invalidate_drops_pointer():
    snapshots = _snapshots()
    snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", LEGACY_PAYLOAD)
    snapshots.invalidate(KIND_LEGACY, "web9", 3, "getTou-abc")
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") is None


@pytest.mark.parametrize("field", ["_simulation_should_hit", "should_hit", "truth_source", "future_truth"])
def test_publish_rejects_internal_marker_fields(field):
    snapshots = _snapshots()
    payload = {"data": [{"content": "蛇", field: True}]}
    with pytest.raises(ValueError):
        snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", payload)
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") is None


def test_public_is_opened_field_is_allowed():
    """`is_opened` 是公开历史行字段（实测只出现已开奖行），不应阻止缓存。"""
    snapshots = _snapshots()
    payload = {"data": [{"term": "266", "content": "蛇,猪,猴", "is_opened": True}]}
    assert snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", payload) is True
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") == payload


def test_site_page_shape_without_data_key_is_cacheable():
    """`/api/public/site-page` 的顶层是 {site, draw, modules}，没有 data 键。"""
    snapshots = _snapshots()
    payload = {
        "site": {"id": 9, "web_id": 9},
        "draw": {"current_issue": "2026266", "result_balls": []},
        "modules": [{"mechanism_key": "pt1xiao", "history": [{"term": 266, "is_opened": True}]}],
    }
    assert payload_is_cacheable(KIND_SITE, payload) is True
    assert snapshots.publish(KIND_SITE, "site9", 3, "page-abc", payload) is True
    assert snapshots.get(KIND_SITE, "site9", 3, "page-abc") == payload


def test_nested_internal_marker_is_rejected():
    snapshots = _snapshots()
    payload = {"data": {"modules": [{"rows": [{"raw": {"_simulation_should_hit": 1}}]}]}}
    with pytest.raises(ValueError):
        snapshots.publish(KIND_SITE, "site9", 3, "page-abc", payload)


def test_empty_legacy_payload_is_not_cacheable():
    snapshots = _snapshots()
    empty = {"data": []}
    assert payload_is_cacheable(KIND_LEGACY, empty) is False
    assert snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", empty) is False
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") is None


def test_legacy_rows_shape_is_cacheable():
    """`/api/legacy/module-rows` 的载荷是 {modes_id,title,table_name,rows}。"""
    from cache.prediction_snapshots import KIND_LEGACY_ROWS

    snapshots = _snapshots()
    payload = {
        "modes_id": 56,
        "title": "平特一肖",
        "table_name": "mode_payload_56",
        "rows": [{"term": "266", "content": "蛇,猪,猴", "res_code": "", "res_sx": ""}],
    }
    assert payload_is_cacheable(KIND_LEGACY_ROWS, payload) is True
    assert snapshots.publish(KIND_LEGACY_ROWS, "web9", 3, "rows-56-8-abc", payload) is True
    assert snapshots.get(KIND_LEGACY_ROWS, "web9", 3, "rows-56-8-abc") == payload
    assert payload_is_cacheable(KIND_LEGACY_ROWS, {"rows": []}) is False
    # rows 不是列表时直接拒绝缓存（结构校验由可缓存性把关）。
    assert snapshots.publish(KIND_LEGACY_ROWS, "web9", 3, "rows-56-8-abc", {"rows": "nope"}) is False
    # 行内的内部标记仍然会被递归拒绝。
    with pytest.raises(ValueError):
        snapshots.publish(
            KIND_LEGACY_ROWS,
            "web9",
            3,
            "rows-56-8-abc",
            {"rows": [{"term": "266", "_simulation_should_hit": 1}]},
        )


def test_generation_bump_invalidates_site_and_lottery_type():
    """开奖/生成/后台改资料通过代际 +1 让整片快照失效（无需按前缀扫描）。"""
    snapshots = _snapshots()
    payload_a = {"data": [{"term": "266", "content": "蛇"}]}
    payload_b = {"rows": [{"term": "266", "content": "虎"}]}
    from cache.prediction_snapshots import KIND_LEGACY_ROWS

    assert snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-aaa", payload_a) is True
    assert snapshots.publish(KIND_LEGACY_ROWS, "web9", 3, "rows-56-8-bbb", payload_b) is True
    assert snapshots.publish(KIND_LEGACY, "web8", 3, "getTou-aaa", payload_a) is True
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-aaa") == payload_a

    # 站点级 bump：只影响该站
    snapshots.bump_site("web9", 3)
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-aaa") is None
    assert snapshots.get(KIND_LEGACY_ROWS, "web9", 3, "rows-56-8-bbb") is None
    assert snapshots.get(KIND_LEGACY, "web8", 3, "getTou-aaa") == payload_a

    # 彩种级 bump：影响所有站点
    snapshots.bump_lottery_type(3)
    assert snapshots.get(KIND_LEGACY, "web8", 3, "getTou-aaa") is None


def test_generation_bump_is_monotonic_and_survives_corrupt_values():
    from cache.prediction_snapshots import generation_key_for_lottery_type

    cache = MemoryCacheStore()
    snapshots = PublicPredictionSnapshots(cache, ttl_seconds=300)
    snapshots.bump_lottery_type(3)
    assert cache.get(generation_key_for_lottery_type(3)) == b"1"
    snapshots.bump_lottery_type(3)
    assert cache.get(generation_key_for_lottery_type(3)) == b"2"
    # 脏值按 0 处理，不会让 bump 失败
    cache.set(generation_key_for_lottery_type(3), b"not-a-number", ttl_seconds=60)
    snapshots.bump_lottery_type(3)
    assert cache.get(generation_key_for_lottery_type(3)) == b"1"


def test_generation_token_changes_the_key():
    first = snapshot_keys(KIND_LEGACY, "web9", 3, "getTou-abc", "abc", "0.0")
    second = snapshot_keys(KIND_LEGACY, "web9", 3, "getTou-abc", "abc", "1.0")
    assert first.pointer_key != second.pointer_key
    with pytest.raises(ValueError):
        snapshot_keys(KIND_LEGACY, "web9", 3, "getTou-abc", "abc", "bad gen")


def test_missing_known_top_level_key_is_rejected():
    snapshots = _snapshots()
    with pytest.raises(ValueError):
        snapshots.publish(KIND_HOMEPAGE, "site9", 3, "3-8-all", {"modules": []})
    with pytest.raises(ValueError):
        snapshots.publish(KIND_SITE, "site9", 3, "page-abc", {"unexpected": []})


def test_tampered_version_payload_is_ignored():
    cache = MemoryCacheStore()
    snapshots = _snapshots(cache)
    snapshots.publish(KIND_LEGACY, "web9", 3, "getTou-abc", LEGACY_PAYLOAD)
    keys = snapshot_keys(KIND_LEGACY, "web9", 3, "getTou-abc", snapshot_version(LEGACY_PAYLOAD))
    envelope = json.loads(cache.get(keys.version_key).decode("utf-8"))
    envelope["selector"] = "getTou-other"
    cache.set(keys.version_key, json.dumps(envelope).encode("utf-8"), ttl_seconds=300)
    assert snapshots.get(KIND_LEGACY, "web9", 3, "getTou-abc") is None


def test_read_through_publishes_and_reuses_cache():
    snapshots = _snapshots()
    calls = {"count": 0}

    def builder() -> dict:
        calls["count"] += 1
        return LEGACY_PAYLOAD

    first = read_through(
        snapshots, kind=KIND_LEGACY, site_ref="web9", lottery_type_id=3,
        selector="getTou-abc", builder=builder, db_path=None,
    )
    second = read_through(
        snapshots, kind=KIND_LEGACY, site_ref="web9", lottery_type_id=3,
        selector="getTou-abc", builder=builder, db_path=None,
    )
    assert first == second == LEGACY_PAYLOAD
    assert calls["count"] == 1


def test_read_through_falls_back_when_cache_unavailable():
    class BrokenCache(MemoryCacheStore):
        def get(self, key: str) -> bytes | None:  # type: ignore[override]
            raise CacheUnavailable("redis down")

        def publish_versioned(self, *args, **kwargs):  # type: ignore[override]
            raise CacheUnavailable("redis down")

    snapshots = PublicPredictionSnapshots(BrokenCache(), ttl_seconds=300)
    payload = read_through(
        snapshots, kind=KIND_LEGACY, site_ref="web9", lottery_type_id=3,
        selector="getTou-abc", builder=lambda: LEGACY_PAYLOAD, db_path=None,
    )
    assert payload == LEGACY_PAYLOAD


def test_read_through_without_snapshot_instance_builds_directly():
    payload = read_through(
        None, kind=KIND_LEGACY, site_ref="web9", lottery_type_id=3,
        selector="getTou-abc", builder=lambda: LEGACY_PAYLOAD, db_path=None,
    )
    assert payload == LEGACY_PAYLOAD


def test_snapshot_enabled_env_switch(monkeypatch):
    reset_enabled_cache()
    assert snapshot_enabled() is True
    monkeypatch.setenv("PREDICTION_SNAPSHOT_ENABLED", "0")
    reset_enabled_cache()
    assert snapshot_enabled() is False
    monkeypatch.setenv("PREDICTION_SNAPSHOT_ENABLED", "1")
    reset_enabled_cache()
    assert snapshot_enabled() is True
    reset_enabled_cache()


def test_snapshot_keys_reject_unsafe_tokens():
    with pytest.raises(ValueError):
        snapshot_keys(KIND_LEGACY, "web 9", 3, "getTou", "abc")
    with pytest.raises(ValueError):
        snapshot_keys("unknown", "web9", 3, "getTou", "abc")
    with pytest.raises(ValueError):
        snapshot_keys(KIND_LEGACY, "web9", 0, "getTou", "abc")
