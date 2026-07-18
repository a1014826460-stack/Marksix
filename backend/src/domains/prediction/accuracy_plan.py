"""Pure rolling-window target selection for controlled future predictions."""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class AccuracyPolicy:
    """The minimum verified hit rate required in each complete rolling window."""

    window_size: int = 10
    minimum_hit_rate: float = 0.6

    def normalized(self) -> "AccuracyPolicy":
        return AccuracyPolicy(
            window_size=max(1, int(self.window_size)),
            minimum_hit_rate=min(max(float(self.minimum_hit_rate), 0.0), 1.0),
        )

    @property
    def minimum_hits(self) -> int:
        normalized = self.normalized()
        return math.ceil(normalized.window_size * normalized.minimum_hit_rate)

    @property
    def maximum_misses(self) -> int:
        normalized = self.normalized()
        return normalized.window_size - normalized.minimum_hits


def _stable_random(seed: str) -> random.Random:
    value = int(hashlib.sha256(str(seed).encode("utf-8")).hexdigest(), 16) % (2**32)
    return random.Random(value)


def choose_target_hit(
    previous: Sequence[bool],
    *,
    policy: AccuracyPolicy,
    seed: str,
) -> bool:
    """Choose a target while preventing an incomplete window from exceeding misses."""
    normalized = policy.normalized()
    preceding = list(previous)[-(normalized.window_size - 1) :]
    if sum(not bool(value) for value in preceding) >= normalized.maximum_misses:
        return True
    return _stable_random(seed).random() < normalized.minimum_hit_rate


def validate_rolling_hit_rate(
    outcomes: Sequence[bool],
    *,
    policy: AccuracyPolicy,
) -> list[tuple[int, int, int, int]]:
    """Return non-sensitive counts for rolling windows below the required rate."""
    normalized = policy.normalized()
    failures: list[tuple[int, int, int, int]] = []
    for start in range(0, max(0, len(outcomes) - normalized.window_size + 1)):
        end = start + normalized.window_size
        actual_hits = sum(bool(value) for value in outcomes[start:end])
        if actual_hits < normalized.minimum_hits:
            failures.append((start, end, actual_hits, normalized.minimum_hits))
    return failures
