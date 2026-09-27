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
    """28/52/57/63/108 必须标注“相邻连续三期展示值不得相同”。"""
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    assert "adjacent 3 periods: display value differs" in document
    for mode_id, key in (
        (28, "danshuangtema"),
        (52, "sizixuanji"),
        (57, "daxiao"),
        (108, "dxztt1"),
    ):
        assert f"| {mode_id} | {key} |" in document
        row = next(
            line for line in document.splitlines()
            if line.startswith(f"| {mode_id} | {key} |")
        )
        assert "adjacent 3 periods: display value differs" in row


def test_rule_document_marks_five_period_display_uniqueness_for_mode_62():
    """62 欲钱解特诗候选池最大，要求相邻连续五期展示值不得相同。"""
    document = render_prediction_module_rules(PREDICTION_CONFIGS.values())

    row = next(
        line for line in document.splitlines()
        if line.startswith("| 62 | yqjs |")
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
