from __future__ import annotations

from domains.prediction.candidate_control import (
    choose_controlled_labels,
    signature_hash,
)
from domains.prediction.generation_rules import get_generation_rule
from domains.prediction.models import DrawTruth
from predict.mechanisms import PREDICTION_CONFIGS


def _truth(zodiac: str) -> DrawTruth:
    return DrawTruth(
        ("01", "02", "03", "04", "05", "06", "27"),
        "27",
        zodiac,
        "绿波",
    )


def test_mode_470_keeps_a_hit_but_changes_its_first_zodiac_for_another_site():
    config = PREDICTION_CONFIGS["pt3xiao"]
    result = choose_controlled_labels(
        config=config,
        rule=get_generation_rule(config),
        truth=_truth("虎"),
        predicted_labels=("虎", "猪", "羊"),
        should_hit=True,
        forbidden_prefixes={("虎",)},
        forbidden_signatures=set(),
        seed="web:5",
    )

    assert result.labels[0] != "虎"
    assert "虎" in result.labels
    assert result.verified_hit is True


def test_mode_470_changes_an_adjacent_duplicate_full_signature():
    config = PREDICTION_CONFIGS["pt3xiao"]
    result = choose_controlled_labels(
        config=config,
        rule=get_generation_rule(config),
        truth=_truth("虎"),
        predicted_labels=("虎", "猪", "羊"),
        should_hit=True,
        forbidden_prefixes=set(),
        forbidden_signatures={("虎", "猪", "羊")},
        seed="term:199",
    )

    assert result.signature != ("虎", "猪", "羊")
    assert "虎" in result.labels


def test_mode_470_reselection_accepts_hash_only_reservations():
    config = PREDICTION_CONFIGS["pt3xiao"]
    result = choose_controlled_labels(
        config=config,
        rule=get_generation_rule(config),
        truth=_truth("虎"),
        predicted_labels=("虎", "猪", "羊"),
        should_hit=True,
        forbidden_prefixes=set(),
        forbidden_signatures=set(),
        forbidden_prefix_hashes={signature_hash(("虎",))},
        forbidden_signature_hashes={signature_hash(("虎", "猪", "羊"))},
        seed="hashed-reservation",
    )

    assert result.labels[0] != "虎"
    assert result.signature != ("虎", "猪", "羊")


def test_exclusion_candidate_uses_truth_only_for_a_controlled_miss():
    config = PREDICTION_CONFIGS["juesha1xiao"]
    rule = get_generation_rule(config)

    hit = choose_controlled_labels(
        config=config,
        rule=rule,
        truth=_truth("虎"),
        predicted_labels=("虎",),
        should_hit=True,
        forbidden_prefixes=set(),
        forbidden_signatures=set(),
        seed="exclude-hit",
    )
    miss = choose_controlled_labels(
        config=config,
        rule=rule,
        truth=_truth("虎"),
        predicted_labels=("鼠",),
        should_hit=False,
        forbidden_prefixes=set(),
        forbidden_signatures=set(),
        seed="exclude-miss",
    )

    assert "虎" not in hit.labels
    assert hit.verified_hit is True
    assert "虎" in miss.labels
    assert miss.verified_hit is False
