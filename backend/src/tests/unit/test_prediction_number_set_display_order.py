"""无序号码集合玩法的展示顺序修复（mode 9 / 65 / 88 / 116）。

背景（线上实测，created.mode_payload_* web_id=6 最近 40 期）：
- mode 116（10码中特）位置 1 恒为 `01`（38/40），位置 2 恒为 `17`（25/40）；
- mode 88（杀7码）位置 1/2 只在 {01,17} 之间互换，位置 3 恒为 `14`（23/40）；
- mode 9（16码中特）位置 1~5 只在 {23,39,08,22,36} 之间轮转。

根因：号码类玩法的 content 是 `01,17,40,...` 这种纯号码串，生成侧
`score_labels(strategy="hot")` 按热度把同一批号码固定排在最前面，而展示顺序就是
排名顺序（跨站共享源表每个期号有多行，热度窗口只覆盖 1~2 个真实期号，排名因此冻结）。
旧的 `unique_first_two` 位置轮转对这些 mode 实际上是空转：
`parse_array_content` 用 json.loads 解析纯逗号串会失败，因此 `enforce_prediction_diversity`
在 `len(items) < 2` 分支直接返回原值，从未做过任何修复。

本文件锁定修复后的契约：
1. 这些 mode 采用 `unordered_set_display_order` 策略，不再做位置轮转；
2. 展示顺序按 (mode, 年, 期, 站点) 一次性置换：同期稳定、异期不同；
3. **号码成员一个都不变**，命中/不中判定与修复前完全一致。
"""

from __future__ import annotations

import json

from predict.categories.number import format_24_numbers
from predict.common import contains_hit, excludes_hit
from prediction_generation import diversity


# ---------- 白名单与策略解析 ----------


def test_unordered_number_set_mode_ids_cover_reported_modes():
    """工单点名的 10码(116) / 16码(9) 必须在白名单内；杀7码(88) 同样在。"""
    assert {9, 88, 116} <= set(diversity.UNORDERED_NUMBER_SET_MODE_IDS)
    assert 65 in diversity.UNORDERED_NUMBER_SET_MODE_IDS


def test_mode_34_keeps_positional_contract():
    """mode 34（24码）登记了 cross-site prefix: 3 的跨站前缀契约，暂不改展示顺序。"""
    assert 34 not in diversity.UNORDERED_NUMBER_SET_MODE_IDS


def test_resolve_diversity_policy_returns_unordered_set_policy():
    for mode_id in sorted(diversity.UNORDERED_NUMBER_SET_MODE_IDS):
        assert diversity.resolve_diversity_policy(mode_id, None) == diversity.UNORDERED_SET_DIVERSITY_POLICY


def test_resolve_diversity_policy_keeps_other_modes_unchanged():
    assert diversity.resolve_diversity_policy(46, None) == diversity.DEFAULT_DIVERSITY_POLICY
    assert diversity.resolve_diversity_policy(28, None) == diversity.WINDOW_SHARED_DIVERSITY_POLICY
    assert diversity.resolve_diversity_policy(197, None) == diversity.WINDOW_SHARED_DIVERSITY_POLICY


def test_explicit_config_policy_still_wins():
    """兼容既有优先级：配置对象显式给出的 diversity_policy 仍然优先。"""

    class _Config:
        diversity_policy = "free"

    row = {"content": "01,17,40,11,14,06,15,23,37,34", "year": "2026", "term": "88", "web": "6"}
    result = diversity.enforce_prediction_diversity(mode_id=116, row_data=row, config=_Config())
    assert result["content"] == row["content"]


# ---------- content 形态识别 ----------


def test_number_set_members_accepts_all_persisted_shapes():
    expected = ["01", "17", "40"]
    assert diversity.number_set_members("01,17,40") == expected
    assert diversity.number_set_members(["01", "17", "40"]) == expected
    assert diversity.number_set_members(json.dumps(expected)) == expected


def test_number_set_members_rejects_ordered_label_sequences():
    """有序标签序列（`标签|号码`）不能被当成号码集合。"""
    assert diversity.number_set_members('["家禽|牛,马,羊,鸡,狗,猪"]') is None
    assert diversity.number_set_members('["大|25,26,27"]') is None
    assert diversity.number_set_members("01,17,50") is None
    assert diversity.number_set_members("01") is None
    assert diversity.number_set_members("") is None
    assert diversity.number_set_members({"content": "01,17"}) is None


