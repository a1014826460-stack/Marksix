"""六肖三码（getXiaoma2 / num=6）后端契约测试。

背景：twsaimahui 的 `static/js/012liuxiao.js` 请求 `/api/kaijiang/getXiaoma2?web=6&type=3&num=6`，
渲染器要求 `content` 是 `["肖|码,码,码", ...]` 的 JSON 字符串（六肖 + 每肖候选码）。

覆盖两类回归：
1. 兼容层的 endpoint 解析：`num` 与 `mode_payload_*` 同名时不能被 `num` 直表劫持，
   必须拿到「6肖12码」(mode 27) 的正文；
2. 响应字段合同：`content / res_code / res_sx / term` 四个字段、顺序不变，
   `content` 必须是可 `JSON.parse` 的数组且每项形如 `肖|码,码,码`。
"""

from __future__ import annotations

import json

from db import connect
from legacy.frontend_compat import handle_frontend_kaijiang_api


SIX_XIAO_CONTENT = (
    '["狗|09,21,33,45","猪|08,20,32,44","鸡|10,22,34,46",'
    '"龙|03,15,27,39","猴|11,23,35,47","马|01,13,25,37,49"]'
)
NUM_TABLE_CONTENT = '["鼠|07,19"]'


def _setup_db(tmp_path) -> str:
    db_path = str(tmp_path / "legacy_xiaoma2.sqlite3")
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE mode_payload_tables (
                modes_id INTEGER PRIMARY KEY,
                table_name TEXT NOT NULL
            )
            """
        )
        # mode 27 = 「6肖12码」，就是六肖三码的正文来源。
        conn.execute(
            "INSERT INTO mode_payload_tables (modes_id, table_name) VALUES (?, ?)",
            (27, "mode_payload_27"),
        )

        for table_name in ("mode_payload_27", "mode_payload_6"):
            conn.execute(
                f"""
                CREATE TABLE {table_name} (
                    year TEXT,
                    term TEXT,
                    web INTEGER,
                    type INTEGER,
                    content TEXT,
                    res_code TEXT,
                    res_sx TEXT
                )
                """
            )

        conn.execute(
            """
            INSERT INTO mode_payload_27 (year, term, web, type, content, res_code, res_sx)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026",
                "190",
                6,
                3,
                SIX_XIAO_CONTENT,
                "20,19,38,35,23,42,45",
                "猪,鼠,蛇,猴,猴,牛,狗",
            ),
        )
        # 同名直表陷阱：num=6 恰好存在 mode_payload_6，但六肖三码必须走 mode 27。
        conn.execute(
            """
            INSERT INTO mode_payload_6 (year, term, web, type, content, res_code, res_sx)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("2026", "6", 6, 3, NUM_TABLE_CONTENT, "", "鼠"),
        )
        conn.commit()
    return db_path


def test_get_xiaoma2_num6_keeps_expected_field_contract(tmp_path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getXiaoma2",
            {"web": ["6"], "type": ["3"], "num": ["6"]},
            conn,
        )

    assert list(result.keys()) == ["data"]
    assert len(result["data"]) == 1
    row = result["data"][0]
    # getXiaoma2 不在 _ENDPOINT_FIELDS 里，走默认字段集；渲染器只消费下划线标注的四个字段。
    assert list(row.keys()) == [
        "year",
        "term",
        "title",
        "content",
        "res_code",
        "res_sx",
    ]
    for field in ("content", "res_code", "res_sx", "term"):
        assert field in row, f"渲染器需要的字段缺失：{field}"
    assert row["term"] == "190"
    # This fixture has no authoritative draw: candidates stay public, results close.
    assert row["res_sx"] == ""
    assert row["res_code"] == ""
    assert isinstance(row["content"], str)


def test_get_xiaoma2_num6_content_is_zodiac_pipe_code_shape(tmp_path):
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getXiaoma2",
            {"web": ["6"], "type": ["3"], "num": ["6"]},
            conn,
        )

    items = json.loads(result["data"][0]["content"])
    assert len(items) == 6, "六肖三码必须透出 6 个候选肖"
    for item in items:
        name, _, codes = item.partition("|")
        assert name and codes, f"每项必须是「肖名|码,码,码」：{item}"
        for code in codes.split(","):
            assert len(code) == 2 and code.isdigit(), f"候选码必须是两位号码：{item}"


def test_get_xiaoma2_num6_does_not_fall_back_to_same_number_payload_table(tmp_path):
    """`num` 直表优先会劫持 endpoint 解析，这里锁定「六肖三码拿到的是 mode 27 正文」。"""
    db_path = _setup_db(tmp_path)
    with connect(db_path) as conn:
        result = handle_frontend_kaijiang_api(
            "/api/kaijiang/getXiaoma2",
            {"web": ["6"], "type": ["3"], "num": ["6"]},
            conn,
        )

    content = result["data"][0]["content"]
    assert "狗|09,21,33,45" in content
    assert NUM_TABLE_CONTENT not in content
