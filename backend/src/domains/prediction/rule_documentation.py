"""Deterministic documentation rendering for future-generation rules."""

from __future__ import annotations

from typing import Any, Iterable

from .generation_rules import get_generation_rule
from .site_page_dependencies import generation_assurance_for_mode


def _outcome_description(rule_id: str) -> str:
    descriptions = {
        "zodiac": "special zodiac is in any candidate",
        "zodiac_exclusion": "special zodiac is absent from every candidate",
        "number": "special number is in any candidate",
        "number_exclusion": "special number is absent from every candidate",
        "head": "special number head is in any candidate",
        "tail": "special number tail is in any candidate",
        "tail_exclusion": "special number tail is absent from every candidate",
        "size": "special number size is in any candidate",
        "parity": "special number parity is in any candidate",
        "wave": "special number wave is in any candidate",
        "half_wave_exclusion": "special half-wave is absent from every candidate",
        "combined_parity": "special digit-sum parity is in any candidate",
        "combined_size": "special digit-sum size is in any candidate",
        "blocked_pending_rule": "blocked_pending_rule",
    }
    return descriptions.get(rule_id, rule_id)


def render_prediction_module_rules(configs: Iterable[Any]) -> str:
    """Render the registered rules without exposing any future draw information."""
    rows: list[tuple[int, str, str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for config in configs:
        mode_id = int(getattr(config, "default_modes_id", 0) or 0)
        key = str(getattr(config, "key", "") or "")
        identity = (mode_id, key)
        if identity in seen:
            continue
        seen.add(identity)
        rows.append((mode_id, key, str(getattr(config, "title", "") or ""), config))

    lines = [
        "# Prediction Module Future-Generation Rules",
        "",
        "This document is generated from the internal rule manifest. It documents candidate semantics only and never contains future draw values.",
        "",
        "| mode_id | key | title | rule | outcome semantics | assurance | future control | uniqueness |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for mode_id, key, title, config in sorted(rows, key=lambda item: (item[0], item[1])):
        rule = get_generation_rule(config)
        status = "supported" if rule.supported else f"blocked: {rule.block_reason}"
        assurance = generation_assurance_for_mode(mode_id)
        uniqueness = f"cross-site prefix: {rule.cross_site_prefix_width}; adjacent: full ordered signature"
        lines.append(
            f"| {mode_id} | {key} | {title} | {rule.rule_id} | "
            f"{_outcome_description(rule.rule_id)} | {assurance} | {status} | {uniqueness} |"
        )
    return "\n".join(lines) + "\n"


def write_prediction_module_rules(path: str, configs: Iterable[Any]) -> None:
    """Write the deterministic document using UTF-8 without exposing truth data."""
    from pathlib import Path

    Path(path).write_text(render_prediction_module_rules(configs), encoding="utf-8")
