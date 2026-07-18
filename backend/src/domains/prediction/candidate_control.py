"""Deterministic reselection of legal future prediction candidates."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass
from typing import Any

from .generation_rules import PredictionGenerationRule
from .models import DrawTruth


class ControlledCandidateUnavailable(ValueError):
    """No candidate can satisfy the verified rule and uniqueness constraints."""


@dataclass(frozen=True)
class ControlledCandidate:
    labels: tuple[str, ...]
    signature: tuple[str, ...]
    prefix_signature: tuple[str, ...]
    verified_hit: bool


def _rng(seed: str) -> random.Random:
    value = int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest(), 16) % (2**32)
    return random.Random(value)


def signature_hash(values: tuple[str, ...]) -> str:
    """Hash a canonical candidate signature for comparison with ledger reservations."""
    payload = json.dumps([str(value) for value in values], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _candidate_sequences(
    *,
    predicted_labels: tuple[str, ...],
    available_labels: tuple[str, ...],
    width: int,
    seed: str,
) -> list[tuple[str, ...]]:
    candidates: list[tuple[str, ...]] = []
    baseline = _ordered_unique(predicted_labels)
    if len(baseline) == width:
        candidates.append(baseline)
        candidates.extend(tuple(item) for item in itertools.permutations(baseline))

    pool = list(_ordered_unique(available_labels))
    _rng(seed).shuffle(pool)
    for combination in itertools.combinations(pool, width):
        candidates.extend(tuple(item) for item in itertools.permutations(combination))
    return list(dict.fromkeys(candidates))


def choose_controlled_labels(
    *,
    config: Any,
    rule: PredictionGenerationRule,
    truth: DrawTruth,
    predicted_labels: tuple[str, ...],
    should_hit: bool,
    forbidden_prefixes: set[tuple[str, ...]],
    forbidden_signatures: set[tuple[str, ...]],
    seed: str,
    conn: Any = None,
    forbidden_prefix_hashes: set[str] | None = None,
    forbidden_signature_hashes: set[str] | None = None,
) -> ControlledCandidate:
    """Select a rule-verified candidate that does not collide with reserved signatures."""
    if not rule.supported:
        raise ControlledCandidateUnavailable(
            f"mode_id={int(getattr(config, 'default_modes_id', 0) or 0)}: unsupported_rule"
        )

    width = max(1, int(getattr(config, "label_count", 0) or len(predicted_labels) or 1))
    available_labels = tuple(getattr(config, "labels", ()) or ())
    for labels in _candidate_sequences(
        predicted_labels=tuple(predicted_labels),
        available_labels=available_labels,
        width=width,
        seed=seed,
    ):
        signature = rule.signature(labels)
        prefix = rule.prefix_signature(labels)
        if (
            signature in forbidden_signatures
            or prefix in forbidden_prefixes
            or signature_hash(signature) in (forbidden_signature_hashes or set())
            or signature_hash(prefix) in (forbidden_prefix_hashes or set())
        ):
            continue
        verified_hit = rule.verify_hit(config, labels, truth, conn=conn)
        if verified_hit == bool(should_hit):
            return ControlledCandidate(
                labels=labels,
                signature=signature,
                prefix_signature=prefix,
                verified_hit=verified_hit,
            )

    raise ControlledCandidateUnavailable(
        f"mode_id={int(getattr(config, 'default_modes_id', 0) or 0)}: candidate_space_exhausted"
    )
