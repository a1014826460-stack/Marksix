from __future__ import annotations

from domains.prediction.rule_documentation import (
    render_prediction_module_rules,
    write_prediction_module_rules,
)
from predict.mechanisms import PREDICTION_CONFIGS


def test_rule_document_lists_mode_470_and_blocked_dynamic_configs():
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    assert "| 470 | pt3xiao | 平特3肖 |" in document
    assert "special zodiac is in any candidate" in document
    assert "cross-site prefix: 1" in document
    assert "blocked_pending_rule" in document


def test_rule_document_includes_internal_generation_assurance_without_truth_data():
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    assert "| assurance |" in document
    assert "| 470 | pt3xiao | 平特3肖 |" in document
    assert "| controlled_future |" in document
    assert "| 50 | yijuzhenyan | 一句真言 |" in document
    assert "| history_only |" in document


def test_rule_document_writer_preserves_renderer_output(tmp_path):
    target = tmp_path / "prediction-module-rules.md"

    write_prediction_module_rules(str(target), PREDICTION_CONFIGS.values())

    assert target.read_text(encoding="utf-8") == render_prediction_module_rules(PREDICTION_CONFIGS.values())


def test_rule_document_marks_three_period_display_uniqueness_modes():
    """28/57/63/108 必须标注“相邻连续三期展示值不得相同”。"""
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    assert "adjacent 3 periods: display value differs" in document
    for mode_id, key in (
        (28, "danshuangtema"),
        (57, "daxiao"),
        (108, "dxztt1"),
    ):
        assert f"| {mode_id} | {key} |" in document
        row = next(
            line for line in document.splitlines()
            if line.startswith(f"| {mode_id} | {key} |")
        )
        assert "adjacent 3 periods: display value differs" in row


def test_rule_document_marks_five_period_display_uniqueness_for_text_modes():
    """52 四字玄机与 62 欲钱解特候选池最大，要求相邻连续五期展示值不得相同。"""
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    for mode_id, key in ((52, "sizixuanji"), (62, "yqjs")):
        row = next(
            line for line in document.splitlines()
            if line.startswith(f"| {mode_id} | {key} |")
        )
        assert "adjacent 5 periods: display value differs" in row


def test_rule_document_keeps_single_item_modes_flagged():
    """mode 63（动态注册）在文档中也必须带三期约束标记。"""
    from types import SimpleNamespace

    from predict.mechanisms import PREDICTION_CONFIGS

    dynamic_like = SimpleNamespace(
        key="title_63",
        title="家野中特",
        default_modes_id=63,
        labels=(),
        label_count=1,
    )
    document = render_prediction_module_rules(
        [*PREDICTION_CONFIGS.values(), dynamic_like]
    )

    row = next(
        line for line in document.splitlines()
        if line.startswith("| 63 |") and "家野中特" in line
    )
    assert "adjacent 3 periods: display value differs" in row


def test_rule_document_marks_unordered_number_set_modes():
    """无序号码集合玩法必须标注“不做位置轮转 + 相邻期展示顺序不同”。

    图例与逐行标注都改为从**派生集合**读取（`unordered_number_set_mode_ids()`），
    并显式列出合同例外（mode 65/156），避免审阅者以为段区间玩法也被置换。
    """
    from types import SimpleNamespace

    from prediction_generation.diversity import unordered_number_set_mode_ids

    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())
    derived = sorted(unordered_number_set_mode_ids())
    assert "Unordered number-set modules (mode " + " / ".join(str(m) for m in derived) + ")" in document
    assert "never use positional rotation" in document
    # 图例必须写明派生来源与合同例外，否则审阅者无从判断新增 mode 是否已覆盖
    assert "derived" in document
    assert "Contract exceptions (mode 65 / 156)" in document
    assert "content[0]-content[-1]" in document

    configs = [
        SimpleNamespace(
            key=f"title_{mode_id}",
            title=f"number-set-{mode_id}",
            default_modes_id=mode_id,
            labels=(),
            label_count=10,
        )
        for mode_id in derived
    ]
    document = render_prediction_module_rules(configs)
    for mode_id in derived:
        row = next(
            line for line in document.splitlines()
            if line.startswith(f"| {mode_id} |") and f"number-set-{mode_id}" in line
        )
        assert "unordered number set: no positional rotation; adjacent: display order differs" in row
        assert "full ordered signature" not in row


