import json

from db import connect
from database.versioned_migrations import _install_twsyw_site_profile
from domains.prediction.site_module_blueprints import get_blueprint_name_for_site
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


EXPECTED_MODE_IDS = (14, 42, 49, 493, 38, 78, 57, 66, 34, 31, 479, 143, 5, 12, 279, 56, 132, 26, 476, 475)


def test_twsyw_dependencies_are_reviewed_and_complete():
    assert required_mode_ids_for_site_key("twsyw") == EXPECTED_MODE_IDS


def test_twsyw_profile_matching_does_not_shadow_existing_vendor_sites():
    assert get_blueprint_name_for_site({"web_id": 13}) == "twsyw"
    assert get_blueprint_name_for_site({"web_id": 12}) == "twwanli"
    assert get_blueprint_name_for_site({"web_id": 11}) == "twjsz666"


def test_twsyw_profile_registers_web_13_and_authorizes_modules(tmp_path):
    db_path = str(tmp_path / "twsyw.sqlite3")
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE site_blueprint_profiles (blueprint_name TEXT PRIMARY KEY, required_mode_ids_json TEXT NOT NULL, known_unavailable_mode_ids_json TEXT NOT NULL, blocked_items_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE managed_sites (id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL, domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL, blueprint_name TEXT, announcement TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE site_prediction_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER NOT NULL, mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL, sort_order INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, title TEXT, UNIQUE(site_id, mechanism_key))")
        _install_twsyw_site_profile(conn)
        site = conn.execute("SELECT id, web_id, name, domain, blueprint_name FROM managed_sites WHERE id = 13").fetchone()
        profile = conn.execute("SELECT required_mode_ids_json FROM site_blueprint_profiles WHERE blueprint_name = 'twsyw'").fetchone()
        modules = conn.execute("SELECT COUNT(*) AS total FROM site_prediction_modules WHERE site_id = 13").fetchone()

    assert dict(site) == {"id": 13, "web_id": 13, "name": "台湾神预网", "domain": "www.twsyw.com", "blueprint_name": "twsyw"}
    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == EXPECTED_MODE_IDS
    assert int(modules["total"]) == len(EXPECTED_MODE_IDS)
