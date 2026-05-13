"""SiteContext 单元测试。

测试 path site_id 解析、domain 解析、web 校验等场景。
注意：这些测试需要 mock 数据库连接。
"""

from __future__ import annotations

from app_http.site_context import (
    SiteContext,
    validate_web_matches_site,
    extract_site_web_value,
    _coalesce_site_id,
)


def _make_site_ctx(site_id=1, web_id=7, name="测试站点", domain="test.example.com",
                   lottery_type_id=3, enabled=True):
    return SiteContext(
        site_id=site_id,
        web_id=web_id,
        name=name,
        domain=domain,
        lottery_type_id=lottery_type_id,
        enabled=enabled,
    )


# ── validate_web_matches_site ──────────────────────────

def test_validate_web_none_is_ok():
    """web_value 为空时不抛异常。"""
    site = _make_site_ctx(web_id=7)
    validate_web_matches_site(site, None)  # 不应抛异常


def test_validate_web_empty_string_is_ok():
    site = _make_site_ctx(web_id=7)
    validate_web_matches_site(site, "")


def test_validate_web_matches():
    site = _make_site_ctx(web_id=7)
    validate_web_matches_site(site, 7)
    validate_web_matches_site(site, "7")


def test_validate_web_mismatch_raises():
    """web 与站点 web_id 不一致时抛 ForbiddenError。"""
    from core.errors import ForbiddenError
    site = _make_site_ctx(web_id=7)
    try:
        validate_web_matches_site(site, 4)
        assert False, "应该抛异常"
    except ForbiddenError as e:
        assert "web_id=7" in str(e)
        assert "4" in str(e) or "只允许访问" in str(e)


def test_validate_web_invalid_type_raises():
    """web 值非整数时抛 ValidationError。"""
    from core.errors import ValidationError
    site = _make_site_ctx(web_id=7)
    try:
        validate_web_matches_site(site, "abc")
        assert False, "应该抛异常"
    except ValidationError:
        pass


# ── extract_site_web_value ─────────────────────────────

def test_extract_web_from_query():
    assert extract_site_web_value(query={"web": ["7"]}) == "7"


def test_extract_web_id_from_query():
    assert extract_site_web_value(query={"web_id": ["5"]}) == "5"


def test_extract_web_from_body():
    assert extract_site_web_value(body={"web": 7}) == 7


def test_extract_web_id_from_body():
    assert extract_site_web_value(body={"web_id": 5}) == 5


def test_extract_web_none_when_missing():
    assert extract_site_web_value() is None


def test_extract_web_body_priority_over_query():
    """body 中的 web 值优先于 query。"""
    result = extract_site_web_value(
        query={"web": ["3"]},
        body={"web": 7},
    )
    assert result == 7


# ── _coalesce_site_id ─────────────────────────────────

def test_coalesce_path_priority():
    """path_site_id 优先级最高。"""
    assert _coalesce_site_id(10, {"site_id": ["5"]}, {"site_id": 3}) == 10


def test_coalesce_query_fallback():
    """无 path 时用 query。"""
    assert _coalesce_site_id(None, {"site_id": ["5"]}, {}) == 5


def test_coalesce_body_fallback():
    """无 path 和 query 时用 body。"""
    assert _coalesce_site_id(None, {}, {"site_id": 3}) == 3


def test_coalesce_none_when_all_missing():
    assert _coalesce_site_id(None, {}, {}) is None


# ── SiteContext 不可变 ─────────────────────────────────

def test_site_context_is_frozen():
    site = _make_site_ctx()
    try:
        site.web_id = 99  # type: ignore
        assert False, "dataclass frozen 应该阻止修改"
    except Exception:
        pass
