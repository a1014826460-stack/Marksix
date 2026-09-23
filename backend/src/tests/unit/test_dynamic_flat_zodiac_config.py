from __future__ import annotations

from db import connect
from domains.prediction.generation_rules import get_generation_rule
from predict import mechanisms


def test_flat_window_zodiac_config_keeps_the_flat_rule():
    """三期平特1肖（start/end 连期表）必须保留平特口径标记。

    第二阶段分类器会用 `_make_window_config` 包装基础配置；逐字段重建会丢失
    `flat_zodiac`，导致动态 mode（如 103）退回“只看特码生肖”的判定。
    """
    base = mechanisms._classify_title_config("三期平特1肖", "mode_payload_103", 103, "蛇")
    assert base is not None
    assert base.flat_zodiac is True

    wrapped = mechanisms._make_window_config(base)

    assert wrapped.flat_zodiac is True
    assert wrapped.hit_checker is base.hit_checker
    assert wrapped.content_parser is base.content_parser
    assert get_generation_rule(wrapped).rule_id == "zodiac_flat"


def test_dynamic_flat_one_xiao_config_is_rule_verified(tmp_path):
    db_path = tmp_path / "flat_window_registry.sqlite3"
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL,
                title TEXT,
                record_count INTEGER
            )
            """
        )
        conn.execute(
            'CREATE TABLE mode_payload_103 (content TEXT, start TEXT, "end" TEXT, '
            "res_code TEXT, res_sx TEXT)"
        )
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, table_name, title, record_count) "
            "VALUES (103, 'mode_payload_103', '三期平特1肖', 1)"
        )
        conn.execute(
            'INSERT INTO mode_payload_103 (content, start, "end", res_code, res_sx) '
            "VALUES ('蛇', '263', '265', '21,39,42,02,18,17,08', '狗,龙,牛,蛇,牛,虎,猪')"
        )

    configs = mechanisms.build_title_prediction_configs(db_path)

    config = configs.get("title_103")
    assert config is not None
    assert config.flat_zodiac is True
    assert get_generation_rule(config).rule_id == "zodiac_flat"
