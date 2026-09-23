"""快照键派生：旧站 kaijiang 端点与站点资料聚合的缓存键。"""

from __future__ import annotations

from types import SimpleNamespace

from routes.legacy_routes import _legacy_kaijiang_snapshot_target
from routes.public_routes import _site_page_selector
from routes.vendor_routes import _modules_fingerprint


def _ctx(path: str, **query: str) -> SimpleNamespace:
    return SimpleNamespace(path=path, query={key: [value] for key, value in query.items()})


def test_legacy_target_derives_site_type_and_endpoint():
    target = _legacy_kaijiang_snapshot_target(
        _ctx("/api/kaijiang/getPingte", web="9", type="3", num="1")
    )
    assert target is not None
    site_ref, lottery_type, selector = target
    assert site_ref == "web9"
    assert lottery_type == 3
    assert selector.startswith("getPingte-")


def test_legacy_target_is_stable_across_cache_busters():
    first = _legacy_kaijiang_snapshot_target(
        _ctx("/api/kaijiang/getTou", web="9", type="3", num="3", _ts="111", callback="cb")
    )
    second = _legacy_kaijiang_snapshot_target(
        _ctx("/api/kaijiang/getTou", web="9", type="3", num="3", _ts="222", callback="cb2")
    )
    assert first == second


def test_legacy_target_changes_with_num_and_type():
    base = _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="9", type="3", num="3"))
    other_num = _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="9", type="3", num="5"))
    other_type = _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="9", type="2", num="3"))
    assert base != other_num
    assert base != other_type


def test_legacy_target_skips_curterm_and_incomplete_requests():
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/curTerm", type="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", type="3", num="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="9", num="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="9", type="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="0", type="3", num="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/getTou", web="x", type="3", num="3")) is None
    assert _legacy_kaijiang_snapshot_target(_ctx("/api/kaijiang/", web="9", type="3", num="3")) is None


def test_legacy_selector_only_contains_token_characters():
    target = _legacy_kaijiang_snapshot_target(
        _ctx("/api/kaijiang/get.Sha_Xiao-2", web="9", type="3", num="1")
    )
    assert target is not None
    selector = target[2]
    assert all(character.isalnum() or character in "._-" for character in selector)


def test_site_page_selector_is_stable_and_param_sensitive():
    base = _site_page_selector(3, 8, 9, 9, [], "www.twssz.com")
    assert base == _site_page_selector(3, 8, 9, 9, [], "WWW.TWSSZ.COM")
    assert base != _site_page_selector(3, 8, 1, 1000, [], "www.twssz.com")
    assert base != _site_page_selector(3, 12, 9, 9, [], "www.twssz.com")
    assert base != _site_page_selector(2, 8, 9, 9, [], "www.twssz.com")
    assert base != _site_page_selector(3, 8, 9, 9, [56], "www.twssz.com")


def test_modules_fingerprint_is_order_insensitive():
    assert _modules_fingerprint(["b", "a"]) == _modules_fingerprint(["a", "b"])
    assert _modules_fingerprint([]) == "all"
    assert _modules_fingerprint(["a"]) != _modules_fingerprint(["b"])
