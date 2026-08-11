from __future__ import annotations

from pathlib import Path
import re


def test_twsaimahui_manifest_covers_live_scripts_but_not_commented_script():
    from domains.prediction.site_page_dependencies import dependencies_for_site

    dependencies = dependencies_for_site("twsaimahui")
    source_paths = {item.source_path for item in dependencies}
    mode_ids = {mode_id for item in dependencies for mode_id in item.mode_ids}

    assert "static/js/067sanzipw.js" in source_paths
    assert 470 in mode_ids
    assert "static/js/020nn4x.js" not in source_paths
    assert 24 not in mode_ids


def test_twsaimahui_blocked_six_not_in_source_never_authorizes_a_mode():
    from domains.prediction.site_page_dependencies import (
        blocked_dependencies_for_site,
        required_mode_ids_for_site_key,
    )

    blocked = blocked_dependencies_for_site("twsaimahui")

    assert any(item.source_path == "static/js/019liubuzhong.js" for item in blocked)
    assert 333 not in required_mode_ids_for_site_key("twsaimahui")


def test_shengshi8800_manifest_matches_live_vendor_scripts_only():
    from domains.prediction.site_page_dependencies import (
        dependencies_for_site,
        required_mode_ids_for_site_key,
    )

    dependencies = dependencies_for_site("shengshi8800")
    source_paths = {item.source_path for item in dependencies}
    expected_mode_ids = {
        2, 3, 8, 12, 20, 26, 28, 31, 34, 38, 42, 43, 45, 46, 48,
        49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 65, 68,
        108, 151, 197, 244, 246, 331,
    }

    assert set(required_mode_ids_for_site_key("shengshi8800")) == expected_mode_ids
    assert "static/js/018shu3x.js" in source_paths
    assert "static/js/kj.js" not in source_paths
    assert 64 not in expected_mode_ids


def test_shengshi8800_manifest_source_paths_match_live_prediction_scripts():
    """The site-4 manifest may not silently drift from its reachable shell."""
    from domains.prediction.site_page_dependencies import dependencies_for_site

    source_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "public"
        / "vendor"
        / "shengshi8800"
        / "index.html"
    )
    html = source_path.read_text(encoding="utf-8")
    uncommented_html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    live_scripts = set(
        re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', uncommented_html, flags=re.IGNORECASE)
    )
    non_prediction_scripts = {
        "static/js/jquery.js",
        "static/js/ajax_interceptor.js",
        "static/js/util.js",
        "static/js/url_zlz_yuming_ht.js",
        "static/js/handleSelect.js",
        "static/js/djck.js",
        "static/js/kj.js",
        "static/js/tu1.js",
            "/vendor/_shared/managed-site-links.js",
            "/vendor/_shared/forced-announcement.js",
    }

    assert {
        item.source_path for item in dependencies_for_site("shengshi8800")
    } == live_scripts - non_prediction_scripts


def test_twjinniu_manifest_matches_its_homepage_provider_sources():
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    assert {56, 49, 151, 117, 123, 474, 476, 484} <= set(
        required_mode_ids_for_site_key("twjinniu")
    )


def test_twjinniu_manifest_covers_every_live_article_provider():
    """Article routes are accessible pages, not optional homepage extras."""
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    assert {
        5,
        12,
        14,
        20,
        26,
        38,
        47,
        48,
        53,
        66,
        74,
        132,
        143,
        144,
        198,
        279,
        472,
        479,
        480,
        481,
        482,
        483,
    } <= set(required_mode_ids_for_site_key("twjinniu"))


def test_twcf888_manifest_includes_live_articles_but_not_snapshot_or_blocked_articles():
    from domains.prediction.site_page_dependencies import (
        blocked_dependencies_for_site,
        required_mode_ids_for_site_key,
    )

    blocked = blocked_dependencies_for_site("twcf888")

    assert 470 in required_mode_ids_for_site_key("twcf888")
    assert any("广东5兄弟" in item.blocked_reason for item in blocked)


def test_twsaimahui_sixteen_code_page_uses_the_compatibility_route_mode():
    from domains.prediction.site_page_dependencies import dependencies_for_site

    dependency = next(
        item
        for item in dependencies_for_site("twsaimahui")
        if item.source_path == "static/js/035ma16.js"
    )

    assert dependency.endpoint == "getCode"
    assert dependency.params == (("num", "16"),)
    assert dependency.mode_ids == (9,)


def test_kaijiang_compatibility_route_maps_sixteen_codes_to_mode_nine():
    route_path = (
        Path(__file__).resolve().parents[4]
        / "frontend"
        / "app"
        / "api"
        / "kaijiang"
        / "[[...path]]"
        / "route.ts"
    )
    route_text = route_path.read_text(encoding="utf-8")

    assert 'num === "16" ? 9' in route_text


def test_generation_assurance_marks_only_verified_rules_as_controlled_future():
    from domains.prediction.site_page_dependencies import generation_assurance_for_mode

    assert generation_assurance_for_mode(470) == "controlled_future"
    assert generation_assurance_for_mode(50) == "history_only"
    assert generation_assurance_for_mode(476) == "history_only"
    assert generation_assurance_for_mode(None, blocked_reason="no exact source") == "blocked"


def test_twcaibawang_manifest_covers_every_rendered_public_and_vendor_source():
    from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key

    assert {
        12, 26, 34, 38, 44, 47, 49, 50, 52, 54, 56, 57, 58, 60,
        69, 108, 151, 197, 472, 474, 475, 476, 478, 479, 480, 481,
        482, 483, 484,
    } <= set(required_mode_ids_for_site_key("twcaibawang"))