def test_number_set_detection_matches_real_number_formatter_output():
    """生成侧 `format_24_numbers` 的输出必须被判为号码集合。"""
    labels = ("01", "17", "40", "11", "14", "06", "15", "23", "37", "34")
    content = format_24_numbers(labels, None)
    assert content == "01,17,40,11,14,06,15,23,37,34"
    assert diversity.is_unordered_number_set_content(content) is True


def test_legacy_parser_could_not_see_csv_content():
    """锁定根因：旧 `unique_first_two` 轮转对号码类 content 是空转。

    `parse_array_content` 只接受 JSON 数组，纯逗号串会走 `len(items) < 2` 分支直接返回，
    因此线上 mode 116/88/9 的 `01,17,...` 前缀从来没有被修复过。
    """
    assert diversity.parse_array_content("01,17,40,11,14,06,15,23,37,34") is None
    assert diversity.content_prefix_signature("01,17,40", width=2) is None


# ---------- 位置不再固定（工单现象回归测试） ----------


def test_no_position_is_pinned_across_issues():
    """40 个不同期号喂同一个“冻结前缀”排名结果，位置 1 不得集中在 `01`。

    修复前：content 原样落库 → 位置 1 = `01` 出现 40/40（线上 38/40）。
    修复后：位置 1 在集合成员间轮换，`01` 出现次数应接近 1/10（这里放宽到 <= 8）。
    """
    frozen_ranking = "01,17,40,11,14,06,15,23,37,34"
    position_one: list[str] = []
    position_two: list[str] = []
    for term in range(200, 240):
        row = {"content": frozen_ranking, "year": "2026", "term": str(term), "web": "6"}
        result = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)
        items = result["content"].split(",")
        position_one.append(items[0])
        position_two.append(items[1])

    assert len(set(position_one)) >= 5
    assert position_one.count("01") <= 8
    assert (position_one[0], position_two[0]) != ("01", "17")


def test_mode_88_and_mode_9_positions_also_vary():
    """杀7码（88）与 16码（9）同样不再出现固定轮转位。"""
    for mode_id, frozen in (
        (88, "01,17,14,28,03,20,36"),
        (9, "23,39,08,22,36,18,15,26,14,05,27,16,20,40,33,44"),
    ):
        leads = []
        for term in range(200, 240):
            row = {"content": frozen, "year": "2026", "term": str(term), "web": "6"}
            leads.append(diversity.enforce_prediction_diversity(mode_id=mode_id, row_data=row)["content"].split(",")[0])
        assert len(set(leads)) >= 4, (mode_id, leads)
        assert max(leads.count(value) for value in set(leads)) < 20, (mode_id, leads)


def test_display_order_varies_even_without_issue_fields():
    """漏传 year/term/web 时，不同号码集合仍不得退化成同一个固定置换。"""
    member_sets = [
        ["01", "17", "40", "11", "14", "06", "15", "23", "37", "34"],
        ["01", "17", "22", "27", "13", "04", "14", "47", "09", "32"],
        ["01", "17", "05", "33", "42", "12", "06", "04", "31", "19"],
        ["01", "17", "43", "13", "11", "03", "16", "41", "36", "20"],
    ]
    leads = []
    for members in member_sets:
        row = {"content": ",".join(members)}
        leads.append(diversity.enforce_prediction_diversity(mode_id=116, row_data=row)["content"].split(",")[0])
    # 排名结果的前两位恒为 01/17，修复后位置 1 不应在 4 个不同集合上完全相同
    assert len(set(leads)) > 1, leads


def test_display_order_differs_from_the_previous_issue():
    """相邻期展示顺序必须不同（原来这里根本没有生效的约束）。"""
    content = "01,17,40,11,14,06,15,23,37,34"
    recent_rows: list[dict] = []
    seen: list[str] = []
    for term in range(200, 220):
        row = {"content": content, "year": "2026", "term": str(term), "web": "6"}
        result = diversity.enforce_prediction_diversity(
            mode_id=116, row_data=row, recent_rows=list(recent_rows)
        )
        ordered = result["content"]
        if seen:
            assert ordered != seen[-1]
        seen.append(ordered)
        recent_rows.insert(0, {"content": ordered})


# ---------- 判定语义等价 ----------


