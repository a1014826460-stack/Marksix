import json

from db import connect
from database.versioned_migrations import _install_twjsz666_site_profile
from domains.prediction.site_page_dependencies import required_mode_ids_for_site_key


EXPECTED_MODE_IDS = (54, 56, 57, 483, 472, 51, 58, 26, 50, 38, 470, 20, 473, 49, 31, 492, 491, 14, 74, 52, 493, 494, 495)


def test_twjsz666_dependencies_are_reviewed_and_nonempty():
    mode_ids = required_mode_ids_for_site_key("twjsz666")
    assert mode_ids == EXPECTED_MODE_IDS


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
