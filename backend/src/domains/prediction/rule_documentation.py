"""Deterministic documentation rendering for future-generation rules."""

from __future__ import annotations

from typing import Any, Iterable

from .generation_rules import get_generation_rule
from .site_page_dependencies import generation_assurance_for_mode


def _display_uniqueness_note(mode_id: int) -> str:
    """标注“相邻连续 N 期展示值不得相同”模式，供规则文档审阅。"""
    from prediction_generation.diversity import (
        THREE_PERIOD_UNIQUE_MODE_IDS,
        display_unique_window,
    )

    resolved_mode_id = int(mode_id or 0)
    if resolved_mode_id not in THREE_PERIOD_UNIQUE_MODE_IDS:
        return ""
    window = display_unique_window(resolved_mode_id)
    return f"adjacent {window} periods: display value differs"


def _unordered_set_note(mode_id: int) -> str:
    """标注“无序号码集合”模式：不做位置轮转，改为按期号的一次性展示置换。

    这些 mode 的 content 是 01-49 号码集合，展示顺序没有语义；旧的“前二唯一”轮转
    在纯号码串上本来就是空转，且会让同一批号码固定占住前几位。
    """
    from prediction_generation.diversity import UNORDERED_NUMBER_SET_MODE_IDS

    if int(mode_id or 0) not in UNORDERED_NUMBER_SET_MODE_IDS:
        return ""
    return "unordered number set: no positional rotation; adjacent: display order differs"


def _unordered_set_legend() -> str:
    """图例：说明无序号码集合模式的展示顺序契约（由白名单直接生成）。"""
    from prediction_generation.diversity import UNORDERED_NUMBER_SET_MODE_IDS

    modes = " / ".join(str(mode_id) for mode_id in sorted(UNORDERED_NUMBER_SET_MODE_IDS))
    return (
        f"Unordered number-set modules (mode {modes}) never use positional rotation: their `content` "
        "is a set of 01-49 numbers, so the display order is a per-issue permutation of the same "
        "members and the adjacent-period contract is `display order differs` instead of "
        "`full ordered signature`."
    )


_SEMANTIC_NOTES: tuple[str, ...] = (
    "\n".join(
        (
            "Wave-label modules (mode 38 双波中特 / mode 143 一波中特) store the candidate as the **wave label** itself",
            "(`蓝波,绿波`, or `[\"蓝波|03,04,…\",\"绿波|05,06,…\"]`), so their `content_parser` must be",
            "`parse_literal_label_content`; `parse_zodiac_content` only recognizes zodiac characters and returns an empty",
            "tuple for wave labels, which made `is_correct` permanently `null` for mode 38 before 2026-09-28.",
            "The special-number wave comes from `res_color` (last value → 红波/蓝波/绿波) with `fixed_data` sign `波色`",
            "as fallback (`predict.categories.size_parity.special_wave_from_row`) and is embedded in the composite outcome",
            "by `public.api._compute_outcome_from_row`.",
        )
    ),
    "\n".join(
        (
            "Half-wave modules (mode 58 绝杀半波 / mode 490 杀两半波) predict the candidate as the **half-wave label**",
            "itself (`蓝双` / `绿单`), so `_compute_outcome_from_row` must also carry the half-wave atom",
            "(`{波色}{单双}` = `蓝双`) next to the wave and parity atoms; without it the `label in outcome` substring",
            "check can never match and `excludes_hit` returns `True` for every row (the whole column was permanently",
            "\"对\" before 2026-09-28).",
        )
    ),
    "\n".join(
        (
            "Mode 492 三头四尾 is a `PredictionCategory.MIXED` play (`头:` / `尾:` label prefixes), so its hit semantics",
            "follow the repo-wide mixed rule — **any dimension hits** (特码头或特尾任一落入对应候选即命中), implemented by",
            "`predict.mechanisms.three_head_four_tail_hit` and mirrored by",
            "`frontend/lib/prediction-contract.ts::verifyVerdictAgainstCandidates`.",
        )
    ),
    "\n".join(
        (
            "Mode 30 单双各4尾 splits its candidate across two columns: `dan` must hold 4 **single** tails",
            "(`1尾/3尾/5尾/7尾/9尾`, each tail at most once) and `shuang` must hold 4 **double** tails",
            "(`0尾/2尾/4尾/6尾/8尾`). The generator draws every tail from its own group",
            "(`predict.common.selection_group_quotas` / `domains.prediction.candidate_control` group quotas),",
            "so `0尾` can never appear in `dan` and `1尾` can never appear in `shuang`.",
        )
    ),
)


def _semantic_notes() -> str:
    """审阅用的候选形态说明（纯静态文本，不含任何开奖真值）。"""
    return "\n\n".join((*(note for note in _SEMANTIC_NOTES), ""))


def _outcome_description(rule_id: str) -> str:
    descriptions = {
        "zodiac": "special zodiac is in any candidate",
        "zodiac_flat": "any drawn number's zodiac is in any candidate",
        "tail_flat": "any drawn number's tail is in any candidate",
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
        "head_tail": "special number head OR tail is in its candidate group (mixed: any dimension)",
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
        _unordered_set_legend(),
        "",
        _semantic_notes(),
        "| mode_id | key | title | rule | outcome semantics | assurance | future control | uniqueness |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for mode_id, key, title, config in sorted(rows, key=lambda item: (item[0], item[1])):
        rule = get_generation_rule(config)
        status = "supported" if rule.supported else f"blocked: {rule.block_reason}"
        assurance = generation_assurance_for_mode(mode_id)
        uniqueness = f"cross-site prefix: {rule.cross_site_prefix_width}; adjacent: full ordered signature"
        unordered_note = _unordered_set_note(mode_id)
        if unordered_note:
            uniqueness = f"cross-site prefix: {rule.cross_site_prefix_width}; {unordered_note}"
        display_note = _display_uniqueness_note(mode_id)
        if display_note:
            uniqueness = f"{uniqueness}; {display_note}"
        lines.append(
            f"| {mode_id} | {key} | {title} | {rule.rule_id} | "
            f"{_outcome_description(rule.rule_id)} | {assurance} | {status} | {uniqueness} |"
        )
    return "\n".join(lines) + "\n"


def write_prediction_module_rules(path: str, configs: Iterable[Any]) -> None:
    """Write the deterministic document using UTF-8 without exposing truth data."""
    from pathlib import Path

    Path(path).write_text(render_prediction_module_rules(configs), encoding="utf-8")
