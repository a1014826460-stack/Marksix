from __future__ import annotations

from domains.prediction.models import DrawContext, DrawTruth, PredictionCategory, PredictionRequest
from domains.prediction.simulation_service import SimulationConfig, SimulationState, apply_simulation_control
from predict.common import excludes_hit


def _request(labels=("rat", "ox", "tiger")):
    return PredictionRequest(
        category=PredictionCategory.ZODIAC,
        context=DrawContext(
            lottery_type_id=3,
            year=2026,
            term=131,
            is_future=True,
            site_id=7,
            web_id=6,
            mode_id=43,
            mechanism_key="pt3xiao",
        ),
        config_key="pt3xiao",
        candidate_labels=labels,
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "07"),
            special_code="07",
            special_zodiac="rat",
            special_color="red",
        ),
    )


def _mixed_request(labels=("zodiac:rabbit", "number:27", "tail:7", "head:2", "color:red", "tail:3")):
    request = _request(labels=labels)
    return PredictionRequest(
        category=PredictionCategory.MIXED,
        context=DrawContext(
            lottery_type_id=3,
            year=2026,
            term=131,
            is_future=True,
            site_id=7,
            web_id=6,
            mode_id=333,
            mechanism_key="mixed",
        ),
        config_key="mixed",
        candidate_labels=labels,
        truth=DrawTruth(
            numbers=("01", "02", "03", "04", "05", "06", "27"),
            special_code="27",
            special_zodiac="rabbit",
            special_color="red",
        ),
    )


def test_simulation_forces_hit_when_target_hit_rate_is_one():
    result = apply_simulation_control(
        _request(),
        predicted_labels=("ox", "tiger"),
        config=SimulationConfig(target_hit_rate=1.0, max_consecutive_hits=3, max_consecutive_misses=3),
        state=SimulationState(),
        seed="hit",
    )

    assert result.labels[0] == "rat"
    assert result.should_hit is True
    assert result.safe_debug == {"has_truth": True, "should_hit": True}


def test_simulation_forces_miss_when_target_hit_rate_is_zero():
    result = apply_simulation_control(
        _request(),
        predicted_labels=("rat", "ox"),
        config=SimulationConfig(target_hit_rate=0.0, max_consecutive_hits=3, max_consecutive_misses=3),
        state=SimulationState(),
        seed="miss",
    )

    assert "rat" not in result.labels
    assert result.should_hit is False


def test_simulation_reverses_after_consecutive_limits():
    hit_limited = apply_simulation_control(
        _request(),
        predicted_labels=("ox", "tiger"),
        config=SimulationConfig(target_hit_rate=1.0, max_consecutive_hits=3, max_consecutive_misses=3),
        state=SimulationState(consecutive_hits=3),
        seed="force-miss",
    )
    miss_limited = apply_simulation_control(
        _request(),
        predicted_labels=("ox", "tiger"),
        config=SimulationConfig(target_hit_rate=0.0, max_consecutive_hits=3, max_consecutive_misses=3),
        state=SimulationState(consecutive_misses=3),
        seed="force-hit",
    )

    assert hit_limited.should_hit is False
    assert "rat" not in hit_limited.labels
    assert miss_limited.should_hit is True
    assert "rat" in miss_limited.labels


def test_simulation_noops_when_truth_is_missing_or_not_taiwan_future():
    request = _request()
    request = PredictionRequest(
        category=request.category,
        context=DrawContext(
            lottery_type_id=1,
            year=2026,
            term=131,
            is_future=True,
            site_id=7,
            web_id=6,
            mode_id=43,
            mechanism_key="pt3xiao",
        ),
        config_key=request.config_key,
        candidate_labels=request.candidate_labels,
        truth=request.truth,
    )

    result = apply_simulation_control(
        request,
        predicted_labels=("ox", "tiger"),
        config=SimulationConfig(),
        state=SimulationState(),
        seed="noop",
    )

    assert result.labels == ("ox", "tiger")
    assert result.should_hit is None


def test_simulation_uses_any_truth_dimension_for_mixed_hit_control():
    forced_hit = apply_simulation_control(
        _mixed_request(),
        predicted_labels=("tail:3",),
        config=SimulationConfig(target_hit_rate=1.0),
        state=SimulationState(),
        seed="mixed-hit",
    )
    forced_miss = apply_simulation_control(
        _mixed_request(),
        predicted_labels=("tail:7", "zodiac:rabbit", "tail:3"),
        config=SimulationConfig(target_hit_rate=0.0),
        state=SimulationState(),
        seed="mixed-miss",
    )

    assert set(forced_hit.labels) & {"zodiac:rabbit", "number:27", "tail:7", "head:2", "color:red"}
    assert not (set(forced_miss.labels) & {"zodiac:rabbit", "number:27", "tail:7", "head:2", "color:red"})
    assert "tail:3" in forced_miss.labels


def test_simulation_respects_exclusion_hit_checker_semantics():
    base = _request(labels=("rat", "ox", "tiger"))
    request = PredictionRequest(
        category=base.category,
        context=base.context,
        config_key=base.config_key,
        candidate_labels=base.candidate_labels,
        truth=base.truth,
        hit_checker=excludes_hit,
    )

    should_hit = apply_simulation_control(
        request,
        predicted_labels=("rat",),
        config=SimulationConfig(target_hit_rate=1.0),
        state=SimulationState(),
        seed="exclude-hit",
    )
    should_miss = apply_simulation_control(
        request,
        predicted_labels=("ox",),
        config=SimulationConfig(target_hit_rate=0.0),
        state=SimulationState(),
        seed="exclude-miss",
    )

    assert should_hit.should_hit is True
    assert "rat" not in should_hit.labels
    assert should_miss.should_hit is False
    assert "rat" in should_miss.labels
