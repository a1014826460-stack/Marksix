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
    }

    for key, (mode_id, label_count, rule_id) in expected.items():
        config = get_prediction_config(key)
        assert config.default_modes_id == mode_id
        assert config.label_count == label_count
        assert get_generation_rule(config).rule_id == rule_id


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
