"""Verified future-generation rules for prediction modules.

Rules keep future truth inside the generation domain and convert it into the
single outcome label that each configured module actually evaluates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import DrawTruth

TruthOutcome = Callable[[DrawTruth, Any], str]


def _normalized_code(truth: DrawTruth) -> int:
    return int(str(truth.special_code or "0"))


def _special_zodiac(truth: DrawTruth, _conn: Any) -> str:
    return str(truth.special_zodiac or "").strip()


def _special_number(truth: DrawTruth, _conn: Any) -> str:
    return str(truth.special_code or "").strip()


def _special_head(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "0头" if number < 10 else f"{number // 10}头"


def _special_tail(truth: DrawTruth, _conn: Any) -> str:
    return f"{_normalized_code(truth) % 10}尾"


def _special_parity(truth: DrawTruth, _conn: Any) -> str:
    return "双" if _normalized_code(truth) % 2 == 0 else "单"


def _special_size(truth: DrawTruth, _conn: Any) -> str:
    return "大" if _normalized_code(truth) >= 25 else "小"


def _special_wave(truth: DrawTruth, _conn: Any) -> str:
    raw = str(truth.special_color or "").strip()
    return {"red": "红波", "blue": "蓝波", "green": "绿波"}.get(raw, raw)


def _special_half_wave(truth: DrawTruth, _conn: Any) -> str:
    wave = _special_wave(truth, _conn).removesuffix("波")
    parity = _special_parity(truth, _conn)
    return f"{wave}{parity}" if wave and parity else ""


def _combined_parity(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "合单" if ((number // 10) + (number % 10)) % 2 else "合双"


def _combined_size(truth: DrawTruth, _conn: Any) -> str:
    number = _normalized_code(truth)
    return "合数大" if (number // 10) + (number % 10) >= 7 else "合数小"


@dataclass(frozen=True)
class PredictionGenerationRule:
    rule_id: str
    rule_revision: int
    supported: bool
    block_reason: str
    cross_site_prefix_width: int
    truth_outcome: TruthOutcome | None = None

    def verify_hit(
        self,
        config: Any,
        labels: tuple[str, ...],
        truth: DrawTruth,
        *,
        conn: Any,
    ) -> bool:
        if not self.supported or self.truth_outcome is None:
            return False
        outcome = self.truth_outcome(truth, conn)
        hit_checker = getattr(config, "hit_checker", None)
        return bool(outcome and callable(hit_checker) and hit_checker(outcome, tuple(labels)))

    def signature(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(str(label).strip() for label in labels if str(label).strip())

    def prefix_signature(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        return self.signature(labels)[: max(1, int(self.cross_site_prefix_width))]


_BLOCKED_RULE = PredictionGenerationRule(
    rule_id="blocked_pending_rule",
    rule_revision=1,
    supported=False,
    block_reason="missing_verified_rule",
    cross_site_prefix_width=1,
)


def _rule(rule_id: str, truth_outcome: TruthOutcome, *, prefix_width: int = 1) -> PredictionGenerationRule:
    return PredictionGenerationRule(
        rule_id=rule_id,
        rule_revision=1,
        supported=True,
        block_reason="",
        cross_site_prefix_width=prefix_width,
        truth_outcome=truth_outcome,
    )


_RULE_BY_MODE_ID: dict[int, PredictionGenerationRule] = {
    # Ordered zodiac candidates, including normal and exclusion variants.
    31: _rule("zodiac", _special_zodiac, prefix_width=2),
    42: _rule("zodiac_exclusion", _special_zodiac),
    43: _rule("zodiac", _special_zodiac),
    44: _rule("zodiac", _special_zodiac, prefix_width=2),
    45: _rule("zodiac", _special_zodiac, prefix_width=2),
    46: _rule("zodiac", _special_zodiac, prefix_width=2),
    47: _rule("zodiac", _special_zodiac),
    48: _rule("zodiac", _special_zodiac, prefix_width=2),
    49: _rule("zodiac", _special_zodiac, prefix_width=3),
    51: _rule("zodiac", _special_zodiac),
    56: _rule("zodiac", _special_zodiac),
    60: _rule("zodiac", _special_zodiac, prefix_width=3),
    69: _rule("zodiac", _special_zodiac),
    72: _rule("zodiac", _special_zodiac),
    78: _rule("zodiac", _special_zodiac),
    117: _rule("zodiac", _special_zodiac),
    197: _rule("zodiac", _special_zodiac),
    219: _rule("zodiac", _special_zodiac),
    470: _rule("zodiac", _special_zodiac),
    472: _rule("zodiac_exclusion", _special_zodiac),
    473: _rule("zodiac_exclusion", _special_zodiac),
    484: _rule("zodiac", _special_zodiac, prefix_width=2),
    # Number, head, tail, and basic classification candidates.
    12: _rule("head", _special_head),
    20: _rule("tail_exclusion", _special_tail),
    28: _rule("parity", _special_parity),
    34: _rule("number", _special_number, prefix_width=3),
    38: _rule("wave", _special_wave),
    54: _rule("tail", _special_tail),
    57: _rule("size", _special_size),
    58: _rule("half_wave_exclusion", _special_half_wave),
    66: _rule("tail", _special_tail),
    74: _rule("tail", _special_tail, prefix_width=2),
    77: _rule("number", _special_number, prefix_width=2),
    81: _rule("tail", _special_tail),
    123: _rule("tail", _special_tail),
    132: _rule("combined_parity", _combined_parity),
    143: _rule("wave", _special_wave),
    279: _rule("combined_size", _combined_size),
    471: _rule("head", _special_head),
    481: _rule("number_exclusion", _special_number, prefix_width=2),
    483: _rule("head", _special_head),
}


def get_generation_rule(config: Any) -> PredictionGenerationRule:
    """Return the verified future-control rule for a prediction config."""
    try:
        mode_id = int(getattr(config, "default_modes_id", 0) or 0)
    except (TypeError, ValueError):
        return _BLOCKED_RULE
    return _RULE_BY_MODE_ID.get(mode_id, _BLOCKED_RULE)
