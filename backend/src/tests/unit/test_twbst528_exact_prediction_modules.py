from __future__ import annotations

from db import auto_increment_primary_key, connect
from domains.prediction.generation_rules import get_generation_rule
from predict.mechanisms import get_prediction_config


def test_twbst528_exact_prediction_modes_have_distinct_semantics():
    expected = {
        "daimingxiao": (486, 5, "zodiac"),
        "liuweichute": (487, 6, "tail"),
        "toudanshuang": (488, 5, "head_parity"),
        "liuxiaoliuma": (489, 6, "zodiac"),
        "shaliangbanbo": (490, 2, "half_wave_exclusion"),
        "gongshi_siw": (491, 4, "tail"),
        # 2026-10-01：三块中特面板的权威 mode。
        "jimei_xiongchou": (155, 1, "zodiac_group"),
        "qianhou_shengxiao": (133, 1, "zodiac_group"),
        "sanxiao_siwei_xiao": (117, 3, "zodiac"),
    }

    for key, (mode_id, label_count, rule_id) in expected.items():
        config = get_prediction_config(key)
        assert config.default_modes_id == mode_id
        assert config.label_count == label_count
        assert get_generation_rule(config).rule_id == rule_id


def test_twbst528_zhongte_mode_tables_are_bootstrapped(tmp_path):
    """三张新表（155/133/117）必须是 `content` 单列的 payload 表。"""
    from database.schema.legacy import ensure_twbst528_prediction_tables

    db_path = str(tmp_path / "twbst528_zhongte_modes.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY, filename TEXT, title TEXT,
                table_name TEXT, record_count INTEGER, is_image INTEGER,
                is_text INTEGER, created_at TEXT, updated_at TEXT
            )
            """
        )
        ensure_twbst528_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))

        for mode_id in (155, 133, 117):
            columns = set(conn.table_columns(f"mode_payload_{mode_id}"))
            assert {"content", "res_code", "res_sx", "web", "type", "term"}.issubset(columns)


def test_twbst528_zhongte_modes_authorized_after_migration_33(tmp_path):
    """迁移 33 必须把三个 mode 写进站点 10 的授权行与蓝图。"""
    from database.versioned_migrations import _sync_twbst528_zhongte_mode_authorization

    db_path = str(tmp_path / "twbst528_zhongte_authorization.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE mode_payload_tables (modes_id INTEGER PRIMARY KEY, filename TEXT, "
            "title TEXT, table_name TEXT, record_count INTEGER, is_image INTEGER, is_text INTEGER, "
            "created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE managed_sites (id INTEGER PRIMARY KEY, web_id INTEGER, name TEXT, "
            "domain TEXT, lottery_type_id INTEGER, enabled INTEGER, blueprint_name TEXT, "
            "announcement TEXT, notes TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE site_blueprint_profiles (blueprint_name TEXT PRIMARY KEY, "
            "required_mode_ids_json TEXT, known_unavailable_mode_ids_json TEXT, blocked_items_json TEXT, "
            "created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE site_prediction_modules (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "site_id INTEGER, mechanism_key TEXT, mode_id INTEGER, status INTEGER, sort_order INTEGER, "
            "created_at TEXT, updated_at TEXT, title TEXT, UNIQUE(site_id, mechanism_key))"
        )
        _sync_twbst528_zhongte_mode_authorization(conn)

        rows = {
            str(row["mechanism_key"]): (int(row["mode_id"]), int(row["status"]))
            for row in conn.execute(
                "SELECT mechanism_key, mode_id, status FROM site_prediction_modules WHERE site_id = 10"
            ).fetchall()
        }
        assert rows["jimei_xiongchou"] == (155, 1)
        assert rows["qianhou_shengxiao"] == (133, 1)
        assert rows["sanxiao_siwei_xiao"] == (117, 1)


def test_twbst528_exact_mode_tables_are_bootstrapped(tmp_path):
    from database.schema.legacy import ensure_twbst528_prediction_tables

    db_path = str(tmp_path / "twbst528_exact_modes.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY, filename TEXT, title TEXT,
                table_name TEXT, record_count INTEGER, is_image INTEGER,
                is_text INTEGER, created_at TEXT, updated_at TEXT
            )
            """
        )
        ensure_twbst528_prediction_tables(conn, auto_increment_primary_key("id", conn.engine))

        for mode_id in (486, 487, 488, 490, 491):
            assert "content" in set(conn.table_columns(f"mode_payload_{mode_id}"))

        assert {"content", "xiao", "code"}.issubset(
            set(conn.table_columns("mode_payload_489"))
        )


def test_twbst528_dependency_manifest_uses_exact_modes():
    from domains.prediction.site_page_dependencies import dependencies_for_site

    homepage = [
        item for item in dependencies_for_site("twbst528")
        if item.page_path.endswith("/twbst528/index.html")
    ]
    modes_by_key = {item.endpoint: item.mode_ids for item in homepage}

    assert modes_by_key["daimingxiao"] == (486,)
    assert modes_by_key["liuweichute"] == (487,)
    assert modes_by_key["toudanshuang"] == (488,)
    assert modes_by_key["liuxiaoliuma"] == (489,)
    assert modes_by_key["shaliangbanbo"] == (490,)
    assert modes_by_key["gongshi_siw"] == (491,)