def test_rule_document_does_not_mark_segment_modes_as_unordered_sets():
    """mode 65（码段12）不得被标成无序号码集合：它的展示顺序就是契约。"""
    from types import SimpleNamespace

    document = render_prediction_module_rules(
        [
            *PREDICTION_CONFIGS.values(),
            SimpleNamespace(key="title_65", title="码段12", default_modes_id=65, labels=(), label_count=12),
        ]
    )
    row = next(line for line in document.splitlines() if line.startswith("| 65 | title_65 |"))
    assert "unordered number set" not in row
    assert "full ordered signature" in row
    # 语义说明里必须给出“不登记 number 规则”的理由（段区间契约）
    assert "Mode 65 码段12" in document
    assert "_generate_mode_65_row" in document


def test_rule_document_lists_modes_9_and_88_with_registered_rules():
    """复审新增登记：mode 9（16码，contains）与 mode 88（杀7码，excludes）。

    两者都是动态配置，必须凭规则登记表进入审阅清单，且判定方向不能写反。
    """
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    row_9 = next(line for line in document.splitlines() if line.startswith("| 9 | title_9 |"))
    assert "| 16码 |" in row_9
    assert "| number |" in row_9
    assert "special number is in any candidate" in row_9
    assert "| controlled_future |" in row_9
    assert "| supported |" in row_9
    assert "cross-site prefix: 2" in row_9

    row_88 = next(line for line in document.splitlines() if line.startswith("| 88 | title_88 |"))
    assert "| 杀7码 |" in row_88
    assert "| number_exclusion |" in row_88
    assert "special number is absent from every candidate" in row_88
    assert "| controlled_future |" in row_88
    assert "| supported |" in row_88
    assert "cross-site prefix: 2" in row_88
    # 反向语义绝不能出现
    assert "special number is in any candidate" not in row_88


def test_rule_document_lists_dynamic_mode_116_with_registered_rule():
    """mode 116（10码中特）是动态配置，必须凭规则登记表进入审阅清单。

    `PREDICTION_CONFIGS` 只维护静态玩法，`title_116` 由 `predict.registry_builder` 从
    `mode_payload_tables` 动态发现，因此旧版渲染器永远看不到它。登记受控规则后必须
    在文档里出现：`rule=number`、controlled_future、supported。
    """
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    row = next(
        line for line in document.splitlines()
        if line.startswith("| 116 | title_116 |")
    )
    assert "| 10码中特 |" in row
    assert "| number |" in row
    assert "special number is in any candidate" in row
    assert "| controlled_future |" in row
    assert "| supported |" in row
    assert "cross-site prefix: 2" in row
    # 展示顺序契约：无序号码集合不做位置轮转
    assert "unordered number set: no positional rotation; adjacent: display order differs" in row
    # 明确写出中文口径（特码号码落入候选号码集合即命中）
    assert "特码号码落入候选号码集合即命中" in document
    # 受控行不过展示置换（否则预约前缀与落库内容脱钩）
    assert "control_plan is None" in document


def test_dynamic_registered_mode_rows_never_duplicate_passed_configs():
    """已传入的配置不得在动态补充清单里重复；且补充项必须仍是受控已登记规则。"""
    from types import SimpleNamespace

    from domains.prediction.generation_rules import RULE_BY_MODE_ID

    configs = [
        *PREDICTION_CONFIGS.values(),
        SimpleNamespace(key="title_116", title="10码中特", default_modes_id=116),
    ]
    document = render_prediction_module_rules(configs)

    rows = [line for line in document.splitlines() if line.startswith("| 116 |")]
    assert len(rows) == 1
    assert RULE_BY_MODE_ID[116].supported is True
