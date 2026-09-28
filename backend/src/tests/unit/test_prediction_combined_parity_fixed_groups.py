"""mode 132「合数单双」（合数中特）判定链路契约。

用户规则
--------
「合数」= 特码十位 + 个位之和，按该和的奇偶分成 **合单 / 合双**；
判定 = 特码是否落在对应号码集合内（集合精确匹配）。号码集合以
``public.fixed_data`` 的 ``sign = '合单双'`` 为唯一权威来源，不得硬编码：

- 合单：``01,03,05,07,09,10,12,14,16,18,21,23,25,27,29,30,32,34,36,38,41,43,45,47,49``
- 合双：``02,04,06,08,11,13,15,17,19,20,22,24,26,28,31,33,35,37,39,40,42,44,46,48``
  （注意这不是奇偶：如 37 的合数为 10，因此属于**合双**）

线上缺陷（2026-09-28）
--------------------
`getHeds` 的正文只有纯标签 ``合单`` / ``合双``（生成器 `format_literal_label`），
而 `006heshuds.js` 把 ``xiaoV[i]``（此时为空串）拿去 ``indexOf(code)``，
空串恒为 -1 → **每期都显示「不中」**。

本文件钉死：
1. `public.fixed_data` 的合单/合双号码表可经公开只读接口读取（不硬编码）；
2. 后端 mode 132 的判定口径 = 「特码合数奇偶 == 候选标签」；
3. 用真实开奖号码逐期复算，验证渲染层依赖的集合语义（含 37 ∈ 合双、11 ∈ 合单）。
"""
from __future__ import annotations

import pytest

from db import connect
from domains.numbers.fixed_groups import load_fixed_data_groups
from predict.categories.size_parity import special_combined_parity_from_row
from predict.mechanisms import get_prediction_config
from public.api import _check_correct_by_mechanism

#: 用户给出的权威号码表（用于与 `fixed_data` 交叉核对，不参与实现）
EXPECTED_COMBINED_SINGLE = (
    "01,03,05,07,09,10,12,14,16,18,21,23,25,27,29,30,32,34,36,38,41,43,45,47,49"
)
EXPECTED_COMBINED_DOUBLE = (
    "02,04,06,08,11,13,15,17,19,20,22,24,26,28,31,33,35,37,39,40,42,44,46,48"
)

#: 真实开奖逐期复算样本（本地 `public.mode_payload_132` web=6/type=3 的实际行）
LIVE_ROWS = (
    # (期号, res_code, res_sx, 候选标签, 期望判定)
    ("2026364", "34,22,23,40,45,30,18", "猴,猴,羊,虎,鸡,鼠,鼠", "合单", True),   # 18 → 1+8=9（奇）
    ("2026363", "32,18,21,29,45,34,22", "狗,鼠,鸡,牛,鸡,猴,猴", "合单", False),  # 22 → 2+2=4（偶）= 合双
    ("2026361", "21,35,31,20,07,02,05", "鸡,羊,猪,狗,猪,龙,牛", "合单", True),   # 05 → 5（奇）
    ("2026360", "42,18,05,07,02,21,35", "鼠,鼠,牛,猪,龙,鸡,羊", "合双", True),   # 35 → 3+5=8（偶）
    ("2026359", "23,29,37,45,42,18,05", "羊,牛,蛇,鸡,鼠,鼠,牛", "合双", False),  # 05 → 5（奇）= 合单
    ("2026356", "01,03,06,17,16,19,15", "蛇,兔,鼠,牛,虎,猪,兔", "合双", True),   # 15 → 1+5=6（偶）
    ("2026353", "14,17,12,16,13,28,35", "龙,牛,马,虎,蛇,虎,羊", "合单", False),  # 35 → 3+5=8（偶）= 合双
)


