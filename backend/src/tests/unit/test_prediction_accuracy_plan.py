from __future__ import annotations

from domains.prediction.accuracy_plan import (
    AccuracyPolicy,
    choose_target_hit,
    validate_rolling_hit_rate,
)


def test_sixty_percent_plan_has_six_hits_in_its_first_ten_terms():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)
    outcomes: list[bool] = []
    for term in range(10):
        outcomes.append(choose_target_hit(outcomes, policy=policy, seed=f"term:{term}"))

    assert sum(outcomes) >= 6
    assert validate_rolling_hit_rate(outcomes, policy=policy) == []


def test_planner_forces_hit_after_four_misses_inside_the_current_window():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)

    assert choose_target_hit(
        [False, False, True, False, True, False],
        policy=policy,
        seed="must-hit",
    ) is True


def test_validator_returns_only_non_sensitive_window_counts():
    policy = AccuracyPolicy(window_size=10, minimum_hit_rate=0.6)

    assert validate_rolling_hit_rate([False] * 10, policy=policy) == [(0, 10, 0, 6)]
