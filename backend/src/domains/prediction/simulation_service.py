"""Pure domain helpers for Taiwan future-draw simulation control."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from .hit_policy import truth_labels_for_request
from .models import PredictionRequest


@dataclass(frozen=True)
class SimulationConfig:
    target_hit_rate: float = 0.5
    max_consecutive_hits: int = 3
    max_consecutive_misses: int = 3

    def normalized(self) -> "SimulationConfig":
        return SimulationConfig(
            target_hit_rate=min(max(float(self.target_hit_rate), 0.0), 1.0),
            max_consecutive_hits=max(1, int(self.max_consecutive_hits)),
            max_consecutive_misses=max(1, int(self.max_consecutive_misses)),
        )


@dataclass(frozen=True)
class SimulationState:
    consecutive_hits: int = 0
    consecutive_misses: int = 0


@dataclass(frozen=True)
class SimulationResult:
    labels: tuple[str, ...]
    should_hit: bool | None
    safe_debug: dict[str, Any]


def _seed_random(seed: str) -> random.Random:
    seed_int = int(hashlib.sha256(str(seed).encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_int)


def _truth_labels(request: PredictionRequest) -> tuple[str, ...]:
    return tuple(str(label or "").strip() for label in truth_labels_for_request(request) if str(label or "").strip())


def _choose_should_hit(config: SimulationConfig, state: SimulationState, seed: str) -> bool:
    normalized = config.normalized()
    if int(state.consecutive_hits or 0) >= normalized.max_consecutive_hits:
        return False
    if int(state.consecutive_misses or 0) >= normalized.max_consecutive_misses:
        return True
    return _seed_random(seed).random() < normalized.target_hit_rate


def _force_hit(labels: tuple[str, ...], truth_labels: tuple[str, ...]) -> tuple[str, ...]:
    if not truth_labels:
        return labels
    truth_label = truth_labels[0]
    result = list(labels)
    if any(label in result for label in truth_labels):
        return tuple(result)
    if result:
        result[0] = truth_label
    else:
        result.append(truth_label)
    return tuple(result)


def _force_miss(
    labels: tuple[str, ...],
    truth_labels: tuple[str, ...],
    candidates: tuple[str, ...],
    seed: str,
) -> tuple[str, ...]:
    if not truth_labels:
        return labels
    truth_set = set(truth_labels)
    result = [label for label in labels if label not in truth_set]
    alternatives = [label for label in candidates if label not in truth_set and label not in result]
    rng = _seed_random(seed)
    while len(result) < len(labels) and alternatives:
        choice = rng.choice(alternatives)
        alternatives.remove(choice)
        result.append(choice)
    return tuple(result)


def _outcome_from_truth_labels(truth_labels: tuple[str, ...]) -> str:
    return "|".join(truth_labels)


def _is_hit(request: PredictionRequest, labels: tuple[str, ...], truth_labels: tuple[str, ...]) -> bool:
    if request.hit_checker:
        return bool(request.hit_checker(_outcome_from_truth_labels(truth_labels), tuple(labels)))
    return any(label in labels for label in truth_labels)


def _force_target_semantics(
    request: PredictionRequest,
    labels: tuple[str, ...],
    truth_labels: tuple[str, ...],
    candidates: tuple[str, ...],
    should_hit: bool,
    seed: str,
) -> tuple[str, ...]:
    if _is_hit(request, labels, truth_labels) is should_hit:
        return labels

    include_truth = _force_hit(labels, truth_labels)
    if _is_hit(request, include_truth, truth_labels) is should_hit:
        return include_truth

    exclude_truth = _force_miss(labels, truth_labels, candidates, seed)
    if _is_hit(request, exclude_truth, truth_labels) is should_hit:
        return exclude_truth

    return labels


def apply_simulation_control(
    request: PredictionRequest,
    *,
    predicted_labels: tuple[str, ...],
    config: SimulationConfig,
    state: SimulationState,
    seed: str,
) -> SimulationResult:
    if (
        int(request.context.lottery_type_id) != 3
        or not request.context.is_future
        or not request.truth
    ):
        return SimulationResult(labels=tuple(predicted_labels), should_hit=None, safe_debug={})

    truth_labels = _truth_labels(request)
    if not truth_labels:
        return SimulationResult(labels=tuple(predicted_labels), should_hit=None, safe_debug={"has_truth": True})

    should_hit = _choose_should_hit(config, state, seed)
    labels = _force_target_semantics(
        request,
        tuple(predicted_labels),
        truth_labels,
        tuple(request.candidate_labels),
        should_hit,
        seed,
    )
    return SimulationResult(
        labels=labels,
        should_hit=should_hit,
        safe_debug={"has_truth": True, "should_hit": should_hit},
    )