def test_membership_is_preserved_for_every_persisted_shape():
    for content in ("01,17,40,11,14,06,15,23,37,34", '["01","17","40","11"]', ["01", "17", "40", "11"]):
        row = {"content": content, "year": "2026", "term": "88", "web": "6"}
        result = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)
        original_members = diversity.number_set_members(content)
        assert diversity.number_set_members(result["content"]) is not None
        assert sorted(diversity.number_set_members(result["content"])) == sorted(original_members)


def test_content_shape_is_preserved():
    list_result = diversity.enforce_prediction_diversity(
        mode_id=116,
        row_data={"content": ["01", "17", "40"], "year": "2026", "term": "88", "web": "6"},
    )
    assert isinstance(list_result["content"], list)

    json_result = diversity.enforce_prediction_diversity(
        mode_id=116,
        row_data={"content": '["01","17","40"]', "year": "2026", "term": "88", "web": "6"},
    )
    assert isinstance(json_result["content"], str) and json_result["content"].startswith("[")
    assert sorted(json.loads(json_result["content"])) == ["01", "17", "40"]

    csv_result = diversity.enforce_prediction_diversity(
        mode_id=116,
        row_data={"content": "01,17,40", "year": "2026", "term": "88", "web": "6"},
    )
    assert "," in csv_result["content"] and not csv_result["content"].startswith("[")


def test_hit_semantics_identical_before_and_after_reorder():
    """命中/不中只看成员，重排展示顺序不改变任何判定结论。"""
    content = "01,17,40,11,14,06,15,23,37,34"
    row = {"content": content, "year": "2026", "term": "88", "web": "6"}
    reordered = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)["content"]

    before = tuple(content.split(","))
    after = tuple(reordered.split(","))
    for special in [f"{number:02d}" for number in range(1, 50)]:
        # 10码中特：特码在集合内算命中
        assert contains_hit(special, before) == contains_hit(special, after)
        # 杀7码：特码不在集合内算命中
        assert excludes_hit(special, before) == excludes_hit(special, after)
    assert contains_hit("37", before) is True and contains_hit("37", after) is True
    assert contains_hit("49", before) is False and contains_hit("49", after) is False


def test_display_order_is_stable_for_the_same_issue():
    """同一期重复生成（重算/重放）必须得到同一展示顺序，避免快照漂移。"""
    row = {"content": "01,17,40,11,14,06,15,23,37,34", "year": "2026", "term": "88", "web": "6"}
    first = diversity.enforce_prediction_diversity(mode_id=116, row_data=dict(row))["content"]
    second = diversity.enforce_prediction_diversity(mode_id=116, row_data=dict(row))["content"]
    assert first == second

    other_site = dict(row, web="5")
    other_term = dict(row, term="89")
    assert diversity.enforce_prediction_diversity(mode_id=116, row_data=other_site)["content"] != first
    assert diversity.enforce_prediction_diversity(mode_id=116, row_data=other_term)["content"] != first


# ---------- 不误伤其他模式 ----------


def test_non_number_content_is_left_untouched_on_whitelisted_mode():
    """白名单 mode 遇到非号码集合 content 时保持原样（形态护栏）。"""
    row = {"content": '["家禽|牛,马,羊,鸡,狗,猪"]', "year": "2026", "term": "88", "web": "6"}
    result = diversity.enforce_prediction_diversity(mode_id=116, row_data=row)
    assert result["content"] == row["content"]
    assert "_diversity_warning" not in result


def test_ordered_modes_still_use_unique_first_two_rotation():
    """非白名单模式仍走原「前二唯一」旋转，契约不被本次改动影响。"""
    row = {"content": '["01","17","40","11"]', "year": "2026", "term": "88", "web": "6"}
    recent_rows = [{"content": '["01","17","99","98"]'}]
    result = diversity.enforce_prediction_diversity(mode_id=46, row_data=row, recent_rows=recent_rows)
    assert json.loads(result["content"]) != json.loads(row["content"])
    assert sorted(json.loads(result["content"])) == sorted(json.loads(row["content"]))


def test_whitelisted_mode_returns_without_rotation_warning():
    row = {"content": "01,17,40,11", "year": "2026", "term": "88", "web": "6"}
    result = diversity.enforce_prediction_diversity(
        mode_id=116, row_data=row, recent_rows=[{"content": "01,17,40,11"}]
    )
    assert "_diversity_warning" not in result
