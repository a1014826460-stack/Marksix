import json

from db import connect
from database.versioned_migrations import _install_twwanli_site_profile
from domains.prediction.site_module_blueprints import get_blueprint_name_for_site
from domains.prediction.site_page_dependencies import dependencies_for_site, required_mode_ids_for_site_key


EXPECTED_MODE_IDS = (14, 42, 49, 493, 38, 78, 57, 66, 34, 31, 479, 143, 5, 12, 279, 56, 54, 483, 132, 26, 53, 46, 63)


def test_twwanli_dependencies_are_reviewed_and_complete():
    assert required_mode_ids_for_site_key("twwanli") == EXPECTED_MODE_IDS


def test_twwanli_featured_post_pages_have_explicit_dependencies():
    actual = {
        item.page_path: item.endpoint
        for item in dependencies_for_site("twwanli")
        if item.page_path.startswith("/vendor/twwanli/")
    }
    assert actual == {
        "/vendor/twwanli/21.html": "pt1wei",
        "/vendor/twwanli/22.html": "pt1xiao",
        "/vendor/twwanli/25.html": "pt1wei",
        "/vendor/twwanli/26.html": "pt1xiao",
        "/vendor/twwanli/27.html": "title_14",
        "/vendor/twwanli/28.html": "sitouzhongte",
    }


def test_twwanli_profile_matching_does_not_shadow_twjsz666():
    assert get_blueprint_name_for_site({"web_id": 12}) == "twwanli"
    assert get_blueprint_name_for_site({"web_id": 11}) == "twjsz666"


def test_twwanli_profile_registers_web_12_and_authorizes_modules(tmp_path):
    db_path = str(tmp_path / "twwanli.sqlite3")
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE site_blueprint_profiles (blueprint_name TEXT PRIMARY KEY, required_mode_ids_json TEXT NOT NULL, known_unavailable_mode_ids_json TEXT NOT NULL, blocked_items_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE managed_sites (id INTEGER PRIMARY KEY, web_id INTEGER NOT NULL, name TEXT NOT NULL, domain TEXT, lottery_type_id INTEGER, enabled INTEGER NOT NULL, blueprint_name TEXT, announcement TEXT, notes TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE site_prediction_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, site_id INTEGER NOT NULL, mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL, sort_order INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, title TEXT, UNIQUE(site_id, mechanism_key))")
        _install_twwanli_site_profile(conn)
        site = conn.execute("SELECT id, web_id, name, domain, blueprint_name FROM managed_sites WHERE id = 12").fetchone()
        profile = conn.execute("SELECT required_mode_ids_json FROM site_blueprint_profiles WHERE blueprint_name = 'twwanli'").fetchone()
        modules = conn.execute("SELECT COUNT(*) AS total FROM site_prediction_modules WHERE site_id = 12").fetchone()

    assert dict(site) == {"id": 12, "web_id": 12, "name": "台湾万利网", "domain": "www.twwanli.com", "blueprint_name": "twwanli"}
    assert tuple(json.loads(str(profile["required_mode_ids_json"]))) == EXPECTED_MODE_IDS
    # mode 63（家野中特）是**动态注册**机制：它的 config 只在运行时有
    # `mode_payload_tables.modes_id=63` 且 `mode_payload_63` 有数据时由
    # `predict.registry_builder` 从表结构派生（key = `title_{modes_id}`）。
    # 这个 SQLite fixture 没有 mode_payload 元数据，因此 profile 里虽有 63，
    # 蓝图插入行时会被跳过（并记录 missing prediction configs 警告）。
    assert int(modules["total"]) == len(EXPECTED_MODE_IDS) - 1


def test_twwanli_profile_refresh_migration_is_idempotent_and_leaves_modules_alone(tmp_path):
    """线上 profile 重刷迁移：只改 site_blueprint_profiles，重复执行结果一致。

    授权行 `site_prediction_modules.status` 是 reconcile 脚本的职责，迁移不得触碰；
    因此这里预置 status=0 的 title_63 行，迁移跑完后必须仍是 0。
    """
    from database.versioned_migrations import _sync_twwanli_jiaye_zhongte_authorization

    db_path = str(tmp_path / "twwanli_mode_63_profile.sqlite3")
    with connect(db_path) as conn:
        conn.execute("CREATE TABLE site_blueprint_profiles (blueprint_name TEXT PRIMARY KEY, required_mode_ids_json TEXT NOT NULL, known_unavailable_mode_ids_json TEXT NOT NULL, blocked_items_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE site_prediction_modules (id INTEGER PRIMARY KEY, site_id INTEGER NOT NULL, mechanism_key TEXT NOT NULL, mode_id INTEGER NOT NULL, status INTEGER NOT NULL, updated_at TEXT)")
        conn.execute(
            "INSERT INTO site_blueprint_profiles VALUES ('twwanli', '[46]', '[]', '[]', 'old', 'old')"
        )
        conn.execute("INSERT INTO site_prediction_modules VALUES (1, 12, 'title_63', 63, 0, 'old')")

        _sync_twwanli_jiaye_zhongte_authorization(conn)
        first = conn.execute(
            "SELECT required_mode_ids_json, updated_at FROM site_blueprint_profiles WHERE blueprint_name = 'twwanli'"
        ).fetchone()
        _sync_twwanli_jiaye_zhongte_authorization(conn)
        second = conn.execute(
            "SELECT required_mode_ids_json, updated_at FROM site_blueprint_profiles WHERE blueprint_name = 'twwanli'"
        ).fetchone()
        module_row = conn.execute(
            "SELECT status, updated_at FROM site_prediction_modules WHERE id = 1"
        ).fetchone()

    assert tuple(json.loads(str(first["required_mode_ids_json"]))) == EXPECTED_MODE_IDS
    assert str(first["updated_at"]) != "old"
    # 第二次执行完全无副作用：值与时间戳都不再变化。
    assert dict(second) == dict(first)
    assert int(module_row["status"]) == 0
    assert str(module_row["updated_at"]) == "old"