def _create_fixed_data_table(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fixed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year TEXT,
                sign TEXT,
                type INTEGER,
                name TEXT,
                xu INTEGER,
                code TEXT,
                status INTEGER
            )
            """
        )


def _seed_fixed_data(db_path: str) -> None:
    """按 `public.fixed_data` 的真实行形状写两条合单双分组。"""
    _create_fixed_data_table(db_path)
    rows = (
        (8, "合单", EXPECTED_COMBINED_SINGLE),
        (9, "合双", EXPECTED_COMBINED_DOUBLE),
    )
    with connect(db_path) as conn:
        for row_id, name, code in rows:
            conn.execute(
                "INSERT INTO fixed_data (id, year, sign, type, name, xu, code, status) "
                "VALUES (?, '', '合单双', 1, ?, 2, ?, 1)",
                (row_id, name, code),
            )


def test_fixed_data_combined_parity_groups_are_authoritative_and_readable(tmp_path):
    """公开只读入口必须原样返回 `fixed_data` 的合单/合双号码表。"""
    db_path = str(tmp_path / "fixed-groups.sqlite3")
    _seed_fixed_data(db_path)

    payload = load_fixed_data_groups(db_path, "合单双")

    assert payload["sign"] == "合单双"
    assert [group["label"] for group in payload["groups"]] == ["合单", "合双"]
    by_label = {group["label"]: tuple(group["codes"]) for group in payload["groups"]}
    assert by_label["合单"] == tuple(EXPECTED_COMBINED_SINGLE.split(","))
    assert by_label["合双"] == tuple(EXPECTED_COMBINED_DOUBLE.split(","))
    # 两组互斥且覆盖 01-49
    assert set(by_label["合单"]) & set(by_label["合双"]) == set()
    assert set(by_label["合单"]) | set(by_label["合双"]) == {
        f"{number:02d}" for number in range(1, 50)
    }


def test_fixed_data_groups_skip_disabled_rows_and_missing_table(tmp_path):
    db_path = str(tmp_path / "fixed-groups-status.sqlite3")
    _seed_fixed_data(db_path)
    with connect(db_path) as conn:
        conn.execute("UPDATE fixed_data SET status = 0 WHERE name = '合双'")

    payload = load_fixed_data_groups(db_path, "合单双")
    assert [group["label"] for group in payload["groups"]] == ["合单"]

    empty_db = str(tmp_path / "no-fixed-table.sqlite3")
    _create_fixed_data_table(empty_db)
    with connect(empty_db) as conn:
        conn.execute("DROP TABLE fixed_data")
    assert load_fixed_data_groups(empty_db, "合单双") == {"sign": "合单双", "groups": []}


def test_fixed_data_groups_rejects_blank_sign(tmp_path):
    db_path = str(tmp_path / "fixed-groups-blank.sqlite3")
    _seed_fixed_data(db_path)
    with pytest.raises(ValueError):
        load_fixed_data_groups(db_path, "   ")


@pytest.mark.parametrize(
    ("special_code", "expected"),
    (
        ("01", "合单"),
        ("10", "合单"),  # 1 + 0 = 1（奇）→ 合单
        ("37", "合双"),  # 3 + 7 = 10（偶）→ 合双，不是「奇数尾」
        ("49", "合单"),  # 4 + 9 = 13（奇）→ 合单
        ("11", "合双"),  # 1 + 1 = 2（偶）→ 合双，不是「奇数号码」
    ),
)
def test_special_combined_parity_matches_the_published_number_table(special_code, expected):
    """机制口径必须与 `fixed_data` 号码表自洽（先按定义算，再按表查）。"""
    row = {"res_code": f"01,02,03,04,05,06,{special_code}"}
    computed = special_combined_parity_from_row(row, None)

    in_single = special_code in EXPECTED_COMBINED_SINGLE.split(",")
    in_double = special_code in EXPECTED_COMBINED_DOUBLE.split(",")
    assert in_single != in_double, special_code
    from_table = "合单" if in_single else "合双"
    assert computed == from_table == expected


def test_mode132_verdict_is_table_membership_for_real_draws():
    """真实开奖逐期复算：命中 = 特码 ∈ 候选标签对应的号码集合。"""
    config = get_prediction_config("title_132")

    for term, res_code, res_sx, label, expected in LIVE_ROWS:
        row = {
            "year": term[:4],
            "term": term[4:],
            "res_code": res_code,
            "res_sx": res_sx,
            "draw_is_opened": 1,
        }
        # 生成器落库的正文形态就是纯标签（`format_literal_label`）
        assert config.content_formatter((label,), None) == label
        assert config.content_parser(label) == (label,)

        actual = _check_correct_by_mechanism(label, row, config)
        assert actual is expected, f"{term} 期 {label} 开 {res_code.split(',')[-1]} 应为 {expected}"
        # 用 fixed_data 号码表独立复算
        special = res_code.split(",")[-1]
        independent = special in (
            EXPECTED_COMBINED_SINGLE.split(",") if label == "合单" else EXPECTED_COMBINED_DOUBLE.split(",")
        )
        assert independent is expected


def test_mode132_verdict_is_none_when_draw_is_pending():
    """未开奖不给判定。"""
    config = get_prediction_config("title_132")
    row = {"year": "2026", "term": "271", "res_code": "", "res_sx": "", "draw_is_opened": 0}
    assert _check_correct_by_mechanism("合双", row, config) is None


def test_substring_matching_would_misjudge_short_special_codes():
    """回归保护：集合语义不能退化成子串匹配。

    特码 ``03`` 的字符串 ``"3"`` 会命中候选串里的 ``"37"``；修复前渲染层就是用
    ``xiaoV[i].indexOf(code)`` 做的子串匹配。
    """
    row = {"year": "2026", "term": "267", "res_code": "14,21,32,46,10,16,03", "res_sx": "", "draw_is_opened": 1}
    config = get_prediction_config("title_132")

    # 特码 03 → 0 + 3 = 3（奇）→ 合单；候选「合双」应判「错」
    assert _check_correct_by_mechanism("合单", row, config) is True
    assert _check_correct_by_mechanism("合双", row, config) is False

    # 子串口径会把 "3" 认成候选串里的 "37"
    assert "3" in EXPECTED_COMBINED_DOUBLE  # 子串匹配的误判来源
    assert "03" not in EXPECTED_COMBINED_DOUBLE.split(",")
