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
