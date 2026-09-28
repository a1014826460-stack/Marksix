"""无序号码集合玩法的展示顺序修复（mode 9 / 34 / 77 / 88 / 116 / 481 / 485 / 493 / 494）。

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

2026-09-29 复审修订：白名单改为**从配置形状派生**（`is_number_set_config`），
不再人工维护；只有展示顺序本身是契约的 mode 才排除。

本文件锁定修复后的契约：
1. 号码集合玩法采用 `unordered_set_display_order` 策略，不再做位置轮转；
2. 展示顺序按 (mode, 年, 期, 站点) 一次性置换：同期稳定、异期不同；
3. **号码成员一个都不变**，命中/不中判定与修复前完全一致；
4. mode 65（码段区间）与 156（杀码段）是合同例外，绝不置换。
"""

from __future__ import annotations

import json

from predict.categories.number import format_24_numbers
from predict.common import contains_hit, excludes_hit
from prediction_generation import diversity


#: 本部署实际启用的号码集合 mode（工单/复审范围）。
_LIVE_NUMBER_SET_MODES = (9, 34, 77, 88, 116, 481, 485, 493, 494)


# ---------- 派生白名单 ----------


def test_unordered_number_set_mode_ids_cover_the_whole_number_set_family():
    """派生集合必须覆盖全部号码集合玩法，而不只是工单点名的几个。

    旧实现是硬编码 `{9, 65, 88, 116}`：34/77/481/485/493/494 同样是纯号码集合，
    却因为没有人工加白名单而一直保留“热度前几位固定”的展示缺陷。
    """
    resolved = set(diversity.unordered_number_set_mode_ids())
    assert set(_LIVE_NUMBER_SET_MODES) <= resolved
    # 派生自配置形状：静态配置里 34/77/481/485/493/494 都能直接判定出来
    for mode_id in (34, 77, 481, 485, 493, 494):
        assert diversity.is_unordered_number_set_mode(mode_id) is True


def test_mode_65_and_156_are_contract_exceptions():
    """mode 65/156 的内容是**连续段区间**，前台按 `content[0]-content[-1]` 判定与渲染。

    `shengshi8800/static/js/016teduan.js` 的区间显示与
    `legacy-prediction-verdict.js::verdictOf(65, …)` 的
    `value >= parseInt(first) && value <= parseInt(last)` 判定都依赖升序连续，
    置换会同时破坏展示与判定，因此必须排除。
    """
    assert 65 not in diversity.unordered_number_set_mode_ids()
    assert 156 not in diversity.unordered_number_set_mode_ids()
    assert diversity.is_unordered_number_set_mode(65) is False
    assert {65, 156} <= set(diversity.UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS)
    assert diversity.resolve_diversity_policy(65, None) == diversity.DEFAULT_DIVERSITY_POLICY


def test_bootstrap_lower_bound_is_never_wider_than_the_derivation():
    """bootstrap 只是下限兜底：配置清单不可用时行为与历史白名单一致。"""
    assert {9, 34, 77, 88, 116, 481, 485, 493, 494} == set(diversity.UNORDERED_NUMBER_SET_BOOTSTRAP_MODE_IDS)
    assert set(diversity.UNORDERED_NUMBER_SET_MODE_IDS) >= set(diversity.UNORDERED_NUMBER_SET_BOOTSTRAP_MODE_IDS)
    assert not (set(diversity.UNORDERED_NUMBER_SET_MODE_IDS) & set(diversity.UNORDERED_NUMBER_SET_DISPLAY_ORDER_EXCLUDED_MODE_IDS))


