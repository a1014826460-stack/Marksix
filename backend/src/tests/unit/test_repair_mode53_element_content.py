"""`created.mode_payload_53` / `mode_payload_482` 五行正文清单修复（统一号码五行口径）。

回归背景（2026-09-29）：
`public.fixed_data` 里有两套五行分组 —— `sign='五行'`（**号码五行**，权威口径，37→木）
与 `sign='五行肖'`（**生肖五行**，37 是马 → 火肖）。后端判定链
（`predict.common.ELEMENT_NUMBER_GROUPS` / `public.api._compute_outcome_from_row` 的
element 原子 / mode 53、482 的 `special_element_from_row`）用的是号码五行，但历史上
落库的 mode 53/482 正文里每个五行标签后的**号码清单**是按生肖五行拼出来的，
于是「判定说中，展示的候选清单里却找不到那个号码」（反之亦然）。

本测试锁定修复的四个不变量：
1. 清单按**号码五行**重写（标签、条目顺序、其它列都不变）；
2. 幂等（改后清单已正确就跳过，第二次执行不会二次改动）；
3. 只写 `content` 一列（UPDATE 语句不含任何其它列，且必须带原正文比较条件）；
4. 生成侧口径统一（`mode 53/482` 的 `labels_loader` / `explanation` 不再依赖
   `sign='五行肖'`，`format_element_groups` 输出号码五行清单）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from predict.common import ELEMENT_NUMBER_GROUPS, ELEMENT_ORDER
from predict.mechanisms import (
    PREDICTION_CONFIGS,
    TABLE_FIXED_MAPPING_KEYS,
    format_element_groups,
)
from utils.created_prediction_store import (
    CONTENT_LOCATOR_COLUMNS,
    CreatedContentRow,
    FIXED_DATA_ELEMENT_SIGN,
    FIXED_DATA_ELEMENT_ZODIAC_SIGN,
    list_created_content_rows,
    load_element_number_groups,
    rewrite_element_group_content,
    update_created_content_row,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
REPAIR_SCRIPT = REPO_ROOT / "backend" / "scripts" / "repair_mode53_element_content.py"

#: 旧落库口径（生肖五行推导出来的号码清单），来自 fixed_data sign='五行肖' + sign='生肖'。
LEGACY_SX_GROUPS: dict[str, tuple[str, ...]] = {
    "金": ("10", "11", "22", "23", "34", "35", "46", "47"),
    "木": ("04", "05", "16", "17", "28", "29", "40", "41"),
    "水": ("07", "08", "19", "20", "31", "32", "43", "44"),
    "火": ("01", "02", "13", "14", "25", "26", "37", "38", "49"),
    "土": ("03", "06", "09", "12", "15", "18", "21", "24", "27", "30", "33", "36", "39", "42", "45", "48"),
}

CANON: dict[str, tuple[str, ...]] = {
    label: tuple(ELEMENT_NUMBER_GROUPS[label]) for label in ELEMENT_ORDER
}

LEGACY_53 = (
    '["木|04,05,16,17,28,29,40,41", "土|03,06,09,12,15,18,21,24,27,30,33,36,39,42,45,48", '
    '"水|07,08,19,20,31,32,43,44"]'
)
CANONICAL_53 = (
    '["木|07,08,15,16,23,24,37,38,45,46", "土|05,06,19,20,27,28,35,36,49", '
    '"水|13,14,21,22,29,30,43,44"]'
)
COMPACT_CANONICAL_53 = (
    '["木|07,08,15,16,23,24,37,38,45,46","土|05,06,19,20,27,28,35,36,49","水|13,14,21,22,29,30,43,44"]'
)


# ── 1. 清单按号码五行重写 ────────────────────────────────────────


def test_legacy_lists_are_zodiac_element_derived_and_differ_from_canonical():
    """先证明两套口径真的不同（修复不是空操作）。"""

    for label in ELEMENT_ORDER:
        assert set(LEGACY_SX_GROUPS[label]) != set(CANON[label])
    # 37：号码五行=木，生肖=马 → 生肖五行=火。
    assert "37" in CANON["木"]
    assert "37" in LEGACY_SX_GROUPS["火"]
    # 45：号码五行=木，生肖=狗 → 生肖五行=土。
    assert "45" in CANON["木"]
    assert "45" in LEGACY_SX_GROUPS["土"]


def test_rewrite_replaces_number_lists_with_number_element_groups():
    assert rewrite_element_group_content(LEGACY_53, CANON) == CANONICAL_53


def test_rewrite_keeps_labels_order_and_item_count():
    new_content = rewrite_element_group_content(LEGACY_53, CANON)
    before_items = json.loads(LEGACY_53)
    after_items = json.loads(new_content)

    assert len(before_items) == len(after_items)
    for before_item, after_item in zip(before_items, after_items):
        label = before_item.split("|", 1)[0]
        assert after_item.split("|", 1)[0] == label
        assert after_item == f"{label}|{','.join(CANON[label])}"


def test_rewrite_preserves_original_separator_style():
    """只替换号码子串：原文本用紧凑分隔符时不得顺手改成 json.dumps 的 `, `。"""

    assert rewrite_element_group_content(COMPACT_CANONICAL_53, CANON) == COMPACT_CANONICAL_53
    assert rewrite_element_group_content(COMPACT_CANONICAL_53, LEGACY_SX_GROUPS) == LEGACY_53.replace(", ", ",")


def test_rewrite_leaves_unknown_labels_and_non_element_items_alone():
    content = '["木|04,05,16,17,28,29,40,41", "其它|01,02"]'
    assert rewrite_element_group_content(content, CANON) == '["木|07,08,15,16,23,24,37,38,45,46", "其它|01,02"]'


@pytest.mark.parametrize(
    "content",
    ["", "   ", "暂无后端资料", '{"木": 1}', "[1, 2, 3]", '["01,02,03"]', None],
)
def test_rewrite_returns_none_for_content_it_does_not_understand(content):
    assert rewrite_element_group_content(content, CANON) is None


# ── 2. 幂等 ─────────────────────────────────────────────────────


def test_rewrite_is_idempotent_on_already_canonical_content():
    once = rewrite_element_group_content(LEGACY_53, CANON)
    twice = rewrite_element_group_content(once, CANON)
    assert once == twice == CANONICAL_53


def test_rewrite_returns_identical_text_when_numbers_already_canonical():
    """返回值与原文完全相同时，调用方跳过写库 —— 这是幂等的判据。"""

    assert rewrite_element_group_content(CANONICAL_53, CANON) == CANONICAL_53
    assert rewrite_element_group_content(COMPACT_CANONICAL_53, CANON) == COMPACT_CANONICAL_53


# ── 3. 只动 content 一列 ────────────────────────────────────────


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None, rowcount: int = 1) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchall(self) -> list[dict]:
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _FakeConn:
    """最小假连接：记录 SQL 与参数。"""

    engine = "postgres"
    target = "postgresql://fake/db"

    def __init__(self, rows: list[dict] | None = None, rowcount: int = 1) -> None:
        self.rows = rows or []
        self.rowcount = rowcount
        self.calls: list[tuple[str, object]] = []

    def execute(self, sql_text: str, params=None) -> _FakeCursor:
        self.calls.append((" ".join(str(sql_text).split()), params))
        if "information_schema.tables" in str(sql_text):
            return _FakeCursor([{"?column?": 1}])
        if "pg_attribute" in str(sql_text):
            return _FakeCursor(
                [
                    {"column_name": name, "column_type": "text"}
                    for name in ("id", "web_id", "type", "year", "term", "content")
                ]
            )
        return _FakeCursor(self.rows, rowcount=self.rowcount)

    @property
    def update_calls(self):
        return [call for call in self.calls if call[0].upper().startswith("UPDATE")]


def test_update_created_content_row_only_sets_content():
    conn = _FakeConn()
    affected = update_created_content_row(
        conn,
        "mode_payload_53",
        locator=(("id", "c3818"),),
        expected_content=LEGACY_53,
        new_content=CANONICAL_53,
    )

    assert affected == 1
    sql, params = conn.update_calls[0]
    set_clause = sql.split("SET", 1)[1].split("WHERE", 1)[0].strip()
    assert set_clause == '"content" = ?'
    for column in ("web_id", "web", "type", "year", "term", "res_code", "res_sx", "status"):
        assert f'"{column}"' not in set_clause
    # 比较-交换：必须同时锁定位列与「原正文」
    assert 'AND "content" = ?' in sql
    assert params == (CANONICAL_53, "c3818", LEGACY_53)


def test_update_rejects_locator_columns_outside_the_whitelist():
    conn = _FakeConn()
    with pytest.raises(ValueError):
        update_created_content_row(
            conn,
            "mode_payload_53",
            locator=(("content", "x"),),
            expected_content="a",
            new_content="b",
        )
    assert conn.update_calls == []


def test_locator_whitelist_has_no_physical_row_id():
    """`ctid` 会在 UPDATE 后改变，不能用来做可回滚的定位。"""

    assert "ctid" not in CONTENT_LOCATOR_COLUMNS
    assert set(CONTENT_LOCATOR_COLUMNS) == {"id", "web_id", "web", "type", "year", "term"}


def test_created_content_row_locator_prefers_id_then_natural_key():
    with_id = CreatedContentRow(content="x", row_id="c3818", web_id=9, year="2026", term="218")
    assert with_id.locator == (("id", "c3818"),)

    without_id = CreatedContentRow(
        content="x", row_id="", web_id=5, year="2026", term="270", row_type="3"
    )
    assert without_id.locator == (
        ("web_id", "5"),
        ("type", "3"),
        ("year", "2026"),
        ("term", "270"),
    )
    assert without_id.locatable is True

    assert CreatedContentRow(content="x").locator == ()
    assert CreatedContentRow(content="x").locatable is False


def test_list_created_content_rows_selects_only_locator_and_content_columns():
    conn = _FakeConn(rows=[{"id": "c1", "content": "x", "web_id": 4, "year": "2026", "term": "1"}])
    rows = list_created_content_rows(conn, "mode_payload_53")

    select_sql = conn.calls[0][0]
    assert select_sql.upper().startswith("SELECT")
    for column in ("res_code", "res_sx", "res_color", "status", "created_at"):
        assert column not in select_sql
    assert rows[0].row_id == "c1"


# ── 4. 权威口径来源 ────────────────────────────────────────────


def test_element_groups_are_read_from_fixed_data_sign_wu_xing_not_wu_xing_xiao():
    assert FIXED_DATA_ELEMENT_SIGN == "五行"
    assert FIXED_DATA_ELEMENT_ZODIAC_SIGN == "五行肖"

    conn = _FakeConn(
        rows=[
            {"name": "金", "code": "03,04,11,12,25,26,33,34,41,42"},
            {"name": "木", "code": "07,08,15,16,23,24,37,38,45,46"},
            {"name": "水", "code": "13,14,21,22,29,30,43,44"},
            {"name": "火", "code": "01,02,09,10,17,18,31,32,39,40,47,48"},
            {"name": "土", "code": "05,06,19,20,27,28,35,36,49"},
        ]
    )
    groups = load_element_number_groups(conn)

    assert groups["木"] == tuple(ELEMENT_NUMBER_GROUPS["木"])
    assert "37" in groups["木"]
    assert "37" not in groups["火"]
    sql, params = [call for call in conn.calls if "fixed_data" in call[0]][0]
    assert params == ("五行",)
    assert "五行肖" not in params


# ── 脚本契约 ───────────────────────────────────────────────────


def test_repair_script_defaults_to_dry_run_and_requires_explicit_apply():
    text = REPAIR_SCRIPT.read_text(encoding="utf-8")

    assert 'set_defaults(apply=False)' in text
    assert '"--apply"' in text
    assert '"--dry-run"' in text
    assert '"--db-path"' in text
    assert "if not dry_run and all_changes:" in text
    assert "TARGET_TABLES" not in text  # 目标表只有 DEFAULT_TABLES 一处定义
    assert 'DEFAULT_TABLES: tuple[str, ...] = ("mode_payload_53", "mode_payload_482")' in text
    # 只允许 created schema 的目标表
    assert 'MODE_PAYLOAD_TABLE_RE = re.compile(r"^mode_payload_\\d+$")' in text
    # 干跑必须显式声明没有写库
    assert "未对数据库做任何写操作" in text


def test_repair_script_has_no_inline_sql_and_only_touches_created_tables():
    """仓库规范：SQL 只允许在 repository / db / migration / created_store 里。

    脚本只做编排（读 created_store 的快照 + 调 created_store 的写入函数），
    因此正文里不允许出现任何 `execute/fetchall` 或 public schema 的写目标。
    """

    text = REPAIR_SCRIPT.read_text(encoding="utf-8")

    assert "execute(" not in text
    assert "fetchall(" not in text
    assert "fetchone(" not in text
    assert "public.mode_payload" not in text
    # 正文里的 `created.mode_payload_53` 只出现在文档/报告文本里，不得出现在任何 SQL 语句中
    assert not re.search(r"(?i)\b(select|update|insert|delete)\b[^\n]*created\.", text)
    assert "list_created_content_rows" in text
    assert "update_created_content_row" in text
    assert not re.search(r"\b(DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", text, re.IGNORECASE)
    assert not re.search(r"(?i)\binsert\s+into\b", text)


# ── 5. 生成侧口径统一 ───────────────────────────────────────────


@pytest.mark.parametrize("key", ["3hang", "sihangzhongte"])
def test_element_mechanisms_use_number_element_labels(key: str):
    config = PREDICTION_CONFIGS[key]
    assert tuple(config.labels) == tuple(ELEMENT_ORDER)


@pytest.mark.parametrize("key", ["3hang", "sihangzhongte"])
def test_element_mechanism_explanations_do_not_claim_zodiac_element(key: str):
    explanation = " ".join(PREDICTION_CONFIGS[key].explanation)
    assert "sign='五行'" in explanation
    assert "号码五行" in explanation
    assert "不使用生肖五行" in explanation


def test_element_mechanisms_no_longer_read_the_zodiac_element_sign():
    source = (REPO_ROOT / "backend" / "src" / "predict" / "mechanisms.py").read_text(encoding="utf-8")
    assert 'labels_from_fixed("五行肖"' not in source
    assert TABLE_FIXED_MAPPING_KEYS["mode_payload_53"] == "五行"


@pytest.mark.parametrize("key", ["3hang", "sihangzhongte"])
def test_element_content_formatter_emits_number_element_lists(key: str):
    formatter = PREDICTION_CONFIGS[key].content_formatter
    formatted = formatter(("金", "木"), None)

    assert formatted == [f"金|{','.join(CANON['金'])}", f"木|{','.join(CANON['木'])}"]
    # 37 属木：必须出现在木组，不得出现在火组（生肖五行口径会把 37 放进火）
    assert "37" in CANON["木"]
    assert "37" not in CANON["火"]
    assert "45" in CANON["木"]


def test_format_element_groups_covers_all_49_numbers_exactly_once():
    formatted = format_element_groups(tuple(ELEMENT_ORDER), None)
    seen: list[str] = []
    for item in formatted:
        label, _, numbers = item.partition("|")
        assert label in ELEMENT_ORDER
        seen.extend(numbers.split(","))
    assert sorted(seen) == [f"{index:02d}" for index in range(1, 50)]


def test_run_prediction_module_supports_standalone_import():
    """脚本用 `sys.path.insert(.../src)` 独立运行，不依赖调用方已经设好 sys.path。"""

    text = REPAIR_SCRIPT.read_text(encoding="utf-8")

    assert (
        'sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))'
        in text
    )
    assert "from db import connect" in text
    assert "from predict.common import" in text
    assert "from utils.created_prediction_store import" in text
    assert sys.version_info >= (3, 11)
