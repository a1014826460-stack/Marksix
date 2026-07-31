import json

from db import connect
from database.versioned_migrations import _install_twjsz666_site_profile
from domains.prediction.site_page_dependencies import (
    dependencies_for_site,
    required_mode_ids_for_site_key,
)


EXPECTED_MODE_IDS = (
    57, 493, 14, 492, 494, 38, 51, 20, 74, 58, 473, 56, 470, 50,
    54, 49, 31, 491, 52, 495, 483, 34, 46, 43, 47, 69, 151,
)

EXPECTED_ARTICLE_MODULES = {
    "/vendor/twjsz666/154.html": "daxiao",
    "/vendor/twjsz666/155.html": "selected_22_codes",
    "/vendor/twjsz666/156.html": "title_14",
    "/vendor/twjsz666/157.html": "three_head_four_tail",
    "/vendor/twjsz666/158.html": "steady_kill_7_codes",
    "/vendor/twjsz666/159.html": "shuangbo",
    "/vendor/twjsz666/160.html": "4xiao8ma",
    "/vendor/twjsz666/161.html": "juesha1wei",
    "/vendor/twjsz666/162.html": "title_74",
    "/vendor/twjsz666/163.html": "jueshabanbo",
    "/vendor/twjsz666/164.html": "juesha2xiao",
    "/vendor/twjsz666/165.html": "pt1xiao",
    "/vendor/twjsz666/166.html": "pt3xiao",
    "/vendor/twjsz666/167.html": "yijuzhenyan",
}


def test_twjsz666_dependencies_are_reviewed_and_nonempty():
    mode_ids = required_mode_ids_for_site_key("twjsz666")
    assert mode_ids == EXPECTED_MODE_IDS


def test_twjsz666_article_and_composite_sources_are_explicit():
    dependencies = dependencies_for_site("twjsz666")
    article_modules = {
        dependency.page_path: dependency.endpoint
        for dependency in dependencies
        if dependency.page_path.startswith("/vendor/twjsz666/")
    }
    homepage_modules = {
        dependency.endpoint
        for dependency in dependencies
        if dependency.page_path == "/twjsz666"
    }

    assert article_modules == EXPECTED_ARTICLE_MODULES
    assert {
        "sitouzhongte",
        "ma24",
        "selected_22_codes",
        "9xzt",
        "danshuang4xiao",
        "6xzt",
        "4xiao8ma",
        "pt2xiao",
        "wuxiao_wuma",
    } <= homepage_modules


def test_twjsz666_profile_registers_site_11_and_modules(tmp_path):
    db_path = str(tmp_path / "twjsz666.sqlite3")
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE site_blueprint_profiles (blueprint_name TEXT PRIMARY KEY, required_mode_ids_json TEXT NOT NULL, known_unavailable_mode_ids_json TEXT NOT NULL, blocked_items_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE managed_sites (id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL, domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL, blueprint_name TEXT, announcement TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE site_prediction_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER NOT NULL, mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL, sort_order INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, title TEXT, UNIQUE(site_id, mechanism_key))")
        _install_twjsz666_site_profile(conn)
        site = conn.execute("SELECT id, web_id, name, domain, blueprint_name FROM managed_sites WHERE id = 11").fetchone()
        profile = conn.execute("SELECT required_mode_ids_json FROM site_blueprint_profiles WHERE blueprint_name = 'twjsz666'").fetchone()

    assert dict(site) == {
        "id": 11,
        "web_id": 11,
        "name": "台湾金手指",
        "domain": "www.twjsz666.com",
        "blueprint_name": "twjsz666",
    }
    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == required_mode_ids_for_site_key("twjsz666")