def test_number_set_config_shape_criterion_is_precise():
    """`is_number_set_config` 只接受「号码全域 + contains/excludes + parse_number_content」。

    有序标签玩法（生肖/尾数/波色/复合口径）一律不能命中，否则会把 `标签|号码`
    有序序列误当成号码集合置换。
    """
    from types import SimpleNamespace

    from predict.common import exact_contains_hit, parse_number_content, parse_pipe_label_content

    number_set = SimpleNamespace(
        content_parser=parse_number_content,
        hit_checker=contains_hit,
        labels=tuple(f"{value:02d}" for value in range(1, 50)),
        label_count=10,
    )
    assert diversity.is_number_set_config(number_set) is True

    # 有序标签解析器
    assert diversity.is_number_set_config(
        SimpleNamespace(
            content_parser=parse_pipe_label_content,
            hit_checker=contains_hit,
            labels=tuple(f"{value:02d}" for value in range(1, 50)),
            label_count=10,
        )
    ) is False
    # 非号码候选全域（例如生肖）
    assert diversity.is_number_set_config(
        SimpleNamespace(
            content_parser=parse_number_content,
            hit_checker=contains_hit,
            labels=("鼠", "牛"),
            label_count=2,
        )
    ) is False
    # 复合/原子口径（三头四尾的 head_tail、四头中特的 exact_contains_hit）不是号码集合
    assert diversity.is_number_set_config(
        SimpleNamespace(
            content_parser=parse_number_content,
            hit_checker=exact_contains_hit,
            labels=tuple(f"{value:02d}" for value in range(1, 50)),
            label_count=10,
        )
    ) is False
    # label_count 必须落在号码全域之内
    assert diversity.is_number_set_config(
        SimpleNamespace(
            content_parser=parse_number_content,
            hit_checker=contains_hit,
            labels=tuple(f"{value:02d}" for value in range(1, 50)),
            label_count=0,
        )
    ) is False


def test_resolve_diversity_policy_returns_unordered_set_policy():
    for mode_id in _LIVE_NUMBER_SET_MODES:
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


def test_wide_number_modes_34_77_481_485_493_494_also_vary():
    """复审补齐：34/77/481/485/493/494 此前没有任何展示顺序修复。

    它们的落库形态与 9/88/116 完全同族（纯 01-49 号码集合），因此派生白名单
    必须一并覆盖；否则“位置被热度排名钉死”的缺陷仍然存在（mode 34 位置 1 集中度
    0.28、前 4 位被 {08,22,23,39} 占住）。
    """
    cases = {
        34: "06,24,39,08,03,49,46,12,10,27,30,28,32,19,18,34,41,14,20,36,33,17,07,11",
        77: "33,25,06,44,41,40,22,01,15,35,24,23,17,31",
        481: "12,28,33,14,31,47,20,24,08,01",
        485: "12,31,01,08,35",
        493: "37,16,03,33,45,47,29,43,05,25,02,28,15,01,14,35,23,34,41,46,39,27",
        494: "37,16,03,33,36,47,29",
    }
    for mode_id, frozen in cases.items():
        leads = []
        for term in range(200, 240):
            row = {"content": frozen, "year": "2026", "term": str(term), "web": "6"}
            result = diversity.enforce_prediction_diversity(mode_id=mode_id, row_data=row)
            ordered = result["content"].split(",")
            # 成员一个都不能变
            assert sorted(ordered) == sorted(frozen.split(",")), mode_id
            leads.append(ordered[0])
        assert len(set(leads)) >= 4, (mode_id, leads)
        assert max(leads.count(value) for value in set(leads)) < 20, (mode_id, leads)
        # 头号不得恒等于原落库首号
        assert leads.count(frozen.split(",")[0]) < 20, (mode_id, leads)


def test_mode_65_segment_content_is_never_permuted():
    """mode 65（码段12）是合同例外：段区间必须保持升序连续。

    `016teduan.js` 用 `${content[0]}-${content[content.length-1]}` 渲染区间，
    `verdictOf(65, …)` 用 first/last 做区间判定；一旦置换，
    「特码落在段内」的判定与展示同时失效。
    """
    segment = "13,14,15,16,17,18,19,20,21,22,23,24"
    for term in range(200, 240):
        row = {"content": segment, "year": "2026", "term": str(term), "web": "4"}
        result = diversity.enforce_prediction_diversity(mode_id=65, row_data=row)
        assert result["content"] == segment
        assert "_diversity_warning" not in result

    # 派生配置里 mode 65 的形状确实像号码集合，但被合同例外挡住
    assert diversity.number_set_members(segment) is not None
    assert diversity.is_unordered_number_set_mode(65) is False


# ---------- 判定语义等价 ----------


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
