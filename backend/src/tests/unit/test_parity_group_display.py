"""单双类玩法「单/双」分类展示槽的回归测试（mode 15）。

背景（2026-10-13 用户报障）：twtongtian『单双两肖』与 twsaimahui『单双中特』连续多期
只显示「双数」。根因是 `format_content_xiao_columns` 在「候选与所有分类都重叠」时退回
历史众数 (`pool[0]`)，而 mode 15 的两肖几乎每期都横跨单/双两组，于是分类被锁死。

口径（用户确认）：**不做奇偶强制交替**，只限制「同一分类最多连续 3 期，禁止第 4 期」。

本文件锁定三条契约：
1. 分类兜底不再按历史频率挑，而是按候选确定性取模（可复现、会随候选变化）；
2. 生成侧只在「最近 3 期已同值」时把分类换成另一组，其余情况保持生成结果；
3. 换分类**不改变** `xiao` 两肖（判定口径）。
"""

from __future__ import annotations

import pytest

from predict.mechanisms import _stable_pool_index


def test_stable_pool_index_is_deterministic_and_spreads_over_the_pool():
    pool_size = 2
    first = _stable_pool_index(("狗", "鸡"), pool_size)
    assert first == _stable_pool_index(("狗", "鸡"), pool_size)
    # 同一个人以不同顺序给出候选也必须落在同一分类（与顺序无关）
    assert first == _stable_pool_index(("鸡", "狗"), pool_size)
    # 不同候选应能覆盖到另一个分类（不再被单一取值锁死）
    values = {
        _stable_pool_index(pair, pool_size)
        for pair in (
            ("狗", "鸡"),
            ("羊", "蛇"),
            ("猪", "羊"),
            ("龙", "蛇"),
            ("牛", "龙"),
            ("猪", "牛"),
        )
    }
    assert values == {0, 1}, values


def test_stable_pool_index_degrades_safely():
    assert _stable_pool_index(("狗", "鸡"), 1) == 0
    index = _stable_pool_index((), 3)
    assert 0 <= index < 3


DOUBLE = "双生肖|鼠,虎,龙,马,猴,狗"
SINGLE = "单生肖|牛,兔,蛇,羊,鸡,猪"
PARITY_POOL = [DOUBLE, SINGLE]


@pytest.fixture()
def parity_conn(monkeypatch):
    """把候选池钉成两条分类，避免依赖真实库。"""
    import predict.mechanisms as mechanisms

    monkeypatch.setattr(
        mechanisms,
        "_content_category_pool",
        lambda conn, table_name, column="content": list(PARITY_POOL),
    )
    return object()


def _rows(*contents: str) -> list[dict[str, str]]:
    """构造最近行（调用方按 新→旧 传入）。"""
    return [{"content": content, "xiao": "狗,鸡"} for content in contents]


def test_parity_group_flips_only_when_the_run_reaches_the_cap(parity_conn):
    from prediction_generation.service import _stabilize_parity_group

    row = {"content": DOUBLE, "xiao": "狗,鸡"}

    # 最近 3 期都是双 → 到顶，本期必须换单
    at_cap = _stabilize_parity_group(
        row,
        mode_id=15,
        term=289,
        table_name="mode_payload_15",
        conn=parity_conn,
        recent_rows=_rows(DOUBLE, DOUBLE, DOUBLE),
    )
    assert at_cap["content"] == SINGLE
    # 两肖与其它列一律不动（判定口径不变）
    assert at_cap["xiao"] == "狗,鸡"

    # 最近只有 2 期同值 → 未到顶，保持原分类（**不**做奇偶强制交替）
    below_cap = _stabilize_parity_group(
        row,
        mode_id=15,
        term=288,
        table_name="mode_payload_15",
        conn=parity_conn,
        recent_rows=_rows(DOUBLE, DOUBLE),
    )
    assert below_cap is row

    # 最近 3 期里有别的分类 → 也不算到顶
    mixed = _stabilize_parity_group(
        row,
        mode_id=15,
        term=287,
        table_name="mode_payload_15",
        conn=parity_conn,
        recent_rows=_rows(DOUBLE, DOUBLE, SINGLE),
    )
    assert mixed is row


def test_parity_group_sequence_never_repeats_four_times(parity_conn):
    """连续 12 期「生成器都给双」的极端情况：最多连续 3 期双，第 4 期必换单。"""
    from prediction_generation.service import _stabilize_parity_group

    history: list[dict[str, str]] = []
    labels: list[str] = []
    for term in range(280, 292):
        row = {"content": DOUBLE, "xiao": "狗,鸡"}
        result = _stabilize_parity_group(
            row,
            mode_id=15,
            term=term,
            table_name="mode_payload_15",
            conn=parity_conn,
            recent_rows=list(history),
        )
        label = "双" if result["content"].startswith("双") else "单"
        labels.append(label)
        history.insert(0, {"content": result["content"], "xiao": result["xiao"]})

    # 最长连续同值 <= 3，且确实出现过换值
    longest = 1
    current = 1
    for previous, now in zip(labels, labels[1:]):
        current = current + 1 if now == previous else 1
        longest = max(longest, current)
    assert longest <= 3, labels
    assert set(labels) == {"单", "双"}, labels


def test_parity_stabilizer_only_touches_mode_15(parity_conn):
    from prediction_generation.service import _stabilize_parity_group

    row = {"content": DOUBLE, "xiao": "狗,鸡"}
    untouched = _stabilize_parity_group(
        row,
        mode_id=28,
        term=289,
        table_name="mode_payload_28",
        conn=parity_conn,
        recent_rows=_rows(DOUBLE, DOUBLE, DOUBLE),
    )
    assert untouched is row

    # 非「标签|成员」形态（如 mode 28 的号码集合）不得被改写
    invalid = {"content": '["单|01,03,05"]', "xiao": ""}
    assert (
        _stabilize_parity_group(
            invalid,
            mode_id=15,
            term=289,
            table_name="mode_payload_15",
            conn=parity_conn,
            recent_rows=_rows(DOUBLE, DOUBLE, DOUBLE),
        )
        is invalid
    )
